import logging
import sys
from typing import Optional


class Logger:
    _instance: Optional["Logger"] = None

    def __init__(self, name: str = "stm32_ota"):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)

        if not self.logger.handlers:
            handler = logging.StreamHandler(sys.stdout)
            handler.setFormatter(
                logging.Formatter(
                    "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
                    datefmt="%H:%M:%S"
                )
            )
            self.logger.addHandler(handler)

        Logger._instance = self

    @classmethod
    def get(cls) -> "Logger":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def debug(self, msg: str) -> None:
        self.logger.debug(msg)

    def info(self, msg: str) -> None:
        self.logger.info(msg)

    def warning(self, msg: str) -> None:
        self.logger.warning(msg)

    def error(self, msg: str) -> None:
        self.logger.error(msg)


def get_logger() -> Logger:
    return Logger.get()