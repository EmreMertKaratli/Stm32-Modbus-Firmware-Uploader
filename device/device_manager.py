import serial
from serial.tools import list_ports
from typing import List, Optional

from protocol.modbus_client import ModbusClient
from utils.config import Config
from utils.logger import get_logger


class DeviceInfo:
    def __init__(self, slave_id: int, port: str, baudrate: int):
        self.slave_id = slave_id
        self.port = port
        self.baudrate = baudrate

    def __repr__(self) -> str:
        return f"DeviceInfo(id={self.slave_id}, port={self.port}, baud={self.baudrate})"


class DeviceManager:
    def __init__(self, port: str, baudrate: int = 115200):
        self._port = port
        self._baudrate = baudrate
        self._config = Config()
        self._logger = get_logger()
        self._devices: List[DeviceInfo] = []

    @property
    def port(self) -> str:
        return self._port

    @property
    def baudrate(self) -> int:
        return self._baudrate

    @property
    def devices(self) -> List[DeviceInfo]:
        return self._devices

    def scan(self) -> List[DeviceInfo]:
        self._devices = []
        self._logger.info(f"Scanning devices on {self._port}...")

        for sid in range(
            self._config.scan_range_start,
            self._config.scan_range_end + 1
        ):
            try:
                client = ModbusClient(self._port, sid, self._baudrate)
                if client.ping():
                    device = DeviceInfo(sid, self._port, self._baudrate)
                    self._devices.append(device)
                    self._logger.info(f"Found device {sid}")
                client.close()
            except Exception as e:
                self._logger.debug(f"Device {sid} not responding: {e}")
                continue

        self._logger.info(f"Scan complete: {len(self._devices)} device(s) found")
        return self._devices

    def create_client(self, slave_id: int) -> ModbusClient:
        return ModbusClient(self._port, slave_id, self._baudrate)

    @staticmethod
    def get_available_ports() -> List[str]:
        ports = list(list_ports.comports())
        return [p.device for p in ports]

    def ping_device(self, slave_id: int) -> bool:
        try:
            client = self.create_client(slave_id)
            result = client.ping()
            client.close()
            return result
        except Exception as e:
            self._logger.debug(f"Ping device {slave_id} failed: {e}")
            return False