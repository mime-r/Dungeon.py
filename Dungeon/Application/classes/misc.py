import time

from .. import input as keys
from ..utils import style_text


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
            f"\n[move_count]Game paused.[/move_count] "
            f"Press {style_text('p', 'controls')} to {style_text('resume', 'action')}.",
            highlight=False,
        )
        while True:
            if keys.read_key() == "p":
                self.reset()
                self.game.render()
                break
