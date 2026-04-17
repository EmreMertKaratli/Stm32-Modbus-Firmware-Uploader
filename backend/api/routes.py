from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import tempfile
import os

from device import DeviceManager, DeviceInfo
from core.ota_engine import OTAEngine, UploadProgress
from utils.crc import calculate_crc32
from utils.hex_parser import read_firmware

router = APIRouter()

device_manager = DeviceManager()
ota_engine = OTAEngine()


class ConnectionRequest(BaseModel):
    port: str
    baudrate: int = 115200


class ScanRequest(BaseModel):
    port: str
    baudrate: int = 115200


class UploadRequest(BaseModel):
    port: str
    baudrate: int = 115200
    device_ids: List[int]


class PingRequest(BaseModel):
    port: str
    baudrate: int = 115200
    device_id: int


class DeviceResponse(BaseModel):
    slave_id: int
    port: str
    baudrate: int


class ProgressResponse(BaseModel):
    device_id: int
    bytes_written: int
    total_bytes: int
    speed_kb_s: float
    percent: int


@router.get("/ports")
async def get_ports() -> List[str]:
    return DeviceManager.get_available_ports()


@router.post("/connect")
async def set_connection(req: ConnectionRequest):
    device_manager.set_connection(req.port, req.baudrate)
    return {"status": "connected", "port": req.port, "baudrate": req.baudrate}


@router.post("/scan")
async def scan_devices(req: ScanRequest) -> List[DeviceResponse]:
    device_manager.set_connection(req.port, req.baudrate)
    devices = await device_manager.scan()
    return [DeviceResponse(**d.to_dict()) for d in devices]


@router.post("/ping")
async def ping_device(req: PingRequest) -> dict:
    device_manager.set_connection(req.port, req.baudrate)
    result = await device_manager.ping_device(req.device_id)
    return {"device_id": req.device_id, "online": result}


@router.post("/upload/init")
async def init_upload(file bytes = None, filename: str = ""):
    if not file:
        raise HTTPException(status_code=400, detail="No file provided")
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(filename)[1]) as tmp:
        tmp.write(file)
        tmp_path = tmp.name
    
    try:
        size = await ota_engine.load_firmware(tmp_path)
        ota_engine.compute_chunks()
        return {
            "size": size,
            "chunks": ota_engine.get_chunk_count(),
            "crc": hex(ota_engine.get_crc())
        }
    finally:
        os.unlink(tmp_path)


@router.post("/upload/start")
async def start_upload(req: UploadRequest):
    device_manager.set_connection(req.port, req.baudrate)
    
    results = []
    for device_id in req.device_ids:
        try:
            success = await ota_engine.upload(req.port, device_id, req.baudrate)
            results.append({"device_id": device_id, "success": success})
        except Exception as e:
            results.append({"device_id": device_id, "success": False, "error": str(e)})
    
    return {"results": results}


from core.state_manager import StateManager


@router.get("/state")
async def get_state():
    state_manager = StateManager()
    state = state_manager.load()
    if state:
        return state.to_dict()
    return {"offset": 0, "address": 0, "device_id": None, "filename": None}