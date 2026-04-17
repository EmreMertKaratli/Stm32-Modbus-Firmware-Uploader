from PySide6.QtCore import QThread, Signal

from protocol.modbus_client import ModbusClient
from utils.config import Config
from utils.logger import get_logger


class DeviceInfo:
    def __init__(self, slave_id: int, port: str, baudrate: int):
        self.slave_id = slave_id
        self.port = port
        self.baudrate = baudrate


class ScanWorker(QThread):
    device_found = Signal(int)
    scan_progress = Signal(int, int)
    scan_finished = Signal(list)
    scan_error = Signal(str)
    log_message = Signal(str, str)

    def __init__(self, port: str, baudrate: int = 115200):
        super().__init__()
        self._port = port
        self._baudrate = baudrate
        self._config = Config()
        self._logger = get_logger()
        self._devices = []
        self._cancelled = False

    def run(self):
        self._devices = []
        self._cancelled = False
        self._logger.info(f"Starting scan on {self._port}...")
        self.log_message.emit(f"Scanning on {self._port}...", "INFO")

        total = self._config.scan_range_end - self._config.scan_range_start + 1

        for sid in range(
            self._config.scan_range_start,
            self._config.scan_range_end + 1
        ):
            if self._cancelled:
                self._logger.info("Scan cancelled")
                self.log_message.emit("Scan cancelled", "WARNING")
                break

            self.scan_progress.emit(sid, total)

            try:
                client = ModbusClient(self._port, sid, self._baudrate)
                if client.ping():
                    device = DeviceInfo(sid, self._port, self._baudrate)
                    self._devices.append(device)
                    self._logger.info(f"Found device {sid}")
                    self.device_found.emit(sid)
                    self.log_message.emit(f"Found device {sid}", "INFO")
                client.close()
            except Exception as e:
                self._logger.debug(f"Device {sid} not responding: {e}")
                continue

        self._logger.info(f"Scan complete: {len(self._devices)} device(s) found")
        self.scan_finished.emit([d.slave_id for d in self._devices])

    def cancel(self):
        self._cancelled = True