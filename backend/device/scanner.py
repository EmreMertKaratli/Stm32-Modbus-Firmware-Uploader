from serial.tools import list_ports
from typing import List

from protocol.modbus_client import ModbusClient
from core.config import Config
from utils.logger import get_logger


class DeviceInfo:
    def __init__(self, slave_id: int, port: str, baudrate: int):
        self.slave_id = slave_id
        self.port = port
        self.baudrate = baudrate

    def to_dict(self) -> dict:
        return {
            "slave_id": self.slave_id,
            "port": self.port,
            "baudrate": self.baudrate
        }


class DeviceScanner:
    def __init__(self, port: str, baudrate: int = 115200):
        self._port = port
        self._baudrate = baudrate
        self._config = Config()
        self._logger = get_logger()

    async def scan(self) -> List[DeviceInfo]:
        devices = []
        self._logger.info(f"Scanning devices on {self._port}...")

        for sid in range(
            self._config.scan_range_start,
            self._config.scan_range_end + 1
        ):
            try:
                client = ModbusClient(self._port, sid, self._baudrate)
                if client.ping():
                    device = DeviceInfo(sid, self._port, self._baudrate)
                    devices.append(device)
                    self._logger.info(f"Found device {sid}")
                client.close()
            except Exception as e:
                self._logger.debug(f"Device {sid} not responding: {e}")
                continue

        self._logger.info(f"Scan complete: {len(devices)} device(s) found")
        return devices


class DeviceManager:
    def __init__(self):
        self._config = Config()
        self._logger = get_logger()
        self._devices: List[DeviceInfo] = []
        self._current_port = None
        self._current_baudrate = 115200

    @property
    def devices(self) -> List[DeviceInfo]:
        return self._devices

    @property
    def current_port(self) -> str:
        return self._current_port

    @property
    def current_baudrate(self) -> int:
        return self._current_baudrate

    def set_connection(self, port: str, baudrate: int = 115200) -> None:
        self._current_port = port
        self._current_baudrate = baudrate

    async def scan(self) -> List[DeviceInfo]:
        scanner = DeviceScanner(self._current_port, self._current_baudrate)
        self._devices = await scanner.scan()
        return self._devices

    def create_client(self, slave_id: int) -> ModbusClient:
        if not self._current_port:
            raise ValueError("No port configured")
        return ModbusClient(self._current_port, slave_id, self._current_baudrate)

    @staticmethod
    def get_available_ports() -> List[str]:
        ports = list(list_ports.comports())
        return [p.device for p in ports]

    async def ping_device(self, slave_id: int) -> bool:
        try:
            client = self.create_client(slave_id)
            result = client.ping()
            client.close()
            return result
        except Exception as e:
            self._logger.debug(f"Ping device {slave_id} failed: {e}")
            return False