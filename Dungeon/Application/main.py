import datetime
import os
import sys
import time
import operator
import traceback
import random

from tinydb import TinyDB, Query
from rich.panel import Panel

from . import input as keys
from .config import config
from .utils import style_text, clear_screen
from .classes.map import DungeonMap, DungeonPlayer
from .classes.menus import DungeonMenu
from .classes.items import DungeonOrb, DungeonPotion, DungeonScroll
from .classes.database import DungeonDatabase
from .classes.misc import DungeonTimeData
from .classes.people import DungeonTrader, DungeonHealer
from .classes.levelgen import generate_level

print("Loading...")

T = config.terrain

TURN = 10  # energy one full-speed action costs / grants per game-tick

# compass direction -> (dy, dx), for cursor movement and pathfinding
DIR_DELTA = {
    "n": (-1, 0), "s": (1, 0), "w": (0, -1), "e": (0, 1),
    "ne": (-1, 1), "nw": (-1, -1), "se": (1, 1), "sw": (1, -1),
}

# Weapons seeded into vault treasure, by how deep you are.
_VAULT_WEAPONS = ["Short Sword", "Mace", "Spear", "Long Sword", "War Axe"]

# Randomised appearances for unidentified consumables (shuffled per game).
_POTION_ADJ = [
    "fizzy", "murky", "glowing", "viscous", "azure", "crimson", "smoky", "bubbling",
    "cloudy", "oily", "sparkling", "luminous", "syrupy", "effervescent",
]
_SCROLL_LABELS = [
    "XYZZY", "FOOBIE", "KLATAA", "ZELGO", "NR9", "PRZ", "VELOX", "GNARL",
    "HRUM", "TZADIK", "OByeDA", "WAffLE",
]


class Dungeon:
    """Main game controller: owns the floors, player, database, and game loop."""

    def __init__(self, logger, rich_console) -> None:
        self.log = logger
        self.rich_console = rich_console
        self.print = self.rich_console.print
        self.over = False

        clear_screen()
        self.menu = DungeonMenu(game=self)
        self.moves = 0
        self.depth = 1
        self.levels: dict[int, DungeonMap] = {}
        self.target_cursor = None   # ranged-targeting overlay state
        self.target_path = None
        # Developer god mode: enable from the start with DUNGEON_GODMODE=1, or toggle in-game with `~`.
        self.godmode = os.environ.get("DUNGEON_GODMODE") == "1"

        from .classes.ui import DungeonUI
        self.ui = DungeonUI(game=self)

        self.db = DungeonDatabase(game=self)
        self._init_identification()
        self.leaderboard = TinyDB("leaderboard.json")
        self.leaderboardQuery = Query()

        self.player = DungeonPlayer(
            health=config.player.health,
            max_health=config.player.max_health,
            max_inventory=config.player.max_inventory,
            coins=config.player.coins,
            xp=config.player.xp,
            equipped=self.db.item_db.search_item(name="Fists"),
            game=self,
        )
        self._choose_background()

        while True:
            self.session_id = random.getrandbits(64)
            if not self.leaderboard.search(self.leaderboardQuery.session_id == self.session_id):
                break

        self.player.name = input("Hello adventurer, what is your name? (Enter for random)\n> ").strip()
        if not self.player.name:
            from .classes.people import DungeonPeople
            self.player.name = DungeonPeople.generate_name()
            print(f"You are {self.player.name}.")
            time.sleep(1.2)

        self.enter_level(1, mode="down")
        self.message(f"[flavor]You descend into the dungeon. Somewhere far below lies the Orb of Zot.[/flavor]")
        self.log.info("dungeon initialised")

    # --- character creation --------------------------------------------
    def _choose_background(self) -> None:
        from rich.table import Table
        backgrounds = self.db.backgrounds
        clear_screen()
        table = Table(title="Choose your Class", title_style="menu_header", border_style="grey37")
        table.add_column("#", style="controls", justify="right")
        table.add_column("Class", style="name")
        table.add_column("HP", style="health", justify="right")
        table.add_column("Starting kit", style="flavor")
        for i, bg in enumerate(backgrounds, 1):
            kit = ", ".join([bg["start_weapon"]] + bg.get("start_items", []))
            table.add_row(str(i), bg["name"], f"+{bg['hp_bonus']}", kit)
        self.print(table)
        self.print(
            f"\nPress {style_text('1', 'controls')}-{style_text(str(len(backgrounds)), 'controls')} "
            f"to choose (any other key = Wanderer).", highlight=False)
        key = keys.read_key()
        idx = int(key) - 1 if key.isdigit() and 1 <= int(key) <= len(backgrounds) else len(backgrounds) - 1
        self._apply_background(backgrounds[idx])

    def _apply_background(self, bg: dict) -> None:
        p = self.player
        p.background = bg["name"]
        p.max_health += bg.get("hp_bonus", 0)
        p.health = p.max_health
        weapon = self.db.item_db.search_item(name=bg["start_weapon"])
        if weapon:
            p.inventory.append(weapon)
            p.equipped = weapon
            self.identify(weapon, announce=False)
        for name in bg.get("start_items", []):
            item = self.db.item_db.search_item(name=name)
            if item:
                p.inventory.append(item)
                self.identify(item, announce=False)  # starting kit is known

    # --- messaging ------------------------------------------------------
    def message(self, text: str, drop: int | None = None) -> None:
        self.ui.message(text, drop=drop)

    def render(self) -> None:
        self.ui.render()

    # --- item identification -------------------------------------------
    def _init_identification(self) -> None:
        """Assign each potion/scroll type a random appearance for this game."""
        self.ident: dict[str, dict] = {}
        potions = list(self.db.item_db.potions)
        for pot, adj in zip(potions, random.sample(_POTION_ADJ, len(potions))):
            self.ident[pot.name] = {"appearance": f"{adj} potion", "identified": False}
        scrolls = list(self.db.item_db.scrolls)
        for sc, label in zip(scrolls, random.sample(_SCROLL_LABELS, len(scrolls))):
            self.ident[sc.name] = {"appearance": f"scroll labelled '{label}'", "identified": False}

    def display_name(self, item) -> str:
        rec = self.ident.get(getattr(item, "name", None))
        if rec and not rec["identified"]:
            return rec["appearance"]
        return getattr(item, "name", "?")

    def identify(self, item, announce: bool = True) -> None:
        """Mark an item's whole type identified (optionally announcing its true name)."""
        rec = self.ident.get(getattr(item, "name", None))
        if rec and not rec["identified"]:
            rec["identified"] = True
            if announce:
                self.message(f"[success]You identify it as {style_text(item.name, 'item')}![/success]")

    # --- level generation & travel -------------------------------------
    def _new_level(self, depth: int) -> DungeonMap:
        is_last = depth >= config.depth.floors
        layout = generate_level(is_last=is_last, depth=depth)
        level = DungeonMap(game=self, layout=layout)
        self._populate(level, depth, is_last)
        return level

    def _populate(self, level: DungeonMap, depth: int, is_last: bool) -> None:
        pool = list(level.floor_cells)
        random.shuffle(pool)
        suy, sux = level.stairs_up

        def far_cell():
            while pool:
                y, x = pool.pop()
                if abs(y - suy) + abs(x - sux) > 3:
                    return (y, x)
            return None

        # Monsters (count scales with depth).
        count = config.spawn.enemies_base + config.spawn.enemies_per_depth * (depth - 1)
        for _ in range(count):
            loader = self.db.enemy_db.random_for_depth(depth)
            spot = far_cell()
            if loader and spot:
                enemy = loader.load()
                level.place_occupant(enemy, *spot)
                level.enemies.append(enemy)

        # NPCs spawn inside open rooms (never in 1-wide corridors, so they can't wall you
        # in), and none appear on the Orb floor.
        if not is_last:
            floor_set = set(level.floor_cells)
            room_pool = [
                (y, x) for room in level.rooms for (y, x) in room.interior()
                if (y, x) in floor_set and abs(y - suy) + abs(x - sux) > 3
            ]
            random.shuffle(room_pool)

            def room_cell():
                while room_pool:
                    y, x = room_pool.pop()
                    if level.matrix[y][x].occupant is None:
                        return (y, x)
                return far_cell()

            for loader in random.sample(self.db.people_db.traders(),
                                        k=min(config.spawn.npcs_per_floor, len(self.db.people_db.traders()))):
                spot = room_cell()
                if not spot:
                    break
                npc = loader.load()
                npc.symbol = loader.data.symbol
                npc.style = npc.occupation.lower()
                level.place_occupant(npc, *spot)
                level.npcs.append(npc)

        # Loose loot on the floor (placed on any open floor tile, never inside a vault).
        for _ in range(config.spawn.floor_potions):
            self._scatter(level, self._depth_potion(depth))
        for _ in range(config.spawn.floor_scrolls):
            self._scatter(level, random.choice(self.db.item_db.scrolls))
        for _ in range(config.spawn.floor_weapons):
            self._scatter(level, random.choice(self.db.item_db.weapons[1:]))
        for _ in range(config.spawn.gold_piles):
            cell = self._floor_cell(level)
            if cell:
                cell.gold += random.randint(2, 6 + depth * 2)

        # Hidden traps (depth-scaled), away from the entry stairs.
        for _ in range(config.spawn.traps_base + depth // 2):
            y, x = random.choice(level.floor_cells)
            cell = level.matrix[y][x]
            if cell.trap is None and not cell.items and cell.gold == 0 \
                    and abs(y - suy) + abs(x - sux) > 4:
                cell.trap = random.choice(["dart", "poison", "teleport", "alarm"])

        # Vault treasure (or the Orb chamber on the last floor), then any temple.
        self._fill_vault(level, depth, is_last)
        self._fill_temple(level, depth)

    def _scatter(self, level, item) -> None:
        cell = self._floor_cell(level)
        if cell and item:
            cell.items.append(item)

    def _floor_cell(self, level):
        if not level.floor_cells:
            return None
        y, x = random.choice(level.floor_cells)
        return level.matrix[y][x]

    def _depth_potion(self, depth: int):
        roll = random.randint(0, 9) + depth
        name = "Strong Healing Potion" if roll > 9 else "Medium Healing Potion" if roll > 4 else "Weak Healing Potion"
        return self.db.item_db.search_item(name=name)

    def _fill_vault(self, level, depth: int, is_last: bool) -> None:
        if not level.vault_cells:
            return
        cells = list(level.vault_cells)
        random.shuffle(cells)
        if is_last:
            oy, ox = cells.pop()
            level.matrix[oy][ox].items.append(DungeonOrb())
            level.matrix[oy][ox].gold += random.randint(40, 80)
            loader = self.db.enemy_db.search_enemy(name="Orb Guardian")
            if loader and cells:
                gy, gx = min(cells, key=lambda c: abs(c[0] - oy) + abs(c[1] - ox))
                boss = loader.load()
                boss.awake = True
                level.place_occupant(boss, gy, gx)
                level.enemies.append(boss)
            if cells:  # the legendary blade rewards reaching the bottom, on its own tile
                sy, sx = cells.pop()
                level.matrix[sy][sx].items.append(self.db.item_db.search_item(name="Sword of Zot"))
        else:
            wy, wx = cells.pop()
            weapon_name = _VAULT_WEAPONS[min(depth - 1, len(_VAULT_WEAPONS) - 1)]
            level.matrix[wy][wx].items.append(self.db.item_db.search_item(name=weapon_name))
            if cells:
                gy, gx = cells.pop()
                level.matrix[gy][gx].gold += random.randint(15, 30 + depth * 5)
            if cells:
                py, px = cells.pop()
                level.matrix[py][px].items.append(self.db.item_db.search_item(name="Strong Healing Potion"))

    def _fill_temple(self, level, depth: int) -> None:
        if not level.temple_cells:
            return
        cells = list(level.temple_cells)
        random.shuffle(cells)
        for _ in range(min(3, len(cells))):  # guardians, a notch tougher than the floor
            loader = self.db.enemy_db.random_for_depth(min(config.depth.floors, depth + 1))
            if not loader or not cells:
                continue
            sy, sx = cells.pop()
            if level.matrix[sy][sx].occupant is None:
                enemy = loader.load()
                level.place_occupant(enemy, sy, sx)
                level.enemies.append(enemy)
        if cells:  # a strong weapon as the prize
            wy, wx = cells.pop()
            weapon_name = _VAULT_WEAPONS[min(depth, len(_VAULT_WEAPONS) - 1)]
            level.matrix[wy][wx].items.append(self.db.item_db.search_item(name=weapon_name))
        if cells:
            gy, gx = cells.pop()
            level.matrix[gy][gx].gold += random.randint(20, 40 + depth * 5)
        pool = self.db.item_db.potions + self.db.item_db.scrolls
        for _ in range(2):
            if cells:
                cy, cx = cells.pop()
                level.matrix[cy][cx].items.append(random.choice(pool))

    def enter_level(self, depth: int, mode: str) -> None:
        if depth not in self.levels:
            self.levels[depth] = self._new_level(depth)
        self.depth = depth
        self.map = self.levels[depth]
        if mode == "up" and self.map.stairs_down:
            self.player.location = self.map.stairs_down
        else:
            self.player.location = self.map.stairs_up
        self.player.energy = TURN  # ready to act immediately on arrival
        self.map.update_fov()
        if mode == "down":
            self.message(f"[stairs]You arrive on Depth {depth}.[/stairs]")
        else:
            self.message(f"[stairs]You climb to Depth {depth}.[/stairs]")

    # --- turn engine (energy scheduler) --------------------------------
    def spend_turn(self) -> None:
        self.player.energy -= TURN
        self.moves += 1
        self.time.add()

    def game_tick(self) -> None:
        """One unit of world time: grant energy, tick statuses, run monster actions."""
        p = self.player
        p.energy += p.effective_speed()
        p.status.tick(p, self)
        if p.health <= 0:
            self.game_over("dead")
            return
        for e in self.map.enemies:
            e.energy += e.effective_speed()
        for e in list(self.map.enemies):
            if e.health > 0:
                e.status.tick(e, self)
                if e.health <= 0:
                    self.on_enemy_death(e)
        for e in list(self.map.enemies):
            while e.health > 0 and e.energy >= TURN:
                e.act()
                e.energy -= TURN
                if self.player.health <= 0:
                    self.game_over("dead")
                    return

    def advance_world(self) -> None:
        """Advance time until the player can act again, then settle fog and detection."""
        while self.player.energy < TURN and not self.over:
            self.game_tick()
        if self.over:
            return
        if self.player.health <= 0:
            self.game_over("dead")
            return
        found = self.map.auto_detect_secret()
        if found == "door":
            self.message("[warn]You notice a hidden door nearby![/warn]")
        elif found == "trap":
            self.message("[warn]You spot a hidden trap nearby![/warn]")
        self.map.update_fov()

    def on_enemy_death(self, enemy) -> None:
        self.player.gain_xp(enemy.xp_drop)
        self.map.remove_occupant(enemy)
        if enemy in self.map.enemies:
            self.map.enemies.remove(enemy)
        ey, ex = enemy.location
        self.map.matrix[ey][ex].gold += enemy.coin_drop
        self.message(enemy.texts.death)
        if enemy.tier == "boss":
            self.message("[success]The guardian shatters! The Orb of Zot lies unguarded.[/success]")

    def awaken_floor(self) -> None:
        for enemy in self.map.enemies:
            enemy.awake = True

    # --- player commands ------------------------------------------------
    def interact_npc(self, npc) -> bool:
        """Open an NPC's menu. Returns True if a turn was spent (the player stepped past)."""
        result = None
        if isinstance(npc, DungeonTrader):
            for item in npc.stuff:  # merchants' wares are displayed identified
                self.identify(item, announce=False)
            result = self.menu.trader(npc)
        elif isinstance(npc, DungeonHealer):
            result = self.menu.healer(npc)
        if result == "swap":
            return self.swap_with_npc(npc)
        return False

    def swap_with_npc(self, npc) -> bool:
        """Trade places with a non-hostile NPC so corridors are never permanently blocked."""
        py, px = self.player.location
        ny, nx = npc.location
        self.map.move_occupant(npc, py, px)
        self.player.location = (ny, nx)
        self.player._on_enter(self.player.cell)
        self.message(f"You slip past {style_text(npc.name, 'name')}.")
        return True

    def collect_item(self, item) -> bool:
        """Move one item from the player's tile into the pack (or claim the Orb). True if taken."""
        cell = self.player.cell
        if item not in cell.items:
            return False
        if isinstance(item, DungeonOrb):
            cell.items.remove(item)
            self.player.has_orb = True
            self.message("[orb]You hoist the Orb of Zot! Its light floods the chamber.[/orb]")
            self.message("[warn]The dungeon shudders awake. Flee to the surface![/warn]")
            self.awaken_floor()
            return True
        if len(self.player.inventory) >= self.player.max_inventory:
            self.message("Your pack is full.")
            return False
        cell.items.remove(item)
        self.player.inventory.append(item)
        self.message(f"You pick up the {style_text(self.display_name(item), 'item')}.")
        return True

    def pickup(self) -> bool:
        cell = self.player.cell
        if not cell.items:
            self.message("There is nothing here to pick up.")
            return False
        if len(cell.items) == 1:
            return self.collect_item(cell.items[0])
        return self.menu.pickup_menu(cell) > 0

    def descend(self) -> None:
        if self.player.cell.terrain == T.STAIRS_DOWN:
            self.enter_level(self.depth + 1, mode="down")
        else:
            self.message("There are no stairs down here.")

    def ascend(self) -> None:
        if self.player.cell.terrain != T.STAIRS_UP:
            self.message("There are no stairs up here.")
            return
        if self.depth == 1:
            if self.player.has_orb:
                self.game_over("win")
            else:
                self.message("[warn]You cannot abandon the dungeon without the Orb of Zot.[/warn]")
        else:
            self.enter_level(self.depth - 1, mode="up")

    def apply_potion(self, pot) -> None:
        p = self.player
        appearance = self.display_name(pot)
        was_unknown = appearance != pot.name
        self.identify(pot, announce=False)  # learned by drinking; named in the message below
        parts = []
        if pot.effect == "curing":
            cured = p.status.clear_harmful()
            parts.append("the poison drains away" if "poison" in cured else "you feel cleansed")
        elif pot.effect == "might":
            p.status.add("might", pot.duration, pot.potency)
            parts.append("[might]power surges through you[/might]")
        elif pot.effect == "haste":
            p.status.add("haste", pot.duration, pot.potency)
            parts.append("[haste]the world slows around you[/haste]")
        elif pot.effect == "regen":
            p.status.add("regen", pot.duration, pot.potency)
            parts.append("[regen]your wounds begin to knit[/regen]")
        if pot.hp_change > 0:
            if p.health < p.max_health:
                healed = min(p.max_health - p.health, pot.hp_change)
                p.health += healed
                parts.append("you feel rejuvenated")
            elif not pot.effect:
                parts.append("nothing seems to happen")
        effect_text = f" {', '.join(parts)}." if parts else ""
        real = style_text(pot.name, "item")
        if was_unknown:
            self.message(f"You quaff the {style_text(appearance, 'item')} — "
                         f"it is [success]{real}[/success]!{effect_text}")
        else:
            self.message(f"You quaff the {real}.{effect_text}")

    def use_scroll(self, scroll) -> bool:
        appearance = self.display_name(scroll)
        was_unknown = appearance != scroll.name
        self.identify(scroll, announce=False)  # learned by reading; named in the message below
        real = style_text(scroll.name, "item")
        read = (f"You read the {style_text(appearance, 'item')} — it is [success]{real}[/success]!"
                if was_unknown else f"You read the {real}.")
        if scroll.effect == "identify":
            self.message(read)
            target = self.menu.choose_unidentified(exclude=scroll)
            if target is not None:
                self.identify(target)
            else:
                self.message("You have nothing else to identify.")
            return True
        if scroll.effect == "magic_mapping":
            self.map.reveal_all()
            self.message(f"{read} The floor's layout floods into your mind.")
        elif scroll.effect == "teleport":
            self.player.location = self.map.random_walkable()
            self.map.update_fov()
            self.message(f"{read} You blink across the floor.")
        return True

    def search(self) -> None:
        if self.map.search(self.player.y, self.player.x):
            self.message("[warn]You uncover something hidden nearby![/warn]")
        else:
            self.message("You search the area but find nothing.")

    # --- traps ----------------------------------------------------------
    def trigger_trap(self, cell) -> None:
        kind = cell.trap
        cell.trap_hidden = False
        p = self.player
        if kind == "dart":
            dmg = random.randint(2, 4 + self.depth)
            p.health -= dmg
            self.message(f"[trap]A dart trap fires![/trap] You take {dmg} damage.")
        elif kind == "poison":
            dmg = random.randint(1, 3)
            p.health -= dmg
            p.status.add("poison", random.randint(4, 7), 1 + self.depth // 4)
            self.message(f"[trap]A needle springs out![/trap] [poison]You are poisoned![/poison]")
        elif kind == "teleport":
            p.location = self.map.random_walkable()
            self.map.update_fov()
            self.message("[trap]A teleport trap whisks you across the floor![/trap]")
        elif kind == "alarm":
            self.awaken_floor()
            self.message("[trap]An alarm trap blares! The floor's monsters stir.[/trap]")

    # --- temple altar ---------------------------------------------------
    def bless_at_altar(self, cell) -> None:
        cell.feature = None  # a single blessing per altar
        p = self.player
        p.health = p.max_health
        p.status.add("regen", 15, 2)
        self.message("[success]You kneel at the ancient altar. Warmth floods you — "
                     "fully healed and blessed with [regen]Regeneration[/regen].[/success]")

    # --- ranged combat --------------------------------------------------
    def fire(self) -> bool:
        weapon = self.player.equipped
        if not getattr(weapon, "ranged", False):
            self.message("You have no ranged weapon equipped.")
            return False
        rng = weapon.range
        py, px = self.player.location

        def reachable(e):
            return (max(abs(e.y - py), abs(e.x - px)) <= rng
                    and self.map._line_of_sight(py, px, e.y, e.x))

        targets = sorted((e for e in self.map.visible_enemies() if reachable(e)),
                         key=lambda e: max(abs(e.y - py), abs(e.x - px)))
        if not targets:
            self.message("There is no target in range.")
            return False
        idx = 0
        cursor = list(targets[idx].location)
        while True:
            self._show_target(cursor)
            self.render()
            key = keys.read_key()
            if key in (keys.ESC, "q"):
                self._clear_target()
                return False
            if key in (keys.ENTER, "f"):
                break
            if key == keys.TAB:
                idx = (idx + 1) % len(targets)
                cursor = list(targets[idx].location)
                continue
            d = keys.read_direction(key)
            if d:
                dy, dx = DIR_DELTA[d]
                ny, nx = cursor[0] + dy, cursor[1] + dx
                if self.map.in_bounds(ny, nx):
                    cursor = [ny, nx]
        ty, tx = cursor
        self._clear_target()
        enemy = self.map.matrix[ty][tx].occupant
        if (enemy and getattr(enemy, "is_enemy", False)
                and max(abs(ty - py), abs(tx - px)) <= rng
                and self.map._line_of_sight(py, px, ty, tx)):
            self.ranged_attack(enemy)
        else:
            self.message("Your shot flies wide and strikes nothing.")
        return True

    def _show_target(self, cursor) -> None:
        self.target_cursor = (cursor[0], cursor[1])
        self.target_path = self.map.line_points(
            self.player.y, self.player.x, cursor[0], cursor[1])[1:-1]

    def _clear_target(self) -> None:
        self.target_cursor = None
        self.target_path = None

    def ranged_attack(self, enemy) -> None:
        weapon = self.player.equipped
        en = style_text(enemy.name, "enemy")
        wn = style_text(weapon.name, "weapons")
        if self.godmode:
            self.message(f"[warn][GOD][/warn] Your shot vaporises the {en}.")
            enemy.health = 0
            self.on_enemy_death(enemy)
            return
        dmg_bonus, acc_bonus = self.player.combat_bonus()
        if random.randint(1, 100) <= weapon.accuracy + acc_bonus:
            raw = random.randint(weapon.attack_range[0], weapon.attack_range[1])
            damage = max(1, weapon.base_attack + raw + dmg_bonus)
            self.message(f"You shoot the {en} with your {wn}.", drop=damage)
            enemy.health -= damage
            if enemy.health <= 0:
                self.on_enemy_death(enemy)
        else:
            self.message(f"Your shot whistles past the {en}.")

    # --- autoexplore ----------------------------------------------------
    def autoexplore(self) -> None:
        for _ in range(1000):
            if self.over or self.map.visible_enemies():
                if self.map.visible_enemies():
                    self.message("[warn]A monster comes into view.[/warn]")
                break

            def passable(y, x):
                c = self.map.matrix[y][x]
                if c.occupant is not None:
                    return False
                if c.terrain in (T.WALL, T.SECRET_DOOR):
                    return False
                if c.trap and not c.trap_hidden:
                    return False
                return True

            def is_goal(cur):
                y, x = cur
                if not self.map.matrix[y][x].explored:
                    return False
                for dy, dx in DIR_DELTA.values():
                    ny, nx = y + dy, x + dx
                    if self.map.in_bounds(ny, nx) and not self.map.matrix[ny][nx].explored:
                        return True
                return False

            path = self.map.bfs_path(self.player.location, is_goal, passable)
            if not path:
                self.message("[flavor]There is nothing left to explore here.[/flavor]")
                break
            ny, nx = path[0]
            direction = self._dir_to(ny, nx)
            if direction is None or not self.player.move(direction):
                break
            self.spend_turn()
            self.advance_world()
            self.render()
            time.sleep(0.03)

    def _dir_to(self, ny: int, nx: int) -> str | None:
        return {(-1, 0): "n", (1, 0): "s", (0, -1): "w", (0, 1): "e",
                (-1, -1): "nw", (-1, 1): "ne", (1, -1): "sw", (1, 1): "se"}.get(
            (ny - self.player.y, nx - self.player.x))

    # --- main loop ------------------------------------------------------
    def gameloop(self) -> None:
        self.time = DungeonTimeData(game=self)
        self.log.info(f"started game at {time.time():.2f}")
        self.player.energy = TURN
        while not self.over:
            self.advance_world()
            if self.over:
                break
            self.render()
            key = keys.read_key()
            if self.handle(key):
                self.spend_turn()

    def handle(self, key: str) -> bool:
        """Dispatch one keypress. Returns True if the action spent a game turn."""
        direction = keys.read_direction(key)
        if direction:
            if self.player.status.has("confusion") and random.random() < 0.5:
                direction = random.choice(list(keys.MOVE_KEYS.values()))
            return self.player.move(direction)
        if key == "g":
            return self.pickup()
        if key in ("d", "i"):
            self.menu.pack()
            return False
        if key == "f":
            return self.fire()
        if key == "o":
            self.autoexplore()
            return False
        if key == ">":
            self.descend()
            return False
        if key == "<":
            self.ascend()
            return False
        if key == "s":
            self.search()
            return True
        if key in (".", keys.SPACE):
            self.message("You wait.")
            return True
        if key == "p":
            self.time.pause_menu()
            return False
        if key == "~":
            self.godmode = not self.godmode
            if self.godmode:
                self.map.reveal_all()
            self.message(f"[warn]Developer god mode {'ENABLED' if self.godmode else 'disabled'}.[/warn]")
            return False
        if key == "?":
            self.help_screen()
            return False
        if key == keys.ESC:
            self.over = True
            self.log.info("game exited by player")
            clear_screen()
            print("Exiting [Dungeon]...")
            sys.exit()
        return False

    def help_screen(self) -> None:
        clear_screen()
        self.print(Panel(
            "[menu_header]Dungeon.py — Controls[/menu_header]\n\n"
            "[controls]arrows[/controls] or [controls]hjkl[/controls]  move / attack (walk into a monster)\n"
            "[controls]yubn[/controls]  diagonal movement (nw / ne / sw / se)\n"
            "[controls]f[/controls]  fire a ranged weapon (aim, then [controls]f[/controls]/[controls]enter[/controls]; [controls]tab[/controls] next target)\n"
            "[controls]o[/controls]  autoexplore the floor (stops when a monster appears)\n"
            "[controls]g[/controls]  pick up items on your tile (choose which, or take all)\n"
            "[controls]i[/controls] / [controls]d[/controls]  open pack — use, equip, unequip, drop\n"
            "[controls]>[/controls] / [controls]<[/controls]  descend / ascend stairs\n"
            "[controls]s[/controls]  search adjacent tiles for secret doors and traps\n"
            "[controls].[/controls] or [controls]space[/controls]  wait one turn\n"
            "[controls]p[/controls]  pause    [controls]esc[/controls]  quit\n\n"
            "[flavor]At a trader/healer, press [controls]space[/controls] to step past them.[/flavor]\n"
            "[flavor]Developer: [controls]~[/controls] toggles god mode (or set DUNGEON_GODMODE=1).[/flavor]\n\n"
            "[flavor]Descend to the bottom, seize the Orb of Zot, and escape to the surface.[/flavor]\n\n"
            f"Press {style_text('any key', 'controls')} to return.",
            border_style="grey37"))
        keys.read_key()

    # --- endgame --------------------------------------------------------
    def record_leaderboard(self, outcome: str) -> None:
        self.leaderboard.insert({
            "name": self.player.name,
            "outcome": outcome,
            "depth": self.depth,
            "orb": self.player.has_orb,
            "time": round(self.time.elapsed, 3),
            "moves": self.moves,
            "xp": self.player.xp,
            "datetime": str(datetime.datetime.now()),
            "session_id": self.session_id,
        })
        winners = sorted(
            [e for e in self.leaderboard.all() if e.get("outcome") == "win"],
            key=operator.itemgetter("time"))
        self.print(f"\n{style_text('[ Hall of Champions ]', 'menu_header')}\n", highlight=False)
        if not winners:
            self.print("[flavor]No one has escaped with the Orb yet. Be the first.[/flavor]", highlight=False)
        for i, e in enumerate(winners[:10]):
            here = style_text("you", "success") if e["session_id"] == self.session_id else e["name"]
            self.print(f"{i + 1}. {here} — {e['time']}s, {e['moves']} turns", highlight=False)

    def game_over(self, how: str) -> None:
        self.over = True
        clear_screen()
        if how == "win":
            self.print(Panel(
                f"[success]You escape the dungeon clutching the Orb of Zot![/success]\n"
                f"[name]{self.player.name}[/name], you are victorious.\n"
                f"Turns: {self.moves}   Time: {self.time.elapsed:.1f}s   XP: {self.player.xp}",
                title="[success]VICTORY[/success]", border_style="green"))
            self.record_leaderboard("win")
        else:
            self.print(Panel(
                f"[fail]You have fallen on Depth {self.depth}.[/fail]\n"
                f"[name]{self.player.name}[/name] will be remembered... briefly.\n"
                f"Turns: {self.moves}   Time: {self.time.elapsed:.1f}s   XP: {self.player.xp}",
                title="[fail]DEATH[/fail]", border_style="red"))
            self.record_leaderboard("death")
        self.print(f"\nPress {style_text('any key', 'controls')} to exit.", highlight=False)
        keys.read_key()
        sys.exit()

    @staticmethod
    def __start__(logger, rich_console) -> None:
        try:
            d = Dungeon(logger=logger, rich_console=rich_console)
            d.log.info("dungeon set up is done, starting game")
            d.gameloop()
        except SystemExit:
            raise
        except KeyboardInterrupt:
            print("Exiting [Dungeon]...")
            logger.info(f"game exited by KeyboardInterrupt at {time.time():.2f}")
            sys.exit()
        except Exception as e:
            logger.fatal(f"\n{''.join(traceback.format_tb(e.__traceback__))}\n\n{str(e)}")
