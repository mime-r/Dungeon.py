import time
import sys

from rich.console import Console
from rich.theme import Theme

from . import input as keys
from .config import config
from .utils import style_text, clear_screen
from .main import Dungeon


class GameWrapper:
    """Displays the splash screen and routes input to start or exit."""

    def __init__(self, logger) -> None:
        self.logger = logger
        self.rich_console = Console(theme=Theme(config.styles))
        self.print = self.rich_console.print

        clear_screen()
        self.print(
            r"""
      _
     | |
   __| | _   _  _ __    __ _   ___   ___   _ __
  / _` || | | || '_ \  / _` | / _ \ / _ \ | '_ \
 | (_| || |_| || | | || (_| ||  __/| (_) || | | |
  \__,_| \__,_||_| |_| \__, | \___| \___/ |_| |_|
                        __/ |
                       |___/
""",
            highlight=False,
        )
        self.print(
            "[flavor]Descend the dungeon, claim the Orb of Zot, and escape to the surface.[/flavor]\n\n"
            f"Press {style_text('enter', 'controls')} to {style_text('start', 'action')}.\n"
            f"Press {style_text('esc', 'controls')} to {style_text('exit', 'action')}.\n",
            highlight=False,
        )
        while True:
            key = keys.read_key()
            if key == keys.ENTER:
                time.sleep(0.1)
                Dungeon.__start__(logger=self.logger, rich_console=self.rich_console)
                break
            if key == keys.ESC:
                print("Exiting [Dungeon]...")
                self.logger.info(f"game exited at {time.time():.2f}")
                sys.exit()
