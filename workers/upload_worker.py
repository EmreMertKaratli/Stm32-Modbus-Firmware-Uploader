from PySide6.QtCore import QThread, Signal
import time

from protocol.modbus_client import ModbusClient
from utils.config import Config, CHUNK_SIZE
from utils.config import APP_SLOT_A, APP_SLOT_B
from utils.crc import calculate_crc32
from utils.hex_parser import read_firmware
from utils.logger import get_logger


class UploadWorker(QThread):
    upload_progress = Signal(int, int, float)
    upload_finished = Signal(int, bool)
    upload_error = Signal(int, str)
    log_message = Signal(str, str)

    def __init__(self, port: str, device_id: int, baudrate: int = 115200):
        super().__init__()
        self._port = port
        self._device_id = device_id
        self._baudrate = baudrate
        self._config = Config()
        self._logger = get_logger()
        self._cancelled = False

        self._firmware_data = None
        self._firmware_path = None

    def set_firmware(self, path: str, data: bytes):
        self._firmware_path = path
        self._firmware_data = data

    def run(self):
        if not self._firmware_data:
            self.upload_error.emit(self._device_id, "No firmware data")
            return

        self._cancelled = False
        self._logger.info(f"Starting upload to device {self._device_id}...")
        self.log_message.emit(f"Uploading to device {self._device_id}...", "INFO")

        slot = APP_SLOT_A if self._device_id % 2 == 0 else APP_SLOT_B
        self._logger.info(f"Using slot: {hex(slot)}")

        try:
            client = ModbusClient(self._port, self._device_id, self._baudrate)
            client.start_bootloader()

            start_time = time.time()
            last_bytes = 0
            current_address = slot
            total_bytes = len(self._firmware_data)

            for i in range(0, total_bytes, CHUNK_SIZE):
                if self._cancelled:
                    self._logger.info("Upload cancelled")
                    self.log_message.emit("Upload cancelled", "WARNING")
                    break

                chunk = self._firmware_data[i:i + CHUNK_SIZE]
                client.write_chunk(chunk, current_address)

                current_address += len(chunk)
                last_bytes += len(chunk)

                elapsed = time.time() - start_time
                speed = (last_bytes / 1024) / elapsed if elapsed > 0 else 0
                self.upload_progress.emit(last_bytes, total_bytes, speed)

            crc = calculate_crc32(self._firmware_data)
            client.verify_crc(crc)
            client.set_recovery_flag()
            client.complete()
            client.close()

            self._logger.info(f"Upload to device {self._device_id} complete")
            self.log_message.emit(f"Device {self._device_id} DONE", "INFO")
            self.upload_finished.emit(self._device_id, True)

        except Exception as e:
            self._logger.error(f"Upload failed: {e}")
            self.log_message.emit(f"Error: {e}", "ERROR")
            self.upload_error.emit(self._device_id, str(e))
            self.upload_finished.emit(self._device_id, False)

    def cancel(self):
        self._cancelled = True