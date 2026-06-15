"""The on-screen HUD: map panel, hero sidebar, and a scrolling message log."""

from collections import deque

from rich.text import Text
from rich.panel import Panel
from rich.table import Table

from ..config import config


class DungeonUI:
    """Owns the message log and renders the full game frame each turn."""

    LOG_VIEW = 8          # message lines shown
    LOG_HISTORY = 200     # messages remembered

    def __init__(self, game) -> None:
        self.game = game
        self.console = game.rich_console
        self.messages: deque[str] = deque(maxlen=self.LOG_HISTORY)

    def message(self, text: str, drop: int | None = None) -> None:
        if drop:
            text = f"{text} [hp_drop](-{drop})[/hp_drop]"
        self.messages.append(text)

    # --- frame ----------------------------------------------------------
    def render(self) -> None:
        self.console.clear()
        self.console.print(self._header(), highlight=False)
        grid = Table.grid(padding=(0, 1))
        grid.add_column()
        grid.add_column()
        grid.add_row(self._map_panel(), self._sidebar_panel())
        self.console.print(grid)
        self.console.print(self._log_panel())
        self.console.print(self._controls(), highlight=False)

    def _header(self) -> Text:
        g = self.game
        elapsed = g.time.elapsed if getattr(g, "time", None) else 0.0
        god = "   [warn]<< GOD MODE >>[/warn]" if getattr(g, "godmode", False) else ""
        return Text.from_markup(
            f"[game_header]DUNGEON.PY[/game_header]   "
            f"[depth]Depth {g.depth}/{config.depth.floors}[/depth]   "
            f"[move_count]Turn {g.moves}[/move_count]   "
            f"[time_count]{elapsed:.1f}s[/time_count]{god}"
        )

    def _map_panel(self) -> Panel:
        text = Text(no_wrap=True, overflow="crop")
        rows = self.game.map.render_grid()
        for i, row in enumerate(rows):
            for ch, style in row:
                text.append(ch, style=style)
            if i != len(rows) - 1:
                text.append("\n")
        return Panel(text, border_style="grey37", padding=(0, 1))

    def _sidebar_panel(self) -> Panel:
        p = self.game.player
        ratio = p.health / p.max_health if p.max_health else 0
        bar_w = 16
        filled = max(0, min(bar_w, round(ratio * bar_w)))
        bar_color = "hp_bar" if ratio > 0.33 else "hp_bar_low"
        bar = f"[{bar_color}]{'█' * filled}[/{bar_color}][grey23]{'░' * (bar_w - filled)}[/grey23]"

        if p.has_orb:
            objective = "[orb]Carry the Orb to the surface![/orb]\n[warn]Find up-stairs (<) on Depth 1.[/warn]"
        else:
            objective = "[item]Descend to find the Orb of Zot.[/item]\n[stairs]Take down-stairs (>) ever deeper.[/stairs]"

        full = len(p.inventory) >= p.max_inventory
        pack_line = (
            f"[inventory]Pack[/inventory]: {len(p.inventory)}/{p.max_inventory}"
            + ("  [warn]FULL[/warn]" if full else "")
            + ("  [orb]+Orb[/orb]" if p.has_orb else "")
        )
        lines = [
            f"[name]{p.name or 'Adventurer'}[/name]",
            "",
            f"[health]HP[/health] {p.health}/{p.max_health}",
            bar,
            f"[xp_count]XP[/xp_count]    {p.xp}",
            f"[coin]Gold[/coin]  {p.coins}",
            f"[depth]Depth[/depth] {self.game.depth}",
            "",
            f"[weapons]Weapon[/weapons]: {p.equipped.name}",
            pack_line,
            "",
            objective,
        ]

        enemies = self.game.map.visible_enemies()
        if enemies:
            lines += ["", "[enemy]Threats in view[/enemy]:"]
            for e in enemies[:6]:
                lines.append(f"  [{e.style}]{e.symbol} {e.name}[/{e.style}] {e.health}/{e.max_health}")
            if len(enemies) > 6:
                lines.append(f"  [flavor]+{len(enemies) - 6} more[/flavor]")

        npcs = self.game.map.visible_npcs()
        if npcs:
            lines += ["", "[occupation]People in view[/occupation]:"]
            for n in npcs[:4]:
                lines.append(f"  [{n.style}]{n.symbol}[/{n.style}] {n.name} [flavor]({n.occupation})[/flavor]")

        return Panel(Text.from_markup("\n".join(lines)), title="[menu_header]Hero[/menu_header]",
                     border_style="grey37", width=34)

    def _log_panel(self) -> Panel:
        recent = list(self.messages)[-self.LOG_VIEW:]
        body = "\n".join(recent) if recent else "[flavor]The dungeon is silent...[/flavor]"
        text = Text.from_markup(body)
        return Panel(text, title="[menu_header]Messages[/menu_header]",
                     border_style="grey37", height=self.LOG_VIEW + 2)

    def _controls(self) -> Text:
        return Text.from_markup(
            "[controls]move[/controls] arrows/hjkl/yubn   "
            "[controls]g[/controls] pick up   [controls]i[/controls] pack (use/equip/drop)   "
            "[controls]>[/controls]/[controls]<[/controls] stairs   "
            "[controls]s[/controls] search   [controls].[/controls] wait   "
            "[controls]p[/controls] pause   [controls]?[/controls] help   [controls]esc[/controls] quit"
        )
