import os
import datetime
import platform


def style_text(t: object, s: str) -> str:
    return f"[{s}]{t}[/{s}]"


def controls_style(t: str) -> str:
    return style_text(chr(92) + f"[{t}]", "controls")


def current_time() -> str:
    return datetime.datetime.now().strftime("%Y-%m-%d %T")


def clear_screen() -> int:
    return os.system("cls" if platform.system() == "Windows" else "clear")
