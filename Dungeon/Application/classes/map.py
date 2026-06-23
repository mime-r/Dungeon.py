# -*- coding: utf-8 -*-
"""Map model and the player entity.

A floor is a matrix of :class:`DungeonCell`. Each cell has a *terrain* (floor / wall /
door / stairs), an optional living *occupant* (enemy or NPC), ground *items*, and a
*gold* pile. The player is tracked separately by location and drawn on top.
"""

import copy
import random

from ..utils import style_text
from ..config import config
from .items import (
    DungeonWeapon, DungeonPotion, DungeonScroll, DungeonThrowable,
    DungeonInventory, DungeonArmour, DungeonShard, DungeonSpellBook,
)
from .status import StatusSet
from .skills import SkillSet, skill_for_weapon
from .items import DungeonSpell

T = config.terrain

DIRS = {
    "n": (-1, 0), "s": (1, 0), "w": (0, -1), "e": (0, 1),
    "ne": (-1, 1), "nw": (-1, -1), "se": (1, 1), "sw": (1, -1),
}

# Imported lazily at the bottom of this module to avoid a circular import.
from .brands import brand_on_hit, BRAND_TABLE_REF  # noqa: E402

# Weapon brands applied by the Scroll of Brand Weapon. Each entry describes
# the extra damage roll, the chance of that roll, and any bonus status effect
# on a successful hit. Mirrors DCSS-style brand flavour.
#
# Spec keys:
#   style / verb         - rich markup style + verb shown in impact message
#   dmg / dmg_chance     - extra damage roll (lo, hi) and probability of fire
#   status / status_*    - bonus status effect on hit
#   on_hit(player, enemy, game) - custom callback for complex brands
#   speed_mod            - while equipped, +/- to effective_speed
#   damage_pct           - multiplier on base damage (1.0 = no change)
#   accuracy_mod         - while equipped, +/- to weapon accuracy
#   on_equip(player)     - called when weapon is equipped
#   on_unequip(player)   - called when weapon is unequipped
BRAND_TABLE = {
    # --- Elemental brands (DCSS flaming/freezing/electrocution/holy/pain) ---
    "flaming": {
        "style": "fire", "verb": "scorches",
        "dmg": (2, 5), "dmg_chance": 0.5,
    },
    "freezing": {
        "style": "ice", "verb": "freezes",
        "dmg": (1, 3), "dmg_chance": 0.5,
        "status": "slow", "status_chance": 0.5,
        "status_duration": 3, "status_potency": 1,
        "status_verb": "slowed",
    },
    "venom": {
        "style": "poison", "verb": "coats",
        "dmg": (0, 0), "dmg_chance": 0.0,
        "status": "poison", "status_chance": 0.6,
        "status_duration": 5, "status_potency": 1,
        "status_verb": "poisoned",
    },
    "electrocution": {
        "style": "lightning", "verb": "shocks",
        "dmg": (2, 6), "dmg_chance": 0.5,
    },
    "pain": {
        "style": "arcane", "verb": "torments",
        "dmg": (2, 4), "dmg_chance": 0.5,
    },
    "holy_wrath": {
        "style": "arcane", "verb": "blesses",
        "dmg": (3, 7), "dmg_chance": 0.5,
        # DCSS: Holy Wrath does an average of 75% extra damage to demonic/undead.
        # Applied as a damage_pct multiplier against those holiness tags.
        "dmg_pct_vs_holiness": {"undead": 0.75, "demonic": 0.75},
    },
    "draining": {
        "style": "arcane", "verb": "drains",
        "dmg": (1, 2), "dmg_chance": 0.5,
    },
    # --- New DCSS brands ---
    "antimagic": {
        "style": "arcane", "verb": "disrupts",
        "dmg": (0, 0), "dmg_chance": 0.0,
        "on_hit": "_brand_antimagic",
    },
    "chaos": {
        "style": "arcane", "verb": "warps",
        "on_hit": "_brand_chaos",
    },
    "distortion": {
        "style": "arcane", "verb": "distorts",
        "on_hit": "_brand_distortion",
    },
    "heavy": {
        "style": "arcane", "verb": "crushes",
        "dmg": (3, 6), "dmg_chance": 0.6,
        "speed_mod": -3,
        "damage_pct": 0.6,
    },
    "protection": {
        "style": "arcane", "verb": "shields",
        "dmg": (0, 0), "dmg_chance": 0.0,
        "on_hit": "_brand_protection",
    },
    "spectral": {
        "style": "arcane", "verb": "phases",
        "dmg": (1, 2), "dmg_chance": 0.5,
        "on_hit": "_brand_spectral",
    },
    "speed": {
        "style": "haste", "verb": "whirls",
        "dmg": (1, 2), "dmg_chance": 0.4,
        "speed_mod": 3,
        "accuracy_mod": 5,
    },
    "vampiric": {
        "style": "arcane", "verb": "drains life",
        "dmg": (0, 0), "dmg_chance": 0.0,
        "on_hit": "_brand_vampiric",
    },
}

# Make the brand table visible to the brand-callback module so the dispatch
# table there can reference it by key.
from .brands import BRAND_TABLE_REF  # noqa: E402
BRAND_TABLE_REF.update(BRAND_TABLE)


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
        self.armour: dict[str, object | None] = {
            "body": None, "shield": None, "helmet": None,
            "cloak": None, "gloves": None, "boots": None,
        }
        self.location: tuple[int, int] = (0, 0)
        self.name: str | None = None
        self.background: str | None = None
        self.shards: set[str] = set()
        self.game = game
        # progression
        self.level = 1
        self.xp = 0
        self.xp_next = config.progression.xp_for(1)
        # status + turn economy
        self.status = StatusSet()
        self.energy = 0
        self.speed = 10
        self.skills = None
        # magic
        self.mp = 0
        self.max_mp = 0
        self.intelligence = 8
        self.known_spells: list[DungeonSpell] = []
        self._channeling: dict = {}  # spell_name -> current tick (1..N)
        self._channel_targets: dict = {}  # spell_name -> locked target object

    def effective_speed(self) -> int:
        s = self.speed
        if self.status.has("haste"):
            s += 5
        if self.status.has("slow"):
            s -= 5
        # Weapon brand speed mod (DCSS Speed/Heavy).
        weapon = getattr(self, "equipped", None)
        if weapon is not None:
            brand = getattr(weapon, "brand", None)
            if brand:
                spec = BRAND_TABLE.get(brand)
                if spec and "speed_mod" in spec:
                    s += spec["speed_mod"]
        return max(1, s)

    def combat_bonus(self) -> tuple[int, int]:
        """Return (damage_bonus, accuracy_bonus) from level, skills, and Might."""
        prog = config.progression
        dmg = self.level // prog.damage_every + self.status.potency("might")
        acc = self.level * prog.accuracy_per_level
        if self.skills:
            dmg += int(self.skills.get_level("Fighting") * 0.5)
            weapon = self.equipped
            if weapon:
                wskill = skill_for_weapon(weapon.name)
                if wskill:
                    dmg += int(self.skills.get_level(wskill) * 0.3)
                    acc += int(self.skills.get_level(wskill) * 1.5)
        return dmg, acc

    def armor_class(self) -> int:
        """Total AC from all worn armour and Armour skill."""
        base = sum((piece.ac + getattr(piece, "enchant", 0)) for piece in self.armour.values() if piece)
        if self.skills:
            base += int(self.skills.get_level("Armour") * 0.2)
        # Temporary AC buff (DCSS Protection brand and similar).
        if self.status.has("ac_buff"):
            base += self.status.potency("ac_buff")
        return base

    def total_encumbrance(self) -> int:
        """Combined encumbrance rating of worn body armour and shield, eased by level
        and Armour skill."""
        body, shield = self.armour.get("body"), self.armour.get("shield")
        raw = (body.encumbrance if body else 0) + (shield.encumbrance if shield else 0)
        reduction = self.level // 4
        if self.skills:
            reduction += int(self.skills.get_level("Armour") * 0.3)
        return max(0, raw - reduction)

    def evasion(self) -> int:
        """Shield SH plus Dodging skill, minus encumbrance. Includes ego bonuses
        (Stealth cloak +EV, Parrying gloves +SH)."""
        shield = self.armour.get("shield")
        sh = shield.sh if shield else 0
        cloak = self.armour.get("cloak")
        if cloak:
            sh += getattr(cloak, "ev_bonus", 0)
        gloves = self.armour.get("gloves")
        if gloves:
            sh += getattr(gloves, "sh_bonus", 0)
        if self.skills:
            sh += int(self.skills.get_level("Shields") * 0.5)
            sh += int(self.skills.get_level("Dodging") * 0.3)
        return max(0, sh - self.total_encumbrance())

    def has_see_invisible(self) -> bool:
        """True if any SInv ego or status effect lets the player see through walls."""
        if self.status.has("see_invisible"):
            return True
        helmet = self.armour.get("helmet")
        if helmet and getattr(helmet, "grant_see_invisible", False):
            return True
        return False

    def aggregate_resistances(self) -> dict[str, int]:
        """Sum resistance levels from all equipped armour pieces."""
        result: dict[str, int] = {}
        for piece in self.armour.values():
            if not piece:
                continue
            for dmg_type, level in getattr(piece, "resistances", {}).items():
                result[dmg_type] = max(result.get(dmg_type, 0), level)
        return result

    def ranged_damage_bonus(self) -> float:
        """Sum the ranged-damage % from gloves + helmet ego bonuses."""
        bonus = 0.0
        for slot in ("gloves", "helmet"):
            piece = self.armour.get(slot)
            if piece:
                bonus += getattr(piece, "ranged_dmg_bonus", 0.0)
        return bonus

    def apply_resistance(self, damage_type: str, amount: int) -> int:
        """Reduce `amount` by the player's resistance to `damage_type`.

        r+ = 33 % reduction, r++ = 67 % (we currently cap at 1 level).
        Unknown damage types and 0 resistance return the amount unchanged.
        """
        if not amount or amount <= 0:
            return amount
        resistances = self.aggregate_resistances()
        level = resistances.get(damage_type, 0)
        if level <= 0:
            return amount
        return max(1, int(amount * (1.0 - 0.33 * level)))

    def stealth_penalty(self) -> int:
        """How much further away encumbered armour lets sleeping enemies notice you."""
        base = self.total_encumbrance() // 4
        if self.skills:
            base = max(0, base - int(self.skills.get_level("Stealth") * 0.25))
        return base

    def ranged_encumbrance_delay(self) -> int:
        """Extra energy cost applied after firing a ranged weapon while encumbered."""
        return self.total_encumbrance() // 2

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
            # MP level up
            if self.max_mp > 0:
                mp_gain = max(1, int(self.intelligence * 0.3))
                self.max_mp += mp_gain
                self.mp = min(self.max_mp, self.mp + mp_gain)
                self.game.message(f"[haste](+{mp_gain} max MP)[/haste]")

    @property
    def x(self) -> int:
        return self.location[1]

    @property
    def y(self) -> int:
        return self.location[0]

    @property
    def cell(self) -> DungeonCell:
        return self.game.map.matrix[self.y][self.x]

    def attack_cost(self) -> int:
        """Energy cost of one melee attack with the equipped weapon.

        Reads the weapon's base delay, then reduces by weapon-skill level
        (DCSS: every 2 skill levels = -1 delay, floored at min_delay).
        Returns TURN when unarmed.
        """
        from .skills import skill_for_weapon
        from ..config import config as _cfg
        TURN = 10
        weapon = getattr(self, "equipped", None)
        if weapon is None or not hasattr(weapon, "delay"):
            return TURN
        base_delay = max(1, getattr(weapon, "delay", TURN))
        min_delay = max(1, getattr(weapon, "min_delay", max(3, base_delay // 2)))
        wskill = skill_for_weapon(weapon.name)
        skill_level = 0.0
        if wskill and self.skills:
            skill_level = self.skills.get_level(wskill)
        reduction = int(skill_level // 2)
        effective = max(min_delay, base_delay - reduction)
        # Brand speed_mod already folds into effective_speed; here we just
        # return the base cost so the turn scheduler sees it.
        return max(1, effective)

    def move(self, direction: str) -> int:
        """Attempt to act in a direction. Returns the energy cost of the action,
        or 0 if the action was blocked (no turn spent)."""
        from ..config import config as _cfg
        TURN = 10
        dy, dx = DIRS[direction]
        ny, nx = self.y + dy, self.x + dx
        game = self.game
        if not game.map.in_bounds(ny, nx):
            return 0
        # Player cannot act on tiles they have never seen and cannot currently see.
        if (ny, nx) not in game.map.visible:
            dest_cell = game.map.matrix[ny][nx]
            if not dest_cell.explored:
                return 0
        cell = game.map.matrix[ny][nx]

        if cell.occupant is not None:
            if getattr(cell.occupant, "is_enemy", False):
                self.attack(cell.occupant)
                return self.attack_cost()
            if getattr(cell.occupant, "is_summon", False):
                game.message(f"[action]Swapped places with {style_text(cell.occupant.name, 'item')}.[/action]")
                game.map.move_occupant(cell.occupant, self.y, self.x)
                self.location = (ny, nx)
                if self.skills:
                    self.skills.record("Dodging")
                    self.skills.record("Stealth")
                self._on_enter(cell)
                return TURN
            return game.interact_npc(cell.occupant)  # bump an NPC to trade/heal or step past

        if cell.terrain == T.DOOR_CLOSED:
            cell.terrain = T.DOOR_OPEN
            game.message("You open the door.")
            return TURN
        if cell.terrain in T.blocks_sight:  # wall or undiscovered secret door
            return 0
        if not cell.walkable:
            return 0

        self.location = (ny, nx)
        if self.skills:
            self.skills.record("Dodging")
            self.skills.record("Stealth")
        self._on_enter(cell)
        return TURN

    def _on_enter(self, cell: DungeonCell) -> None:
        game = self.game
        if cell.trap and cell.trap_hidden:
            game.trigger_trap(cell)
        if cell.feature == "altar":
            game.bless_at_altar(cell)
        if cell.gold > 0 and "gold" in getattr(game, "auto_pickup_types", set()):
            game.player.coins += cell.gold
            game.message(f"You pick up {style_text(str(cell.gold) + ' gold', 'gold')}.")
            cell.gold = 0
        if cell.items:
            _AUTO_KIND = {
                "DungeonPotion": "potion", "DungeonScroll": "scroll",
                "DungeonWeapon": "weapon", "DungeonThrowable": "throwable",
                "DungeonInventory": "bag", "DungeonArmour": "armour",
                "DungeonSpellBook": "spellbook",
            }
            auto_types = getattr(game, "auto_pickup_types", set())
            for item in list(cell.items):
                kind = _AUTO_KIND.get(type(item).__name__)
                if kind in auto_types and (kind == "throwable" or len(self.inventory) < self.max_inventory):
                    if game.collect_item(item):
                        pass
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
        if self.skills:
            wskill = skill_for_weapon(weapon.name)
            if wskill:
                self.skills.record(wskill)
            self.skills.record("Fighting")
        if self.game.godmode:
            self.game.message(f"[warn][GOD][/warn] You annihilate the {enemy_name}.")
            enemy.health = 0
            self.game.on_enemy_death(enemy)
            return
        dmg_bonus, acc_bonus = self.combat_bonus()
        # Brand-based accuracy modifier (DCSS Speed brand).
        brand_acc_mod = 0
        brand = getattr(weapon, "brand", None)
        if brand:
            spec = BRAND_TABLE.get(brand)
            if spec:
                brand_acc_mod = spec.get("accuracy_mod", 0)
        # Enchantment accuracy bonus (DCSS: +1 to-hit per +1 enchant).
        enchant_acc = getattr(weapon, "enchant", 0)
        if random.randint(1, 100) <= weapon.accuracy + acc_bonus + brand_acc_mod + enchant_acc:
            raw = random.randint(weapon.attack_range[0], weapon.attack_range[1])
            enchant = getattr(weapon, "enchant", 0)
            damage = max(1, weapon.base_attack + raw + dmg_bonus + enchant)
            # Brand-based damage percentage (DCSS Heavy: +80% base damage).
            if brand:
                spec = BRAND_TABLE.get(brand)
                if spec and "damage_pct" in spec:
                    damage = max(1, int(damage * (1.0 + spec["damage_pct"])))
            # Per-holiness bonus: weapon gets a damage multiplier vs a specific
            # enemy holiness (e.g., Sacred Scourge vs undead = +50%).
            enemy_holiness = getattr(enemy, "holiness", "natural")
            holiness_bonus = getattr(weapon, "dmg_pct_vs_holiness", {}).get(enemy_holiness, 0)
            if holiness_bonus > 0:
                damage = max(1, int(damage * (1.0 + holiness_bonus)))
                self.game.message(
                    f"[haste]{style_text(weapon.name, 'weapons')} burns "
                    f"with holy conviction against the {style_text(enemy.name, 'enemy')}![/haste]",
                    drop=damage,
                )
            crit = raw == weapon.attack_range[1]
            template = weapon.texts.critical_hit if crit else weapon.texts.hit
            self.game.message(template.format(enemy_name, weapon_name), drop=damage)
            enemy.health -= damage
            if enemy.health <= 0:
                self.game.on_enemy_death(enemy)
            else:
                self.apply_weapon_on_hit(weapon, enemy)
                self.apply_weapon_brand(weapon, enemy)
        else:
            self.game.message(weapon.texts.missed_hit.format(enemy_name, weapon_name))

    def apply_weapon_brand(self, weapon, enemy) -> None:
        """Apply a brand-induced extra damage roll and status (Scroll of Brand Weapon)."""
        brand = getattr(weapon, "brand", None)
        if not brand:
            return
        spec = BRAND_TABLE.get(brand)
        if not spec:
            return
        # Extra elemental damage (dmg_dice)
        if "dmg" in spec and spec["dmg"] != (0, 0) and random.random() < spec.get("dmg_chance", 1.0):
            lo, hi = spec["dmg"]
            extra = random.randint(lo, hi)
            enemy.health -= extra
            self.game.message(
                f"[{spec.get('style', 'fire')}]"
                f"The {style_text(weapon.name, 'weapons')} {spec.get('verb', 'burns')} the "
                f"{style_text(enemy.name, 'enemy')} for {extra} extra damage![/{spec.get('style', 'fire')}]",
                drop=extra,
            )
        # Bonus status effect
        if "status" in spec and random.random() < spec.get("status_chance", 1.0):
            eff = spec["status"]
            enemy.status.add(
                eff,
                spec.get("status_duration", 4),
                spec.get("status_potency", 1),
            )
            self.game.message(
                f"[{spec.get('style', 'fire')}]The {style_text(enemy.name, 'enemy')} is "
                f"{spec.get('status_verb', 'afflicted')}![/{spec.get('style', 'fire')}]"
            )
        # Custom on_hit callback (DCSS-style complex brands)
        if "on_hit" in spec:
            brand_on_hit(brand, self, enemy, self.game)
        # Per-holiness damage bonus (DCSS Holy Wrath vs undead/demonic).
        # Applied as a multiplier on the rolled damage.
        brand_holiness_bonus = spec.get("dmg_pct_vs_holiness", {}).get(
            getattr(enemy, "holiness", "natural"), 0
        )
        if brand_holiness_bonus > 0 and enemy.health > 0:
            extra = max(1, int(enemy.health * 0 + (enemy.max_health * 0)))  # noqa
            # Apply as bonus damage (re-rolled on the spot). We re-roll once
            # against a fraction of the original rolled raw damage so the brand
            # damage feels like extra "smite" damage, not a fixed nuke.
            smite = max(1, int(random.randint(3, 7) * (1.0 + brand_holiness_bonus)))
            enemy.health -= smite
            self.game.message(
                f"[arcane]{style_text(weapon.name, 'weapons')} blazes with holy light "
                f"and smites the {style_text(enemy.name, 'enemy')} for {smite}![/arcane]",
                drop=smite,
            )
            if enemy.health <= 0:
                self.game.on_enemy_death(enemy)

    def apply_weapon_on_hit(self, weapon, enemy) -> None:
        """Apply a magical weapon's on-hit status effect (staves) to a surviving enemy."""
        on_hit = getattr(weapon, "on_hit", None)
        if not on_hit:
            return
        if random.randint(1, 100) > on_hit.get("chance", 100):
            return
        effect = on_hit["effect"]
        enemy.status.add(effect, on_hit.get("duration", 4), on_hit.get("potency", 1))
        verb = {"poison": "is poisoned", "burn": "catches fire", "slow": "is chilled to the bone",
                "confusion": "reels in confusion"}.get(effect, f"is afflicted with {effect}")
        enemy_name = style_text(enemy.name, "enemy")
        self.game.message(f"[{effect}]The {enemy_name} {verb}![/{effect}]")

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
        self.summon: list = []
        self.npcs: list = []
        self.visible: set[tuple[int, int]] = set()
        self.excluded_stairs: set[tuple[int, int]] = set()
        self.burning_cells: dict[tuple[int, int], int] = {}
        self.fog_cells: dict[tuple[int, int], int] = {}  # (y, x) -> turns remaining
        self.silence_aura: int = 0  # turns of silence left on the floor
        if self.altar:
            ay, ax = self.altar
            self.matrix[ay][ax].feature = "altar"
        for fy, fx, feat in getattr(layout, "scenery_features", []):
            self.matrix[fy][fx].feature = feat

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
        see_all = (
            self.game.player.has_see_invisible()
            or getattr(self.game, "godmode", False)
        )
        for y in range(max(0, py - r), min(self.max_y, py + r) + 1):
            for x in range(max(0, px - r), min(self.max_x, px + r) + 1):
                if (y - py) ** 2 + (x - px) ** 2 > r * r:
                    continue
                if not see_all and (y, x) in self.fog_cells:
                    continue
                if self._line_of_sight(py, px, y, x) or see_all:
                    self.visible.add((y, x))
                    self.matrix[y][x].explored = True

    def _line_of_sight(self, y0, x0, y1, x1) -> bool:
        for (y, x) in _bresenham(y0, x0, y1, x1)[1:-1]:
            if self.matrix[y][x].terrain in T.blocks_sight:
                return False
            if (y, x) in self.fog_cells:
                return False
        return True

    def tick_floor_effects(self) -> None:
        """Decrement fog tiles and silence aura each game-tick."""
        if self.fog_cells:
            for k in list(self.fog_cells.keys()):
                self.fog_cells[k] -= 1
                if self.fog_cells[k] <= 0:
                    del self.fog_cells[k]
        if self.silence_aura > 0:
            self.silence_aura -= 1

    def line_points(self, y0, x0, y1, x1) -> list[tuple[int, int]]:
        return _bresenham(y0, x0, y1, x1)

    def reveal_all(self) -> None:
        for row in self.matrix:
            for cell in row:
                cell.explored = True

    def visible_enemies(self) -> list:
        god = getattr(self.game, "godmode", False)
        return [
            e for e in self.enemies
            if not getattr(e, "is_summon", False)
            and getattr(e, "health", 0) > 0
            and (god or (e.y, e.x) in self.visible)
        ]

    def visible_summons(self) -> list:
        god = getattr(self.game, "godmode", False)
        return [s for s in self.summon if s.health > 0 and (god or (s.y, s.x) in self.visible)]

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
        """Window onto the map, centred on the player (or camera_override) and clamped to bounds.
        Returns (top, left, height, width)."""
        vw = max(1, min(view_w, self.width))
        vh = max(1, min(view_h, self.height))
        override = getattr(self.game, "camera_override", None)
        cy, cx = override if override is not None else self.game.player.location
        top = max(0, min(cy - vh // 2, self.height - vh))
        left = max(0, min(cx - vw // 2, self.width - vw))
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
        stair_cursor = getattr(self.game, "stair_cursor", None)
        examine_cursor = getattr(self.game, "examine_cursor", None)
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
                if stair_cursor is not None and (y, x) == stair_cursor:
                    style = styles.get("stair_cursor", styles["target"])
                if examine_cursor is not None and (y, x) == examine_cursor:
                    style = styles.get("examine_cursor", "bold reverse white")
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
            if top is not None:
                return top.symbol, config.symbols.tile_style.get(top.symbol, "item")
        if cell.trap and not cell.trap_hidden:
            return config.symbols.trap, "trap"
        if cell.feature:
            feat_sym = getattr(config.symbols, cell.feature, None)
            if feat_sym:
                return feat_sym, cell.feature
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
