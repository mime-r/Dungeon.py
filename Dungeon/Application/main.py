import datetime
import os
import sys
import time
import operator
import traceback
import random
from dataclasses import dataclass, field

from tinydb import TinyDB, Query
from rich.panel import Panel

from . import input as keys
from .config import config
from .utils import style_text, clear_screen
from .classes.map import DungeonMap, DungeonPlayer
from .classes.menus import DungeonMenu
from .classes.items import DungeonShard, DungeonPotion, DungeonScroll
from .classes.database import DungeonDatabase
from .classes.misc import DungeonTimeData
from .classes.people import DungeonTrader, DungeonHealer
from .classes.levelgen import generate_level, STRUCTURE_CATALOG
from .llm import LLMClient

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

# Shard floors: depth -> (shard name, guardian name)
_SHARD_FLOORS = {
    6: ("Shard of Flame", "Flame Guardian"),
    7: ("Shard of Stone", "Stone Guardian"),
    8: ("Shard of Shadow", "Shadow Guardian"),
}

# Floor themes: LLM-generated per-floor biome data
@dataclass
class FloorTheme:
    name: str = ""
    description: str = ""
    layout_bias: str = "any"      # cave | rooms | bsp | any
    enemy_bias: list = field(default_factory=list)
    trap_type: str = "any"        # dart | poison | teleport | alarm | any
    trap_density: str = "normal"  # low | normal | high
    loot_bias: str = "balanced"   # potions | scrolls | weapons | gold | balanced
    ambient: str = ""
    structures: list = field(default_factory=list)        # 0-2 names from STRUCTURE_CATALOG
    terrain_features: list = field(default_factory=list)  # 0-2 from _VALID_TERRAIN_FEATURES

_THEME_SPINNER = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
_VALID_BIAS_ENEMIES = [
    "Giant Rat", "Bat", "Kobold", "Goblin", "Orc", "Skeleton", "Zombie",
    "Giant Spider", "Kobold Slinger", "Ogre", "Wraith", "Troll",
]
_VALID_STRUCTURES = {
    "shrine", "mushroom_grove", "overgrown_room", "ruined_hall",
    "frozen_pond", "campsite", "poison_marsh", "standing_stones",
}
_VALID_TERRAIN_FEATURES = {"lava_pools", "chasms"}

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
        self.camera_override = None  # pans viewport to a staircase when set (y, x)
        self.stair_cursor = None     # highlights a staircase tile in the render
        self.auto_pickup_types: set[str] = {"potion", "scroll"}
        # Developer god mode: enable from the start with DUNGEON_GODMODE=1, or toggle in-game with `~`.
        self.godmode = os.environ.get("DUNGEON_GODMODE") == "1"

        self.llm = LLMClient()
        self.log.info(f"LLM status: {self.llm.status}")

        # DM hint state
        self._hint_future = None
        self._last_hint_turn: int = -30
        self._hinted_states: set[str] = set()

        # Item lore state (name -> Future); _lore_done tracks items already attempted
        self._lore_futures: dict = {}
        self._lore_done: set[str] = set()

        # Floor theme state
        self._floor_themes: dict[int, FloorTheme] = {}
        self._theme_history: list[str] = []

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
        self.message(f"[flavor]You descend into the dungeon. Three shards of a Broken Sigil lie scattered in the depths — find them all.[/flavor]")
        if self.llm.enabled:
            self.message(f"[flavor]The dungeon breathes with strange intelligence. ({self.llm.status})[/flavor]")
        elif self.llm.status != "disabled":
            self.message(f"[warn]LLM unavailable: {self.llm.status}[/warn]")
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
        self._check_state_triggers()
        self._flush_hint()
        self._flush_lore()
        self.ui.render()

    # --- LLM: DM hints -------------------------------------------------
    def _check_state_triggers(self) -> None:
        p = self.player
        if p.max_health and p.health / p.max_health < 0.3:
            self._queue_hint(f"low_hp_d{self.depth}", {
                "trigger": "player is critically wounded",
                "depth": self.depth, "background": p.background,
                "hp": p.health, "max_hp": p.max_health,
            })
        # Ambient flavour: fires at most once per 30-turn bucket (cooldown still applies)
        bucket = self.moves // 30
        if bucket > 0:
            self._queue_hint(f"ambient_{bucket}", {
                "trigger": "a quiet moment in the dungeon between encounters",
                "depth": self.depth, "background": p.background,
                "hp": p.health, "max_hp": p.max_health,
            })

    def _queue_hint(self, trigger_id: str, ctx: dict) -> None:
        if not self.llm.enabled:
            return
        if trigger_id in self._hinted_states:
            return
        if self.moves - self._last_hint_turn < 8:
            return
        self._hinted_states.add(trigger_id)
        self._hint_future = self.llm.complete_async(self._build_hint_prompt(ctx))

    def _build_hint_prompt(self, ctx: dict) -> list[dict]:
        return [
            {"role": "system", "content": (
                "You are the narrator of a dark fantasy roguelike. "
                "Output ONLY one short atmospheric sentence — no thinking, no explanation, "
                "no quotation marks. Maximum 15 words. Pure flavor, no gameplay advice."
            )},
            {"role": "user", "content": (
                f"Event: {ctx.get('trigger', 'something notable happened')}. "
                f"Depth {ctx.get('depth', '?')}, "
                f"{ctx.get('background', 'adventurer')}, "
                f"HP {ctx.get('hp', '?')}/{ctx.get('max_hp', '?')}."
            )},
        ]

    def _flush_hint(self) -> None:
        if self._hint_future and self._hint_future.done():
            text = self._hint_future.result()
            if text:
                self.message(f"[flavor]{text}[/flavor]")
                self._last_hint_turn = self.moves
            self._hint_future = None

    # --- LLM: item lore ------------------------------------------------
    def _build_lore_prompt(self, item) -> list[dict]:
        kind = type(item).__name__.replace("Dungeon", "").lower()
        return [
            {"role": "system", "content": (
                "You write item lore for a dark fantasy game. "
                "Output ONLY one sentence of grim backstory — no thinking, no explanation, "
                "no quotation marks. Specific and evocative."
            )},
            {"role": "user", "content": (
                f"{item.name} ({kind}): {item.description}"
            )},
        ]

    def _flush_lore(self) -> None:
        done = [name for name, f in self._lore_futures.items() if f.done()]
        for name in done:
            text = self._lore_futures.pop(name).result()
            self._lore_done.add(name)
            if not text:
                continue
            if name in self.ident:
                self.ident[name]["lore"] = text
            self.message(f"[flavor]{text}[/flavor]")

    def _maybe_queue_lore(self, item) -> None:
        """Queue lore generation for any identified item that hasn't had lore generated yet."""
        if not self.llm.enabled:
            return
        name = getattr(item, "name", None)
        if not name or name in self._lore_futures or name in self._lore_done:
            return
        rec = self.ident.get(name)
        if rec and not rec["identified"]:
            return  # unidentified consumable — identify() will handle it when used
        self._lore_futures[name] = self.llm.complete_async(self._build_lore_prompt(item))

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
                if self.llm.enabled and item.name not in self._lore_futures:
                    self._lore_futures[item.name] = self.llm.complete_async(
                        self._build_lore_prompt(item)
                    )

    # --- level generation & travel -------------------------------------
    def _new_level(self, depth: int) -> DungeonMap:
        is_last = depth >= config.depth.floors
        theme = self._generate_floor_theme(depth)
        self._floor_themes[depth] = theme
        layout = generate_level(
            is_last=is_last,
            depth=depth,
            layout_hint=theme.layout_bias if theme else "any",
            structures=theme.structures if theme else None,
            terrain_features=theme.terrain_features if theme else None,
        )
        level = DungeonMap(game=self, layout=layout)
        self._populate(level, depth, is_last, theme=theme)
        return level

    def _enemies_for_depth(self, depth: int) -> list[str]:
        """Return names of non-boss enemies valid for the given depth."""
        return [e.data.name for e in self.db.enemy_db.all_for_depth(depth)]

    def _generate_floor_theme(self, depth: int) -> "FloorTheme | None":
        if not self.llm.enabled:
            return None
        history_ctx = "\n".join(self._theme_history[-3:]) or "none yet"
        valid_at_depth = self._enemies_for_depth(depth)
        messages = [
            {"role": "system", "content": (
                "You are a dungeon theme generator for a dark fantasy roguelike. "
                "Output ONLY a single valid JSON object with exactly these keys: "
                "name (string), description (string), "
                "layout_bias (exactly one of: cave rooms bsp any), "
                f"enemy_bias (JSON array of 0-3 names chosen ONLY from: {', '.join(_VALID_BIAS_ENEMIES)}), "
                "trap_type (exactly one of: dart poison teleport alarm any), "
                "trap_density (exactly one of: low normal high), "
                "loot_bias (exactly one of: potions scrolls weapons gold balanced), "
                "ambient (one atmospheric sentence, max 15 words), "
                "structures (JSON array of 0-2 names chosen ONLY from: "
                "shrine mushroom_grove overgrown_room ruined_hall frozen_pond campsite poison_marsh standing_stones), "
                "terrain_features (JSON array of 0-2 names chosen ONLY from: lava_pools chasms). "
                "Choose structures and terrain_features that match the theme's name and description. "
                "No markdown fences, no explanation, no thinking — pure JSON only."
            )},
            {"role": "user", "content": (
                f"Depth {depth} of {config.depth.floors}. "
                f"Previous floor themes for narrative continuity:\n{history_ctx}\n"
                f"Enemies available at depth {depth}: {', '.join(valid_at_depth)}. "
                "Generate the theme for this floor."
            )},
        ]
        future = self.llm.complete_json_async(messages, max_tokens=2500, timeout=90.0)
        clear_screen()
        self.print(f"[stairs]Descending to Depth {depth}...[/stairs]", highlight=False)
        from rich.live import Live
        from rich.text import Text
        with Live(console=self.rich_console, refresh_per_second=10) as live:
            i = 0
            while not future.done():
                live.update(Text.from_markup(
                    f"[flavor]{_THEME_SPINNER[i % len(_THEME_SPINNER)]} The dungeon stirs...[/flavor]"
                ))
                time.sleep(0.1)
                i += 1
        data = future.result()
        if not isinstance(data, dict):
            return None
        _valid_layout = {"cave", "rooms", "bsp", "any"}
        _valid_trap = {"dart", "poison", "teleport", "alarm", "any"}
        _valid_density = {"low", "normal", "high"}
        _valid_loot = {"potions", "scrolls", "weapons", "gold", "balanced"}
        validated_structures = [
            s for s in (data.get("structures") or [])
            if isinstance(s, str) and s in _VALID_STRUCTURES
        ][:2]
        validated_terrain_features = [
            t for t in (data.get("terrain_features") or [])
            if isinstance(t, str) and t in _VALID_TERRAIN_FEATURES
        ][:2]
        theme = FloorTheme(
            name=str(data.get("name", "")),
            description=str(data.get("description", "")),
            layout_bias=data.get("layout_bias", "any") if data.get("layout_bias") in _valid_layout else "any",
            enemy_bias=[e for e in (data.get("enemy_bias") or []) if e in _VALID_BIAS_ENEMIES],
            trap_type=data.get("trap_type", "any") if data.get("trap_type") in _valid_trap else "any",
            trap_density=data.get("trap_density", "normal") if data.get("trap_density") in _valid_density else "normal",
            loot_bias=data.get("loot_bias", "balanced") if data.get("loot_bias") in _valid_loot else "balanced",
            ambient=str(data.get("ambient", "")),
            structures=validated_structures,
            terrain_features=validated_terrain_features,
        )
        if theme.name:
            self._theme_history.append(f"{theme.name}: {theme.description}")
        return theme

    def _populate(self, level: DungeonMap, depth: int, is_last: bool, theme=None) -> None:
        pool = list(level.floor_cells)
        random.shuffle(pool)
        suy, sux = level.stairs_up

        def far_cell():
            while pool:
                y, x = pool.pop()
                if abs(y - suy) + abs(x - sux) > 3:
                    return (y, x)
            return None

        # Monsters (count scales with depth); biased towards theme enemies when theme present.
        count = config.spawn.enemies_base + config.spawn.enemies_per_depth * (depth - 1)
        for _ in range(count):
            if theme and theme.enemy_bias and random.random() < 0.6:
                loader = self.db.enemy_db.random_biased(depth, theme.enemy_bias)
            else:
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

        # Loose loot (counts biased by floor theme when present).
        loot = theme.loot_bias if theme else "balanced"
        if loot == "potions":    pot_n, scr_n, wpn_n, gold_mult = 5, 1, 1, 1.0
        elif loot == "scrolls":  pot_n, scr_n, wpn_n, gold_mult = 1, 4, 1, 1.0
        elif loot == "weapons":  pot_n, scr_n, wpn_n, gold_mult = 1, 1, 4, 1.0
        elif loot == "gold":     pot_n, scr_n, wpn_n, gold_mult = 1, 1, 1, 2.5
        else:                    pot_n, scr_n, wpn_n, gold_mult = config.spawn.floor_potions, config.spawn.floor_scrolls, config.spawn.floor_weapons, 1.0
        for _ in range(pot_n):
            self._scatter(level, self._depth_potion(depth))
        for _ in range(scr_n):
            self._scatter(level, random.choice(self.db.item_db.scrolls))
        for _ in range(wpn_n):
            self._scatter(level, random.choice(self.db.item_db.weapons[1:]))
        for _ in range(config.spawn.gold_piles):
            cell = self._floor_cell(level)
            if cell:
                cell.gold += int(random.randint(2, 6 + depth * 2) * gold_mult)

        # Hidden traps (depth-scaled, density and type biased by theme).
        _density_mult = {"low": 0.5, "normal": 1.0, "high": 1.8}
        density = _density_mult.get(theme.trap_density if theme else "normal", 1.0)
        trap_count = max(1, int((config.spawn.traps_base + depth // 2) * density))
        trap_pool = ["dart", "poison", "teleport", "alarm"]
        if theme and theme.trap_type != "any":
            trap_pool = [theme.trap_type] * 3 + trap_pool
        for _ in range(trap_count):
            y, x = random.choice(level.floor_cells)
            cell = level.matrix[y][x]
            if cell.trap is None and not cell.items and cell.gold == 0 \
                    and abs(y - suy) + abs(x - sux) > 4:
                cell.trap = random.choice(trap_pool)

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
        if depth in _SHARD_FLOORS:
            shard_name, guardian_name = _SHARD_FLOORS[depth]
            sy, sx = cells.pop()
            level.matrix[sy][sx].items.append(DungeonShard(shard_name))
            level.matrix[sy][sx].gold += random.randint(30, 60)
            loader = self.db.enemy_db.search_enemy(name=guardian_name)
            if loader and cells:
                gy, gx = min(cells, key=lambda c: abs(c[0] - sy) + abs(c[1] - sx))
                boss = loader.load()
                boss.awake = True
                level.place_occupant(boss, gy, gx)
                level.enemies.append(boss)
            if is_last and cells:  # legendary blade still rewards reaching the deepest floor
                bsy, bsx = cells.pop()
                level.matrix[bsy][bsx].items.append(self.db.item_db.search_item(name="Sword of Zot"))
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
        theme = self._floor_themes.get(depth)
        if theme and theme.name:
            self.message(f"[flavor]{theme.name}[/flavor]")
        if theme and theme.ambient:
            self.message(f"[flavor]{theme.ambient}[/flavor]")
        if depth >= 6:
            self._queue_hint(f"deep_floor_{depth}", {
                "trigger": f"player descends to depth {depth}, one of the deepest and most dangerous floors",
                "depth": depth, "background": self.player.background,
                "hp": self.player.health, "max_hp": self.player.max_health,
            })
        else:
            self._queue_hint(f"floor_{depth}", {
                "trigger": f"player descends to depth {depth} of the dungeon",
                "depth": depth, "background": self.player.background,
                "hp": self.player.health, "max_hp": self.player.max_health,
            })

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
        if enemy.tier != "boss":
            self._queue_hint("first_kill", {
                "trigger": f"player slew their first enemy, a {enemy.name}",
                "depth": self.depth, "background": self.player.background,
                "hp": self.player.health, "max_hp": self.player.max_health,
            })
        if enemy.tier == "boss":
            self.message("[success]The guardian falls! The shard lies unguarded — take it.[/success]")
            self._queue_hint(f"boss_{enemy.name}", {
                "trigger": f"player just slew the {enemy.name}, a powerful boss guardian",
                "depth": self.depth, "background": self.player.background,
                "hp": self.player.health, "max_hp": self.player.max_health,
            })

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
        if isinstance(item, DungeonShard):
            cell.items.remove(item)
            self.player.shards.add(item.name)
            count = len(self.player.shards)
            self.message(f"[shard]You seize the {item.name}! ({count}/3 sigil shards)[/shard]")
            if count == 3:
                self.message("[warn]The Broken Sigil is whole. The dungeon shudders — flee to the surface![/warn]")
                self.awaken_floor()
                self._queue_hint("all_shards", {
                    "trigger": "player assembled the complete Broken Sigil and must now flee to the surface",
                    "depth": self.depth, "background": self.player.background,
                    "hp": self.player.health, "max_hp": self.player.max_health,
                })
            else:
                remaining = 3 - count
                self.message(f"[flavor]{remaining} shard{'s' if remaining > 1 else ''} remain hidden in the depths.[/flavor]")
                if count == 1:
                    self._queue_hint("first_shard", {
                        "trigger": "player collected the first shard of a broken sigil",
                        "depth": self.depth, "background": self.player.background,
                        "hp": self.player.health, "max_hp": self.player.max_health,
                    })
            return True
        if len(self.player.inventory) >= self.player.max_inventory:
            self.message("Your pack is full.")
            return False
        cell.items.remove(item)
        self.player.inventory.append(item)
        self.message(f"You pick up the {style_text(self.display_name(item), 'item')}.")
        self._maybe_queue_lore(item)
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
            if len(self.player.shards) == 3:
                self.game_over("win")
            else:
                missing = 3 - len(self.player.shards)
                self.message(
                    f"[warn]You cannot leave — {missing} shard{'s' if missing > 1 else ''} "
                    f"of the Broken Sigil still lie in the depths.[/warn]"
                )
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
        def passable(y, x):
            c = self.map.matrix[y][x]
            if c.occupant is not None:
                return False
            if c.terrain in (T.WALL, T.SECRET_DOOR):
                return False
            if c.trap and not c.trap_hidden:
                return False
            if (y, x) in self.map.excluded_stairs:
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

        for _ in range(1000):
            if self.over or self.map.visible_enemies():
                if self.map.visible_enemies():
                    self.message("[warn]A monster comes into view.[/warn]")
                break

            visible_before = frozenset(self.map.visible)
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

            # Pause if a staircase just entered view for the first time.
            for cy, cx in self.map.visible - visible_before:
                terrain = self.map.matrix[cy][cx].terrain
                if terrain == T.STAIRS_DOWN:
                    self.message("[stairs]Auto-explore paused: staircase down spotted.[/stairs]")
                    return
                if terrain == T.STAIRS_UP:
                    self.message("[stairs]Auto-explore paused: staircase up spotted.[/stairs]")
                    return

    def _dir_to(self, ny: int, nx: int) -> str | None:
        return {(-1, 0): "n", (1, 0): "s", (0, -1): "w", (0, 1): "e",
                (-1, -1): "nw", (-1, 1): "ne", (1, -1): "sw", (1, 1): "se"}.get(
            (ny - self.player.y, nx - self.player.x))

    # --- staircase navigation -------------------------------------------
    def goto_stairs_menu(self) -> None:
        """G key: prompt the player to navigate to nearest up or down stairs."""
        self.message("[stairs]Go to: [controls]<[/controls] up-stairs  "
                     "[controls]>[/controls] down-stairs  [controls]esc[/controls] cancel[/stairs]")
        self.render()
        key = keys.read_key()
        if key == "<":
            self.goto_stairs("up")
        elif key == ">":
            self.goto_stairs("down")

    def goto_stairs(self, direction: str) -> None:
        """Walk to the nearest known staircase of the given type ('up' or 'down')."""
        coord = self.map.stairs_up if direction == "up" else self.map.stairs_down
        name = "up-stairs" if direction == "up" else "down-stairs"
        if coord is None:
            self.message(f"There are no {name} on this floor.")
            return
        sy, sx = coord
        if not self.map.matrix[sy][sx].explored:
            self.message(f"You haven't found the {name} yet.")
            return
        if self.player.location == coord:
            self.message(f"You are already at the {name}.")
            return

        def passable(y, x):
            c = self.map.matrix[y][x]
            return (c.occupant is None
                    and c.terrain not in (T.WALL, T.SECRET_DOOR)
                    and not (c.trap and not c.trap_hidden))

        is_goal = lambda cur: cur == coord

        path = self.map.bfs_path(self.player.location, is_goal, passable)
        if not path:
            self.message(f"No clear path to the {name}.")
            return

        self.message(f"[stairs]Travelling to {name}...[/stairs]")
        for _ in range(1000):
            if self.over or self.map.visible_enemies():
                if self.map.visible_enemies():
                    self.message("[warn]A monster comes into view.[/warn]")
                break
            if self.player.location == coord:
                break
            path = self.map.bfs_path(self.player.location, is_goal, passable)
            if not path:
                self.message(f"Path to {name} is blocked.")
                break
            ny, nx = path[0]
            d = self._dir_to(ny, nx)
            if d is None or not self.player.move(d):
                break
            self.spend_turn()
            self.advance_world()
            self.render()
            time.sleep(0.03)

    def view_stair(self, direction: str) -> None:
        """[ / ] keys: pan the camera to a known staircase and highlight it."""
        coord = self.map.stairs_up if direction == "up" else self.map.stairs_down
        name = "up-stairs" if direction == "up" else "down-stairs"
        if coord is None:
            self.message(f"There are no {name} on this floor.")
            return
        sy, sx = coord
        if not self.map.matrix[sy][sx].explored:
            self.message(f"You haven't found the {name} yet.")
            return
        py, px = self.player.location
        dist = abs(sy - py) + abs(sx - px)
        excl = " [warn](excluded)[/warn]" if coord in self.map.excluded_stairs else ""
        self.camera_override = coord
        self.stair_cursor = coord
        self.message(
            f"[stairs]{name.capitalize()} is ~{dist} steps away{excl}. "
            f"[controls]G[/controls]+[controls]{'<' if direction == 'up' else '>'}[/controls] "
            f"to travel · any key to return view[/stairs]"
        )

    def exclude_stair(self) -> None:
        """X key: toggle the staircase under the player in/out of the auto-explore exclusion set."""
        terrain = self.player.cell.terrain
        if terrain not in (T.STAIRS_UP, T.STAIRS_DOWN):
            self.message("Stand on a staircase to exclude it from auto-explore.")
            return
        coord = self.player.location
        kind = "Up-stairs" if terrain == T.STAIRS_UP else "Down-stairs"
        if coord in self.map.excluded_stairs:
            self.map.excluded_stairs.discard(coord)
            self.message(f"[stairs]{kind} exclusion removed.[/stairs]")
        else:
            self.map.excluded_stairs.add(coord)
            self.message(f"[warn]{kind} excluded from auto-explore.[/warn]")

    def auto_pickup_menu(self) -> None:
        """Backslash key: toggle which item types are automatically picked up on contact."""
        OPTIONS = [
            ("potion", "Potions",  "potions", "!"),
            ("scroll", "Scrolls",  "scroll",  "?"),
            ("weapon", "Weapons",  "weapons", ")"),
            ("bag",    "Bags",     "bag",     "("),
        ]
        while True:
            clear_screen()
            self.print(
                "[menu_header]Auto-pickup settings[/menu_header] "
                "(number to toggle, [controls]esc[/controls] to close)\n"
            )
            for i, (key, label, style, sym) in enumerate(OPTIONS, 1):
                state = "[success]ON [/success]" if key in self.auto_pickup_types else "[warn]OFF[/warn]"
                self.print(
                    f"  [controls]{i}[/controls]  [{style}]{sym} {label}[/{style}]  {state}",
                    highlight=False,
                )
            k = keys.read_key()
            if k == keys.ESC:
                break
            if k.isdigit() and 1 <= int(k) <= len(OPTIONS):
                typ = OPTIONS[int(k) - 1][0]
                if typ in self.auto_pickup_types:
                    self.auto_pickup_types.discard(typ)
                else:
                    self.auto_pickup_types.add(typ)
        self.render()

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
        # Clear stair-view overlay on any key that isn't cycling stair views.
        if key not in ("[", "]") and self.camera_override is not None:
            self.camera_override = None
            self.stair_cursor = None

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
        if key == "G":
            self.goto_stairs_menu()
            return False
        if key == "[":
            self.view_stair("up")
            return False
        if key == "]":
            self.view_stair("down")
            return False
        if key == "X":
            self.exclude_stair()
            return False
        if key == "\\":
            self.auto_pickup_menu()
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
            clear_screen()
            self.print(
                f"Quit the game? "
                f"{style_text('y', 'controls')} yes   "
                f"{style_text('n', 'controls')} / {style_text('esc', 'controls')} no",
                highlight=False,
            )
            confirm = keys.read_key()
            if confirm == "y":
                self.over = True
                self.log.info("game exited by player")
                clear_screen()
                print("Exiting [Dungeon]...")
                sys.exit()
            self.render()
            return False
        return False

    def help_screen(self) -> None:
        clear_screen()
        self.print(Panel(
            "[menu_header]Dungeon.py — Controls[/menu_header]\n\n"
            "[controls]arrows[/controls] or [controls]hjkl[/controls]  move / attack (walk into a monster)\n"
            "[controls]yubn[/controls]  diagonal movement (nw / ne / sw / se)\n"
            "[controls]f[/controls]  fire a ranged weapon (aim, then [controls]f[/controls]/[controls]enter[/controls]; [controls]tab[/controls] next target)\n"
            "[controls]o[/controls]  autoexplore the floor (pauses on enemy or new staircase)\n"
            "[controls]g[/controls]  pick up items on your tile (choose which, or take all)\n"
            "[controls]i[/controls] / [controls]d[/controls]  open pack — use, equip, unequip, drop\n"
            "[controls]>[/controls] / [controls]<[/controls]  descend / ascend stairs\n"
            "[controls]G[/controls]  goto stairs — then [controls]<[/controls] or [controls]>[/controls] to walk to nearest up/down staircase\n"
            "[controls][[/controls] / [controls]][/controls]  pan view to known up-stairs / down-stairs (any key returns)\n"
            "[controls]X[/controls]  exclude staircase under you from auto-explore (toggle)\n"
            "[controls]\\\\[/controls]  auto-pickup settings — toggle which item types are grabbed on contact\n"
            "[controls]s[/controls]  search adjacent tiles for secret doors and traps\n"
            "[controls].[/controls] or [controls]space[/controls]  wait one turn\n"
            "[controls]p[/controls]  pause    [controls]esc[/controls]  quit\n\n"
            "[flavor]At a trader/healer, press [controls]space[/controls] to step past them.[/flavor]\n"
            "[flavor]Developer: [controls]~[/controls] toggles god mode (or set DUNGEON_GODMODE=1).[/flavor]\n\n"
            "[flavor]Find all three shards of the Broken Sigil (depths 6–8) and escape to the surface.[/flavor]\n\n"
            f"Press {style_text('any key', 'controls')} to return.",
            border_style="grey37"))
        keys.read_key()

    # --- endgame --------------------------------------------------------
    def record_leaderboard(self, outcome: str) -> None:
        self.leaderboard.insert({
            "name": self.player.name,
            "outcome": outcome,
            "depth": self.depth,
            "shards": len(self.player.shards),
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
                f"[success]You escape the dungeon with the Broken Sigil made whole![/success]\n"
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
