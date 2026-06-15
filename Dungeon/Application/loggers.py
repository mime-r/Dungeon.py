import sys
import time
from enum import Enum
from pathlib import Path

from .utils import current_time

_APPLICATION_NAME = "dungeon"


class LogType(str, Enum):
    INFO = "INFO"
    DEBUG = "DEBUG"
    ERROR = "ERROR"
    FATAL = "FATAL"


class Logger:
    logs_path: Path = Path.cwd() / "logs"

    def __init__(self) -> None:
        self.logs_path.mkdir(parents=True, exist_ok=True)
        self.log_file: Path = self.logs_path / f"{_APPLICATION_NAME}-{round(time.time())}.log"

    def info(self, message: str) -> None:
        self.log(LogType.INFO, message)

    def debug(self, message: str) -> None:
        self.log(LogType.DEBUG, message)

    def fatal(self, message: str) -> None:
        self.log(LogType.FATAL, message)

    def time_logged(self, start: str, func, end: str) -> None:
        self.info(f"{start} at {time.time():.2f}")
        func()
        self.info(f"{end} at {time.time():.2f}")

    def log(self, log_type: LogType, message: str) -> None:
        with open(self.log_file, "a") as f:
            f.write(f"{current_time()} [{log_type}] {message}\n")
        if log_type == LogType.FATAL:
            print(f"[FATAL ERROR]: {message}\n\n[Logs: {self.log_file}]\n{self.get_logs()}\n\n[press any key to exit]")
            try:
                from . import input as keys
                keys.read_key()
            except Exception:
                try:
                    input()
                except Exception:
                    pass
            sys.exit(0)

    def get_logs(self) -> str:
        with open(self.log_file, "r") as f:
            return f.read()
