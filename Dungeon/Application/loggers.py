import os
import sys
import time

cwd = os.getcwd()

applicationName = "dungeon"


class Logger:
    logs_path = os.path.expandvars(fr'{cwd}\logs')

    def __init__(self):
        if not os.path.exists(self.logs_path):
            os.makedirs(self.logs_path)
        self.log_file = os.path.join(
            self.logs_path, f"{applicationName}{round(time.time())}.log")

    def log(self, this):
        with open(self.log_file, "a") as f:
            f.write(f"{round(time.time())} [LOG] {this}\n")
        #print(f"[LOG] {this}")

    def fatal(self, this):
        input(
            f"[FATAL ERROR]: {this}\n\n[Logs: {self.log_file}]\n{self.get_logs()}\n\n[enter to exit]")
        sys.exit(-1)

    def get_logs(self):
        with open(self.log_file, "r") as f:
            logs = f.read()
        return logs
