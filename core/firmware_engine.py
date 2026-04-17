import time
import zlib
from dataclasses import dataclass
from typing import List, Optional, Callable

from protocol.modbus_client import ModbusClient
from core.state_manager import StateManager, UploadState
from utils.config import CHUNK_SIZE, APP_SLOT_A, APP_SLOT_B
from utils.config import Config
from utils.hex_parser import read_firmware
from utils.logger import get_logger


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


class FirmwareUploaderEngine:
    def __init__(
        self,
        port: str,
        baudrate: int,
        state_manager: Optional[StateManager] = None
    ):
        self._port = port
        self._baudrate = baudrate
        self._config = Config()
        self._logger = get_logger()
        self._state_manager = state_manager or StateManager()

        self._firmware_data: Optional[bytes] = None
        self._crc: int = 0
        self._chunks: List[Chunk] = []
        self._start_time: Optional[float] = None
        self._last_bytes: int = 0

    @property
    def firmware_size(self) -> int:
        return len(self._firmware_data) if self._firmware_data else 0

    def load_firmware(self, path: str) -> int:
        self._logger.info(f"Loading firmware: {path}")
        self._firmware_data = read_firmware(path)
        self._crc = zlib.crc32(self._firmware_data) & 0xFFFFFFFF
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
        state = self._state_manager.load()
        if state and state.filename:
            return state.offset // CHUNK_SIZE
        return 0

    def upload(
        self,
        device_id: int,
        progress_callback: Optional[Callable[[UploadProgress], None]] = None
    ) -> bool:
        if not self._firmware_data or not self._chunks:
            self._logger.error("No firmware loaded")
            return False

        self._logger.info(f"Starting upload to device {device_id}")
        client = ModbusClient(self._port, device_id, self._baudrate)

        slot = APP_SLOT_A if device_id % 2 == 0 else APP_SLOT_B
        self._logger.info(f"Using slot: {hex(slot)}")

        state = self._state_manager.load()
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

            self._state_manager.save(offset, current_address, device_id)

            if progress_callback:
                speed = self._calculate_speed()
                progress = UploadProgress(
                    device_id=device_id,
                    bytes_written=offset,
                    total_bytes=len(self._firmware_data),
                    speed_kb_s=speed
                )
                progress_callback(progress)

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

    def get_slot(self, device_id: int) -> int:
        return APP_SLOT_A if device_id % 2 == 0 else APP_SLOT_B