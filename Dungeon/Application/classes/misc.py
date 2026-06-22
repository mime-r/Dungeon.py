import sys
import time

from .. import input as keys
from ..utils import style_text, clear_screen


class DungeonTimeData:
    """Tracks elapsed game time with pause support."""

    def __init__(self, game) -> None:
        self.game = game
        self.start = time.time()
        self.elapsed: float = 0.0

    def add(self) -> None:
        now = time.time()
        self.elapsed += now - self.start
        self.start = now

    def reset(self) -> None:
        self.start = time.time()

    def pause_menu(self) -> None:
        self.add()
        self.game.print(
            f"[menu_header]Paused[/menu_header]\n\n"
            f"{style_text('p', 'controls')} resume\n"
            f"{style_text('S', 'controls')} save game\n"
            f"{style_text('?', 'controls')} manual\n"
            f"{style_text('esc', 'controls')} quit",
            highlight=False,
        )
        while True:
            key = keys.read_key()
            if key == "p":
                self.reset()
                self.game.render()
                break
            if key == "S":
                self.game.save_game()
                self.reset()
                self.game.render()
                break
            if key == "?":
                self.game.manual_screen()
                self.game.render()
                break
            if key == keys.ESC:
                self.game.over = True
                self.game.log.info("game exited by player")
                clear_screen()
                print("Exiting [Dungeon]...")
                sys.exit()
