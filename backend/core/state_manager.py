import json
from dataclasses import dataclass
from typing import Optional

from core.config import STATE_FILE
from utils.logger import get_logger


@dataclass
class UploadState:
    offset: int = 0
    address: int = 0
    device_id: Optional[int] = None
    filename: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "o": self.offset,
            "a": self.address,
            "d": self.device_id,
            "f": self.filename
        }

    @classmethod
    def from_dict(cls, data: dict) -> "UploadState":
        return cls(
            offset=data.get("o", 0),
            address=data.get("a", 0),
            device_id=data.get("d"),
            filename=data.get("f")
        )


class StateManager:
    def __init__(self, state_file: str = STATE_FILE):
        self._state_file = state_file
        self._logger = get_logger()
        self._current_state: Optional[UploadState] = None

    def load(self) -> Optional[UploadState]:
        try:
            with open(self._state_file, "r") as f:
                data = json.load(f)
            self._current_state = UploadState.from_dict(data)
            self._logger.info(f"Loaded state: offset={self._current_state.offset}, addr={self._current_state.address}")
            return self._current_state
        except FileNotFoundError:
            self._logger.info("No saved state found")
            return None
        except Exception as e:
            self._logger.error(f"Failed to load state: {e}")
            return None

    def save(self, offset: int, address: int, device_id: Optional[int] = None, filename: Optional[str] = None) -> None:
        try:
            self._current_state = UploadState(offset, address, device_id, filename)
            with open(self._state_file, "w") as f:
                json.dump(self._current_state.to_dict(), f)
            self._logger.debug(f"Saved state: offset={offset}, addr={hex(address)}")
        except Exception as e:
            self._logger.error(f"Failed to save state: {e}")

    def clear(self) -> None:
        self._current_state = None
        try:
            import os
            if os.path.exists(self._state_file):
                os.remove(self._state_file)
                self._logger.info("State cleared")
        except Exception as e:
            self._logger.error(f"Failed to clear state: {e}")

    def get_current_offset(self) -> int:
        if self._current_state:
            return self._current_state.offset
        return 0

    def get_current_address(self) -> int:
        if self._current_state:
            return self._current_state.address
        return 0