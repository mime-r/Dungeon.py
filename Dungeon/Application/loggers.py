import os
import sys
import time
from .utils import current_time

cwd = os.getcwd()

applicationName = "dungeon"


class Logger:
    logs_path = os.path.expandvars(fr'{cwd}/logs')

    def __init__(self):
        if not os.path.exists(self.logs_path):
            os.makedirs(self.logs_path)
        self.log_file = os.path.join(self.logs_path, f"{applicationName}-{round(time.time())}.log")

        # init convenient lambdas
        self.info = lambda this: self.log(LogType.INFO,this)
        self.debug = lambda this: self.log(LogType.DEBUG, this)
        self.fatal = lambda this: self.log(LogType.FATAL, this)
        self.time_logged = lambda start, func, end: (
            self.info(f"{start} at {time.time():.2f}"),
            func(),
            self.info(f"{end} at {time.time():.2f}")
        )

    def log(self, log_type, this):
        with open(self.log_file, "a") as f:
            f.write(f"{current_time()} [{log_type}] {this}\n")
        if log_type == "FATAL":
            print(f"[FATAL ERROR]: {this}\n\n[Logs: {self.log_file}]\n{self.get_logs()}\n\n[enter to exit]")
            try:
                import keyboard
                while True:
                    if keyboard.read_key() and keyboard.is_pressed("enter"):
                        break
            except:
                input()
            sys.exit(0)

    def get_logs(self):
        with open(self.log_file, "r") as f:
            logs = f.read()
        return logs

class LogType:
    INFO = "INFO"
    DEBUG = "DEBUG"
    ERROR = "ERROR"
    FATAL = "FATAL"

