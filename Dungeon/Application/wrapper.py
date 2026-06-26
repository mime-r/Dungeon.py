import time
import sys
import webbrowser

from rich.console import Console
from rich.theme import Theme

from . import input as keys
from .config import config
from .utils import style_text, clear_screen
from .main import Dungeon, _read_save_state

# Centralised so the splash and any future /about panel can share it.
try:
    from __version__ import __version__
except ImportError:  # pragma: no cover - dev shim
    __version__ = "dev"

_GITHUB_URL = "https://github.com/mime-r/dungeon.py"


class GameWrapper:
    """Displays the splash screen and routes input to start, resume, or exit."""

    def __init__(self, logger) -> None:
        self.logger = logger
        self.rich_console = Console(theme=Theme(config.styles))
        self.print = self.rich_console.print

        clear_screen()
        self._render_banner()
        save_state = _read_save_state()
        self._render_menu(save_state)
        self._input_loop(logger, save_state)

    # --- presentation ------------------------------------------------------

    def _render_banner(self) -> None:
        # Title card.
        self.print(
            r"""
[bold #FF4444]      _                                              [/bold #FF4444]
[bold #FF9E2C]     | |                                             [/bold #FF9E2C]
[bold #FFE066]   __| | _   _  _ __    __ _   ___   ___   _ __     [/bold #FFE066]
[bold #70D2FF]  / _` || | | || '_ \  / _` | / _ \ / _ \ | '_ \    [/bold #70D2FF]
[bold #6BE0FF] | (_| || |_| || | | || (_| ||  __/| (_) || | | |   [/bold #6BE0FF]
[bold #C77DFF]  \__,_| \__,_||_| |_| \__, | \___| \___/ |_| |_|   [/bold #C77DFF]
[bold #C77DFF]                      __/ |                       [/bold #C77DFF]
[bold #C77DFF]                     |___/                        [/bold #C77DFF]
""",
            highlight=False,
        )
        # Tagline + version.
        self.print(
            f"\n[bold #FF9E2C]A turn-based roguelike in the spirit of Dungeon Crawl Stone Soup.[/bold #FF9E2C]"
            f"  [flavor]v{__version__}[/flavor]\n",
            highlight=False,
        )
        # Elevator pitch.
        self.print(
            "[flavor]Descend eight floors of a procedurally generated dungeon, slay the three[/flavor]\n"
            "[flavor]boss-tiers guarding the [bold #FFE066]Shards of the Broken Sigil[/bold #FFE066], and escape to the surface alive.[/flavor]\n",
            highlight=False,
        )
        # Feature highlights.
        self.print(
            "  [success]•[/success] [name]531 monsters[/name] - dragons, demons, liches, slimes, and more\n"
            "  [success]•[/success] [name]Spell-casting AI[/name] - oracles, pyromancers, liches, summoners\n"
            "  [success]•[/success] [name]Cone breath weapons[/name] - fire, ice, lightning, poison, acid, steam\n"
            "  [success]•[/success] [name]21 spells, 15 brands, 7 armour egos, 19 scrolls[/name]\n"
            "  [success]•[/success] [name]Optional AI features[/name] - biome themes, DM hints, item lore\n",
            highlight=False,
        )

    def _render_menu(self, save_state) -> None:
        # Resume line (only if a save exists).
        resume_text = ""
        if save_state is not None:
            sd = save_state.get("player", {})
            depth = save_state.get("depth", "?")
            hp = sd.get("health", "?")
            max_hp = sd.get("max_health", "?")
            shards = len(sd.get("shards", []))
            resume_text = (
                f"  {style_text('r', 'controls')}  {style_text('resume', 'action')}"
                f"    depth {depth}    HP {hp}/{max_hp}    shards {shards}/3\n"
            )
        # Tip line beneath the menu.
        tip = (
            f"  [flavor]Tip: enter the dungeon from a cleared room. "
            f"Search walls ([/flavor]{style_text('s', 'controls')}[flavor]) for secrets, "
            f"and use ranged weapons ([/flavor]{style_text('f', 'controls')}[flavor]) to soften tough foes.[/flavor]\n"
        )
        self.print(
            "\n[menu_header]Main Menu[/menu_header]\n"
            f"  {style_text('enter', 'controls')}  {style_text('start a new run', 'action')}\n"
            + resume_text
            + f"  {style_text('g', 'controls')}  {style_text('open the project on GitHub', 'action')}\n"
            f"  {style_text('esc', 'controls')}  {style_text('exit', 'action')}\n"
            + tip,
            highlight=False,
        )

    # --- input loop --------------------------------------------------------

    def _input_loop(self, logger, save_state) -> None:
        while True:
            key = keys.read_key()
            if key == keys.ENTER:
                time.sleep(0.1)
                Dungeon.__start__(logger=logger, rich_console=self.rich_console)
                return
            if key == "r" and save_state is not None:
                time.sleep(0.1)
                Dungeon.__start__(
                    logger=logger,
                    rich_console=self.rich_console,
                    load_state=save_state,
                )
                return
            if key == "g" or key == "G":
                self._open_github()
                # Re-render so the prompt is still visible after the browser steals focus.
                self._rerender(save_state)
                continue
            if key == keys.ESC:
                print("Exiting [Dungeon]...")
                logger.info(f"game exited at {time.time():.2f}")
                sys.exit()

    def _open_github(self) -> None:
        try:
            opened = webbrowser.open(_GITHUB_URL, new=2, autoraise=True)
        except Exception as exc:
            self.logger.info(f"could not open browser: {exc}")
            opened = False
        if opened:
            self.print(
                f"\n  [success]Opening[/success] [name]{_GITHUB_URL}[/name] [success]in your browser.[/success]\n",
                highlight=False,
            )
        else:
            self.print(
                f"\n  [warn]Could not launch a browser. Visit:[/warn] [name]{_GITHUB_URL}[/name]\n",
                highlight=False,
            )

    def _rerender(self, save_state) -> None:
        # The browser steals focus; redraw so the menu is on screen when the
        # user comes back.
        clear_screen()
        self._render_banner()
        self._render_menu(save_state)
