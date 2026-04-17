import minimalmodbus
from typing import Optional
from functools import wraps

from utils.config import Config, REG_CMD, REG_DATA_START, REG_LENGTH
from utils.config import REG_ADDR_HIGH, REG_ADDR_LOW
from utils.config import REG_CRC_LOW, REG_CRC_HIGH, REG_RECOVERY
from utils.config import CMD_BOOTLOADER, CMD_WRITE, CMD_VERIFY, CMD_COMPLETE, RECOVERY_MAGIC
from utils.logger import get_logger


def retry_on_error(max_retries: int = 3):
    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            last_error = None
            for attempt in range(max_retries):
                try:
                    return func(self, *args, **kwargs)
                except Exception as e:
                    last_error = e
                    if attempt < max_retries - 1:
                        self._logger.warning(
                            f"Attempt {attempt + 1}/{max_retries} failed: {e}, retrying..."
                        )
            raise last_error
        return wrapper
    return decorator


class ModbusClient:
    def __init__(
        self,
        port: str,
        slave_id: int,
        baudrate: int = 115200,
        timeout: float = 1.0
    ):
        self._port = port
        self._slave_id = slave_id
        self._config = Config()
        self._logger = get_logger()

        self._instrument = minimalmodbus.Instrument(port, slave_id)
        self._instrument.serial.baudrate = baudrate
        self._instrument.serial.timeout = timeout
        self._instrument.mode = minimalmodbus.MODE_RTU

    @property
    def slave_id(self) -> int:
        return self._slave_id

    @retry_on_error(max_retries=3)
    def read_register(self, address: int, value: int = 0) -> int:
        return self._instrument.read_register(address, value)

    @retry_on_error(max_retries=3)
    def write_register(self, address: int, value: int) -> None:
        self._instrument.write_register(address, value)

    @retry_on_error(max_retries=3)
    def write_registers(self, address: int, values: list) -> None:
        self._instrument.write_registers(address, values)

    def start_bootloader(self) -> None:
        self._logger.info(f"[{self._slave_id}] Starting bootloader")
        self.write_register(REG_CMD, CMD_BOOTLOADER)

    def write_chunk(self, data: bytes, address: int) -> None:
        regs = []
        for i in range(0, len(data), 2):
            if i + 1 < len(data):
                regs.append(data[i] | (data[i + 1] << 8))
            else:
                regs.append(data[i])

        self.write_registers(REG_DATA_START, regs)
        self.write_register(REG_ADDR_HIGH, (address >> 16) & 0xFFFF)
        self.write_register(REG_ADDR_LOW, address & 0xFFFF)
        self.write_register(REG_LENGTH, len(data))
        self.write_register(REG_CMD, CMD_WRITE)

    def verify_crc(self, crc: int) -> None:
        self._logger.info(f"[{self._slave_id}] Verifying CRC: {hex(crc)}")
        self.write_register(REG_CRC_LOW, crc & 0xFFFF)
        self.write_register(REG_CRC_HIGH, (crc >> 16) & 0xFFFF)
        self.write_register(REG_CMD, CMD_VERIFY)

    def set_recovery_flag(self) -> None:
        self.write_register(REG_RECOVERY, RECOVERY_MAGIC)

    def complete(self) -> None:
        self._logger.info(f"[{self._slave_id}] Upload complete")
        self.write_register(REG_CMD, CMD_COMPLETE)

    def ping(self) -> bool:
        try:
            self.read_register(0x0000, 0)
            return True
        except Exception as e:
            self._logger.debug(f"[{self._slave_id}] Ping failed: {e}")
            return False

    def close(self) -> None:
        if self._instrument:
            self._instrument.serial.close()