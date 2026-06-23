"""The on-screen HUD: map panel, hero sidebar, and a scrolling message log."""

from collections import deque

from rich.text import Text
from rich.panel import Panel
from rich.table import Table

from ..config import config
from .status import EFFECT_STYLE


def _enemy_status_suffix(enemy) -> str:
    """Return a comma-separated list of human status labels for an enemy.

    Example: 'poisoned, slowed'. Returns '' when the enemy has no status.
    Used in the sidebar to make slowed / poisoned / burning etc. visible at a glance.
    """
    names = []
    for effect_name in enemy.status.effects:
        entry = EFFECT_STYLE.get(effect_name)
        label = entry[0] if entry else effect_name.title()
        names.append(label.lower())
    return ", ".join(names)


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
        size = self.console.size
        H, W = size.height, size.width

        controls_groups = self._controls()
        wrapped_controls = self._wrap_controls(controls_groups, W - 2)
        controls_h = max(1, len(wrapped_controls))

        # Size the whole frame to fit the current window so nothing scrolls the header
        # off the top. The map keeps its configured size (view_width x view_height)
        # whenever it fits; the message log absorbs the leftover space and only the log
        # shrinks on short windows. Layout: header(1) + map/sidebar row + log + controls(N),
        # plus borders and a one-line safety margin.
        chrome = 1 + 2 + 2 + controls_h + 1    # header, map borders, log borders, controls, margin
        view_h = max(4, min(config.map.view_height, H - chrome - 2))
        log_view = max(1, min(self.LOG_VIEW, H - chrome - view_h))
        view_w = max(12, min(config.map.view_width, W - 40))
        panel_h = view_h + 2                  # map and sidebar share this height

        grid = Table.grid(padding=(0, 1))
        grid.add_column()
        grid.add_column()
        grid.add_row(self._map_panel(view_w, view_h), self._sidebar_panel(panel_h))

        self.console.print(self._header(), highlight=False, no_wrap=True, crop=True)
        self.console.print(grid)
        self.console.print(self._log_panel(log_view))
        for line in wrapped_controls:
            self.console.print(line, highlight=False)

    def _header(self) -> Text:
        g = self.game
        elapsed = g.time.elapsed if getattr(g, "time", None) else 0.0
        god = "   [warn]<< GOD MODE >>[/warn]" if getattr(g, "godmode", False) else ""
        return Text.from_markup(
            f"[game_header]DUNGEON.PY[/game_header]   "
            f"[depth]Depth {g.depth}/{config.depth.floors}[/depth]"
            + (f" [flavor]— {_t.name}[/flavor]" if (_t := getattr(g, '_floor_themes', {}).get(g.depth)) and _t.name else "")
            + "   "
            f"[move_count]Turn {g.moves}[/move_count]   "
            f"[time_count]{elapsed:.1f}s[/time_count]{god}"
        )

    def _map_panel(self, view_w: int, view_h: int) -> Panel:
        text = Text(no_wrap=True, overflow="crop")
        rows = self.game.map.render_grid(view_w, view_h)
        for i, row in enumerate(rows):
            for ch, style in row:
                text.append(ch, style=style)
            if i != len(rows) - 1:
                text.append("\n")
        return Panel(text, border_style="grey37", padding=(0, 1), height=view_h + 2)

    def _sidebar_panel(self, height: int | None = None) -> Panel:
        p = self.game.player
        ratio = p.health / p.max_health if p.max_health else 0
        bar_w = 12
        filled = max(0, min(bar_w, round(ratio * bar_w)))
        bar_color = "hp_bar" if ratio > 0.33 else "hp_bar_low"
        bar = f"[{bar_color}]{'█' * filled}[/{bar_color}][grey23]{'░' * (bar_w - filled)}[/grey23]"

        shard_count = len(p.shards)
        if shard_count == 3:
            objective = "[shard]Sigil: escape to the surface![/shard]"
        elif shard_count > 0:
            objective = f"[shard]Sigil: {shard_count}/3[/shard] [flavor]({', '.join(p.shards)})[/flavor]"
        else:
            objective = ""

        inventory = getattr(p, "inventory", [])
        full = len(inventory) >= p.max_inventory
        background = f" [flavor]{p.background}[/flavor]" if getattr(p, "background", None) else ""
        lines = [
            f"[name]{p.name or 'Adventurer'}[/name]{background}",
            f"[level]Lv {p.level}[/level] [xp_count]{p.xp}/{p.xp_next}xp[/xp_count] [depth]D{self.game.depth}[/depth] [coin]{p.coins}g[/coin]",
            f"[health]HP[/health] {p.health}/{p.max_health} {bar}",
        ]
        if getattr(p, "max_mp", 0) > 0:
            mp_ratio = p.mp / p.max_mp if p.max_mp else 0
            mp_filled = max(0, min(bar_w, round(mp_ratio * bar_w)))
            mp_bar = f"[haste]{'█' * mp_filled}[/haste][grey23]{'░' * (bar_w - mp_filled)}[/grey23]"
            lines.append(f"[haste]MP[/haste] {int(p.mp)}/{p.max_mp} {mp_bar}")
        if p.status.any():
            tags = ", ".join(f"[{s}]{lbl}[/{s}]" for lbl, s in p.status.summary())
            lines.append(f"[warn]Status[/warn]: {tags}")
        weapon_tag = f"[weapons]{self.game.display_name(p.equipped)}[/weapons]"
        if getattr(p.equipped, "ranged", False):
            weapon_tag += f" [flavor](rng {p.equipped.range})[/flavor]"
        lines.append(
            f"{weapon_tag}  [armour]AC {p.armor_class()}[/armour]  [armour]EV {p.evasion()}[/armour]"
        )
        pack_str = f"[inventory]Pack[/inventory] {len(inventory)}/{p.max_inventory}"
        if full:
            pack_str += " [warn]FULL[/warn]"
        if shard_count > 0:
            pack_str += f"  [shard]+{shard_count}★[/shard]"
        lines.append(pack_str)
        if objective:
            lines.append(objective)

        summons = self.game.map.visible_summons()
        if summons:
            lines.append("[haste]Summons[/haste]: " + ", ".join(
                f"[{s.style}]{s.name}[/{s.style}] {s.health}/{s.max_health}({max(0, s.despawn_timer)}t)"
                for s in summons
            ))

        enemies = self.game.map.visible_enemies()
        if enemies:
            threats = []
            for e in enemies[:6]:
                t = f"[{e.style}]{e.name}[/{e.style}] {e.health}/{e.max_health}"
                statuses = _enemy_status_suffix(e)
                if statuses:
                    t += f" [flavor]({statuses})[/flavor]"
                threats.append(t)
            lines.append("[enemy]Threats[/enemy]: " + " | ".join(threats))
            if len(enemies) > 6:
                lines.append(f"[flavor]+{len(enemies) - 6} more[/flavor]")

        npcs = self.game.map.visible_npcs()
        if npcs:
            lines += ["", "[occupation]People in view[/occupation]:"]
            for n in npcs[:4]:
                lines.append(f"  [{n.style}]{n.symbol}[/{n.style}] {n.name} [flavor]({n.occupation})[/flavor]")

        return Panel(Text.from_markup("\n".join(lines), overflow="crop"),
                     title="[menu_header]Hero[/menu_header]",
                     border_style="grey37", width=34, height=height)

    def _log_panel(self, log_view: int | None = None) -> Panel:
        log_view = log_view or self.LOG_VIEW
        recent = list(self.messages)[-log_view:]
        body = "\n".join(recent) if recent else "[flavor]The dungeon is silent...[/flavor]"
        text = Text.from_markup(body, overflow="crop")
        return Panel(text, title="[menu_header]Messages[/menu_header]",
                     border_style="grey37", height=log_view + 2)

    def _controls(self) -> list[str]:
        return [
            "[controls]move[/controls] arrows/hjkl/yubn",
            "[controls]f[/controls] fire",
            "[controls]g[/controls] pick up",
            "[controls]A[/controls] armour",
            "[controls]i[/controls] pack",
            "[controls]m[/controls] skills",
            "[controls]z[/controls] spells",
            "[controls]o[/controls] explore",
            "[controls]>[/controls]/[controls]<[/controls] stairs",
            "[controls]G[/controls] goto-stairs",
            "[controls][[/controls]/[controls]][/controls] view stairs",
            "[controls]X[/controls] exclude",
            "[controls]\\\\[/controls] pickup-cfg",
            "[controls]x[/controls] examine",
            "[controls]s[/controls] search",
            "[controls]S[/controls] save",
            "[flavor]restart to restore[/flavor]",
            "[controls].[/controls] wait",
            "[controls]?[/controls] help",
            "[controls]esc[/controls] quit",
        ]

    @staticmethod
    def _wrap_controls(groups: list[str], width: int) -> list[str]:
        lines: list[str] = []
        current = ""
        for group in groups:
            candidate = (current + "   " + group) if current else group
            if Text.from_markup(candidate).cell_len > width:
                if current:
                    lines.append(current)
                current = group
            else:
                current = candidate
        if current:
            lines.append(current)
        return lines
