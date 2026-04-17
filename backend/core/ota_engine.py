import time
import json
import asyncio
from dataclasses import dataclass
from typing import List, Optional, Callable, Awaitable

from core.config import CHUNK_SIZE, APP_SLOT_A, APP_SLOT_B, STATE_FILE
from core.config import Config
from protocol.modbus_client import ModbusClient
from utils.logger import get_logger
from utils.crc import calculate_crc32
from utils.hex_parser import read_firmware


@dataclass
class Chunk:
    index: int
    data: bytes
    address: int


@dataclass
class UploadProgress:
    device_id: int
    bytes_written: int
    total_bytes: int
    speed_kb_s: float

    @property
    def percent(self) -> int:
        if self.total_bytes == 0:
            return 0
        return int(self.bytes_written / self.total_bytes * 100)


@dataclass
class UploadState:
    offset: int = 0
    address: int = 0
    device_id: Optional[int] = None
    filename: Optional[str] = None


class OTAEngine:
    def __init__(self):
        self._config = Config()
        self._logger = get_logger()
        self._firmware_data: Optional[bytes] = None
        self._crc: int = 0
        self._chunks: List[Chunk] = []
        self._start_time: Optional[float] = None
        self._last_bytes: int = 0
        self._upload_callback: Optional[Callable[[UploadProgress], Awaitable[None]]] = None

    def set_progress_callback(self, callback: Callable[[UploadProgress], Awaitable[None]]) -> None:
        self._upload_callback = callback

    @property
    def firmware_size(self) -> int:
        return len(self._firmware_data) if self._firmware_data else 0

    async def load_firmware(self, path: str) -> int:
        self._logger.info(f"Loading firmware: {path}")
        self._firmware_data = read_firmware(path)
        self._crc = calculate_crc32(self._firmware_data)
        self._logger.info(f"Firmware loaded: {len(self._firmware_data)} bytes, CRC: {hex(self._crc)}")
        return len(self._firmware_data)

    def compute_chunks(self) -> List[Chunk]:
        if not self._firmware_data:
            raise ValueError("No firmware loaded")

        self._chunks = []
        for i in range(0, len(self._firmware_data), CHUNK_SIZE):
            chunk_data = self._firmware_data[i:i + CHUNK_SIZE]
            chunk = Chunk(
                index=i // CHUNK_SIZE,
                data=chunk_data,
                address=i
            )
            self._chunks.append(chunk)

        self._logger.info(f"Created {len(self._chunks)} chunks")
        return self._chunks

    def get_start_chunk_index(self) -> int:
        state = self._load_state()
        if state and state.filename:
            return state.offset // CHUNK_SIZE
        return 0

    def _load_state(self) -> Optional[UploadState]:
        try:
            with open(STATE_FILE, "r") as f:
                data = json.load(f)
            return UploadState(
                offset=data.get("o", 0),
                address=data.get("a", 0),
                device_id=data.get("d"),
                filename=data.get("f")
            )
        except:
            return None

    def _save_state(self, offset: int, address: int, device_id: Optional[int] = None, filename: Optional[str] = None) -> None:
        try:
            with open(STATE_FILE, "w") as f:
                json.dump({"o": offset, "a": address, "d": device_id, "f": filename}, f)
        except Exception as e:
            self._logger.error(f"Failed to save state: {e}")

    def get_slot(self, device_id: int) -> int:
        return APP_SLOT_A if device_id % 2 == 0 else APP_SLOT_B

    async def upload(
        self,
        port: str,
        device_id: int,
        baudrate: int = 115200
    ) -> bool:
        if not self._firmware_data or not self._chunks:
            self._logger.error("No firmware loaded")
            return False

        self._logger.info(f"Starting upload to device {device_id}")
        client = ModbusClient(port, device_id, baudrate)

        slot = self.get_slot(device_id)
        self._logger.info(f"Using slot: {hex(slot)}")

        state = self._load_state()
        offset = state.offset if state else 0
        start_chunk = offset // CHUNK_SIZE

        client.start_bootloader()

        self._start_time = time.time()
        self._last_bytes = 0
        current_address = slot + offset

        for chunk in self._chunks[start_chunk:]:
            client.write_chunk(chunk.data, current_address)

            current_address += len(chunk.data)
            offset += len(chunk.data)
            self._last_bytes += len(chunk.data)

            self._save_state(offset, current_address, device_id)

            if self._upload_callback:
                progress = UploadProgress(
                    device_id=device_id,
                    bytes_written=offset,
                    total_bytes=len(self._firmware_data),
                    speed_kb_s=self._calculate_speed()
                )
                await self._upload_callback(progress)

        client.verify_crc(self._crc)
        client.set_recovery_flag()
        client.complete()

        self._logger.info(f"Upload to device {device_id} complete")
        client.close()
        return True

    def _calculate_speed(self) -> float:
        if self._start_time is None:
            return 0.0
        elapsed = time.time() - self._start_time
        if elapsed <= 0:
            return 0.0
        kb = self._last_bytes / 1024
        return kb / elapsed

    def get_crc(self) -> int:
        return self._crc

    def get_chunk_count(self) -> int:
        return len(self._chunks)