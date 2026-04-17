from dataclasses import dataclass
from typing import List


@dataclass
class Config:
    chunk_size: int = 128
    state_file: str = "upload_state.json"
    baudrates: List[str] = None
    max_retries: int = 3
    timeout: float = 1.0
    scan_range_start: int = 1
    scan_range_end: int = 20

    def __post_init__(self):
        if self.baudrates is None:
            self.baudrates = [
                "9600", "19200", "38400", "57600",
                "115200", "230400", "460800", "921600"
            ]


CHUNK_SIZE = 128
STATE_FILE = "upload_state.json"
APP_SLOT_A = 0x08008000
APP_SLOT_B = 0x08018000


REG_CMD = 0x0000
REG_ADDR_HIGH = 0x0001
REG_ADDR_LOW = 0x0002
REG_LENGTH = 0x0003
REG_DATA_START = 0x0010
REG_CRC_LOW = 0x0020
REG_CRC_HIGH = 0x0021
REG_RECOVERY = 0x0030


CMD_BOOTLOADER = 1
CMD_WRITE = 2
CMD_VERIFY = 3
CMD_COMPLETE = 4


RECOVERY_MAGIC = 0xA5A5