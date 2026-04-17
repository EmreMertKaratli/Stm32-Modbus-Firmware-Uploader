import logging
import sys
from typing import Optional
from PySide6.QtCore import QObject, Signal


class LogSignalEmitter(QObject):
    log_message = Signal(str, int)


LOG_LEVELS = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
}


class Logger:
    _instance: Optional["Logger"] = None

    def __init__(self, name: str = "stm32_uploader"):
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

        self.emitter = LogSignalEmitter()
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

    def emit(self, msg: str, level: str = "INFO") -> None:
        level_int = LOG_LEVELS.get(level.upper(), logging.INFO)
        self.emitter.log_message.emit(msg, level_int)


def get_logger() -> Logger:
    return Logger.get()