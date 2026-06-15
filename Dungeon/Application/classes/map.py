# -*- coding: utf-8 -*-
"""Map model and the player entity.

A floor is a matrix of :class:`DungeonCell`. Each cell has a *terrain* (floor / wall /
door / stairs), an optional living *occupant* (enemy or NPC), ground *items*, and a
*gold* pile. The player is tracked separately by location and drawn on top.
"""

import random

from ..utils import style_text
from ..config import config
from .status import StatusSet

T = config.terrain

DIRS = {
    "n": (-1, 0), "s": (1, 0), "w": (0, -1), "e": (0, 1),
    "ne": (-1, 1), "nw": (-1, -1), "se": (1, 1), "sw": (1, -1),
}


class DungeonCell:
    """A single tile: terrain, an optional occupant, ground items and gold."""

    def __init__(self, game, terrain: str) -> None:
        self.game = game
        self.terrain = terrain
        self.occupant = None
        self.items: list = []
        self.gold: int = 0
        self.explored: bool = False
        self.trap: str | None = None       # trap kind, or None
        self.trap_hidden: bool = True       # hidden until triggered or searched
        self.feature: str | None = None    # a static feature such as "altar"

    @property
    def object(self):
        return self.items[-1] if self.items else None

    @property
    def walkable(self) -> bool:
        return self.terrain in T.walkable

    def item_pickup(self):
        return self.items.pop() if self.items else None


class DungeonPlayer:
    """The player character: position, health, inventory and bump-to-attack combat."""

    def __init__(self, health, max_health, max_inventory, coins, xp, equipped, game) -> None:
        self.health = health
        self.max_health = max_health
        self.xp = xp
        self.coins = coins
        self.inventory: list = []
        self.max_inventory = max_inventory
        self.equipped = equipped
        self.location: tuple[int, int] = (0, 0)
        self.name: str | None = None
        self.background: str | None = None
        self.has_orb: bool = False
        self.game = game
        # progression
        self.level = 1
        self.xp = 0
        self.xp_next = config.progression.xp_for(1)
        # status + turn economy
        self.status = StatusSet()
        self.energy = 0
        self.speed = 10

    def effective_speed(self) -> int:
        s = self.speed
        if self.status.has("haste"):
            s += 5
        if self.status.has("slow"):
            s -= 5
        return max(1, s)

    def combat_bonus(self) -> tuple[int, int]:
        """Return (damage_bonus, accuracy_bonus) from level and Might."""
        prog = config.progression
        dmg = self.level // prog.damage_every + self.status.potency("might")
        acc = self.level * prog.accuracy_per_level
        return dmg, acc

    def gain_xp(self, amount: int) -> None:
        self.xp += amount
        while self.xp >= self.xp_next:
            self.xp -= self.xp_next
            self.level += 1
            self.xp_next = config.progression.xp_for(self.level)
            gain = config.progression.hp_per_level
            self.max_health += gain
            self.health += gain
            self.game.message(
                f"[level]Welcome to level {self.level}![/level] [health](+{gain} max HP)[/health]")

    @property
    def x(self) -> int:
        return self.location[1]

    @property
    def y(self) -> int:
        return self.location[0]

    @property
    def cell(self) -> DungeonCell:
        return self.game.map.matrix[self.y][self.x]

    def move(self, direction: str) -> bool:
        """Attempt to act in a direction. Returns True if a turn was spent."""
        dy, dx = DIRS[direction]
        ny, nx = self.y + dy, self.x + dx
        game = self.game
        if not game.map.in_bounds(ny, nx):
            return False
        cell = game.map.matrix[ny][nx]

        if cell.occupant is not None:
            if getattr(cell.occupant, "is_enemy", False):
                self.attack(cell.occupant)
                return True
            return game.interact_npc(cell.occupant)  # bump an NPC to trade/heal or step past

        if cell.terrain == T.DOOR_CLOSED:
            cell.terrain = T.DOOR_OPEN
            game.message("You open the door.")
            return True
        if cell.terrain in T.blocks_sight:  # wall or undiscovered secret door
            return False
        if not cell.walkable:
            return False

        self.location = (ny, nx)
        self._on_enter(cell)
        return True

    def _on_enter(self, cell: DungeonCell) -> None:
        game = self.game
        if cell.trap and cell.trap_hidden:
            game.trigger_trap(cell)
        if cell.feature == "altar":
            game.bless_at_altar(cell)
        if cell.gold > 0:
            game.player.coins += cell.gold
            game.message(f"You pick up {style_text(str(cell.gold) + ' gold', 'gold')}.")
            cell.gold = 0
        if cell.items:
            game.map.announce_items(cell)
        if cell.terrain == T.STAIRS_DOWN:
            game.message(f"There is a staircase {style_text('down', 'stairs')} here. Press {style_text('>', 'controls')}.")
        elif cell.terrain == T.STAIRS_UP:
            game.message(f"There is a staircase {style_text('up', 'stairs')} here. Press {style_text('<', 'controls')}.")

    def attack(self, enemy) -> None:
        weapon = self.equipped
        enemy_name = style_text(enemy.name, "enemy")
        weapon_name = style_text(weapon.name, "weapons")
        if self.game.godmode:
            self.game.message(f"[warn][GOD][/warn] You annihilate the {enemy_name}.")
            enemy.health = 0
            self.game.on_enemy_death(enemy)
            return
        dmg_bonus, acc_bonus = self.combat_bonus()
        if random.randint(1, 100) <= weapon.accuracy + acc_bonus:
            raw = random.randint(weapon.attack_range[0], weapon.attack_range[1])
            damage = max(1, weapon.base_attack + raw + dmg_bonus)
            crit = raw == weapon.attack_range[1]
            template = weapon.texts.critical_hit if crit else weapon.texts.hit
            self.game.message(template.format(enemy_name, weapon_name), drop=damage)
            enemy.health -= damage
            if enemy.health <= 0:
                self.game.on_enemy_death(enemy)
        else:
            self.game.message(weapon.texts.missed_hit.format(enemy_name, weapon_name))

    def print_inventory(self) -> None:
        p = self.game.print
        p(f"Inventory ({len(self.inventory)} / {self.max_inventory})", style="inventory", highlight=False)
        p(f"Health: ({self.health} / {self.max_health})", style="health", highlight=False)
        p(f"Coins: {self.coins}\n", style="coin", highlight=False)
        if not self.inventory:
            p("You have nothing in your inventory.\n", highlight=False)
        else:
            for index, item in enumerate(self.inventory):
                p(f"{index + 1}: {style_text(item.name, 'item')}\n\t{item.description}")


class DungeonMap:
    """One dungeon floor: a matrix of cells plus structural anchors and fog-of-war."""

    def __init__(self, game, layout) -> None:
        self.game = game
        self.width = layout.width
        self.height = layout.height
        self.max_y = layout.height - 1
        self.max_x = layout.width - 1
        self.matrix: list[list[DungeonCell]] = [
            [DungeonCell(game=game, terrain=terrain) for terrain in row]
            for row in layout.terrain
        ]
        self.rooms = layout.rooms
        self.stairs_up = layout.stairs_up
        self.stairs_down = layout.stairs_down
        self.vault_cells = layout.vault_cells
        self.temple_cells = layout.temple_cells
        self.altar = layout.altar
        self.floor_cells = layout.floor_cells
        self.enemies: list = []
        self.npcs: list = []
        self.visible: set[tuple[int, int]] = set()
        if self.altar:
            ay, ax = self.altar
            self.matrix[ay][ax].feature = "altar"

    # --- geometry -------------------------------------------------------
    def in_bounds(self, y: int, x: int) -> bool:
        return 0 <= y <= self.max_y and 0 <= x <= self.max_x

    def cell(self, y: int, x: int) -> DungeonCell:
        return self.matrix[y][x]

    def random_walkable(self, exclude=None) -> tuple[int, int]:
        exclude = exclude or set()
        candidates = [
            (y, x) for (y, x) in self.floor_cells
            if self.matrix[y][x].occupant is None
            and (y, x) not in exclude
            and (y, x) != self.game.player.location
        ]
        return random.choice(candidates) if candidates else self.stairs_up

    # --- occupants ------------------------------------------------------
    def place_occupant(self, entity, y: int, x: int) -> None:
        self.matrix[y][x].occupant = entity
        entity.location = (y, x)

    def remove_occupant(self, entity) -> None:
        y, x = entity.location
        if self.matrix[y][x].occupant is entity:
            self.matrix[y][x].occupant = None

    def move_occupant(self, entity, ny: int, nx: int) -> None:
        self.remove_occupant(entity)
        self.place_occupant(entity, ny, nx)

    def announce_items(self, cell: DungeonCell) -> None:
        items = cell.items
        if not items:
            return
        name = self.game.display_name
        if len(items) == 1:
            label = style_text(name(items[0]), "item")
        else:
            label = "{} and {}".format(
                ", ".join(style_text(name(i), "item") for i in items[:-1]),
                style_text(name(items[-1]), "item"),
            )
        self.game.message(f"You see {label} here.")

    # --- fog of war -----------------------------------------------------
    def update_fov(self) -> None:
        self.visible = set()
        py, px = self.game.player.location
        r = config.depth.sight_radius
        for y in range(max(0, py - r), min(self.max_y, py + r) + 1):
            for x in range(max(0, px - r), min(self.max_x, px + r) + 1):
                if (y - py) ** 2 + (x - px) ** 2 > r * r:
                    continue
                if self._line_of_sight(py, px, y, x):
                    self.visible.add((y, x))
                    self.matrix[y][x].explored = True

    def _line_of_sight(self, y0, x0, y1, x1) -> bool:
        for (y, x) in _bresenham(y0, x0, y1, x1)[1:-1]:
            if self.matrix[y][x].terrain in T.blocks_sight:
                return False
        return True

    def line_points(self, y0, x0, y1, x1) -> list[tuple[int, int]]:
        return _bresenham(y0, x0, y1, x1)

    def reveal_all(self) -> None:
        for row in self.matrix:
            for cell in row:
                cell.explored = True

    def visible_enemies(self) -> list:
        god = getattr(self.game, "godmode", False)
        return [e for e in self.enemies if god or (e.y, e.x) in self.visible]

    def visible_npcs(self) -> list:
        god = getattr(self.game, "godmode", False)
        return [n for n in self.npcs if god or n.location in self.visible]

    def search(self, y: int, x: int) -> bool:
        found = False
        for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (-1, 1), (1, -1), (1, 1)):
            ny, nx = y + dy, x + dx
            if not self.in_bounds(ny, nx):
                continue
            cell = self.matrix[ny][nx]
            if cell.terrain == T.SECRET_DOOR:
                cell.terrain = T.DOOR_CLOSED
                found = True
            if cell.trap and cell.trap_hidden:
                cell.trap_hidden = False
                found = True
        return found

    def auto_detect_secret(self) -> str | None:
        """Chance to notice an adjacent secret door or trap; returns 'door'/'trap'/None."""
        py, px = self.game.player.location
        for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            ny, nx = py + dy, px + dx
            if not self.in_bounds(ny, nx):
                continue
            cell = self.matrix[ny][nx]
            if cell.terrain == T.SECRET_DOOR and random.randint(1, 4) == 1:
                cell.terrain = T.DOOR_CLOSED
                return "door"
            if cell.trap and cell.trap_hidden and random.randint(1, 3) == 1:
                cell.trap_hidden = False
                return "trap"
        return None

    # --- rendering ------------------------------------------------------
    def viewport(self, view_w: int, view_h: int) -> tuple[int, int, int, int]:
        """Window onto the map, centred on the player and clamped to bounds.
        Returns (top, left, height, width)."""
        vw = max(1, min(view_w, self.width))
        vh = max(1, min(view_h, self.height))
        py, px = self.game.player.location
        top = max(0, min(py - vh // 2, self.height - vh))
        left = max(0, min(px - vw // 2, self.width - vw))
        return top, left, vh, vw

    def render_grid(self, view_w: int | None = None, view_h: int | None = None
                    ) -> list[list[tuple[str, str]]]:
        """Return rows of (glyph, literal-rich-style) tuples for a scrolling window of
        the map, centred on the player."""
        styles = config.styles
        god = getattr(self.game, "godmode", False)
        player_loc = self.game.player.location
        cursor = getattr(self.game, "target_cursor", None)
        path = getattr(self.game, "target_path", None) or ()
        path_set = set(path)
        top, left, vh, vw = self.viewport(
            view_w or config.map.view_width, view_h or config.map.view_height)
        rows = []
        for y in range(top, top + vh):
            out = []
            for x in range(left, left + vw):
                cell = self.matrix[y][x]
                visible = (y, x) in self.visible or god
                if not cell.explored and not visible:
                    out.append((config.symbols.unknown, styles["unknown"]))
                    continue
                glyph, name = self._glyph(cell, y, x, player_loc, visible)
                style = styles.get(name, name)
                if not visible:
                    style = "dim " + style
                if cursor is not None:
                    if (y, x) == cursor:
                        style = styles["target"]
                    elif (y, x) in path_set:
                        style = styles["target_path"]
                out.append((glyph, style))
            rows.append(out)
        return rows

    def _glyph(self, cell, y, x, player_loc, visible):
        if (y, x) == player_loc:
            return config.symbols.player, "player"
        if visible and cell.occupant is not None:
            occ = cell.occupant
            return occ.symbol, getattr(occ, "style", "enemy")
        if cell.gold > 0:
            return config.symbols.gold, "gold"
        if cell.items:
            top = cell.items[-1]
            return top.symbol, config.symbols.tile_style.get(top.symbol, "item")
        if cell.trap and not cell.trap_hidden:
            return config.symbols.trap, "trap"
        if cell.feature == "altar":
            return config.symbols.altar, "altar"
        glyph = config.symbols.terrain_glyph.get(cell.terrain, config.symbols.empty)
        return glyph, config.symbols.tile_style.get(glyph, "floor")

    # --- pathfinding ----------------------------------------------------
    def bfs_path(self, start, is_goal, passable):
        """Breadth-first search; returns the step path (excluding start) to the nearest
        goal cell, or None. ``is_goal(cell)`` and ``passable(y, x)`` are callables."""
        from collections import deque
        prev = {start: None}
        q = deque([start])
        while q:
            cur = q.popleft()
            if cur != start and is_goal(cur):
                path = []
                node = cur
                while node != start:
                    path.append(node)
                    node = prev[node]
                path.reverse()
                return path
            cy, cx = cur
            for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1),
                            (-1, -1), (-1, 1), (1, -1), (1, 1)):
                ny, nx = cy + dy, cx + dx
                if self.in_bounds(ny, nx) and (ny, nx) not in prev and passable(ny, nx):
                    prev[(ny, nx)] = cur
                    q.append((ny, nx))
        return None


def _bresenham(y0, x0, y1, x1):
    points = []
    dy = abs(y1 - y0)
    dx = abs(x1 - x0)
    sy = 1 if y0 < y1 else -1
    sx = 1 if x0 < x1 else -1
    err = dx - dy
    while True:
        points.append((y0, x0))
        if y0 == y1 and x0 == x1:
            break
        e2 = 2 * err
        if e2 > -dy:
            err -= dy
            x0 += sx
        if e2 < dx:
            err += dx
            y0 += sy
    return points
