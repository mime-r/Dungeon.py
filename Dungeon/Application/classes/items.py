from enum import Enum

from .weapons import WeaponType, DungeonWeaponTexts


class ItemUseType(str, Enum):
    EQUIP = "equip"
    USE = "use"


class DungeonItem:
    """Base class for all dungeon items."""

    symbol = "("  # default ground glyph; subclasses override

    def __init__(self, name: str, description: str, cost: int, actions: list[ItemUseType]) -> None:
        self.name = name
        self.description = description
        self.cost = cost
        self.actions = actions


class DungeonWeapon(DungeonItem):
    """An equippable weapon with attack statistics."""

    symbol = ")"

    def __init__(
        self,
        name: str,
        description: str,
        cost: int,
        type: WeaponType,
        base_attack: int,
        attack_range: int,
        accuracy: int,
        texts: DungeonWeaponTexts,
        hands: str = "One",
        range: int = 1,
        on_hit: dict | None = None,
        brand: str | None = None,
        enchant: int = 0,
        delay: int | None = None,
        min_delay: int | None = None,
        weapon_type: str | None = None,
        magical_staff: bool = False,
        dmg_pct_vs_holiness: dict | None = None,
    ) -> None:
        super().__init__(name=name, description=description, cost=cost, actions=[ItemUseType.EQUIP])
        self.type = type
        self.base_attack = base_attack
        self.attack_range = attack_range
        self.accuracy = accuracy
        self.texts = texts
        self.hands = hands
        self.range = range
        self.ranged = (type == WeaponType.RANGED) or range > 1
        self.on_hit = on_hit or {}
        self.brand = brand  # "flaming" | "freezing" | "venom" | "electrocution" | "pain" | "holy_wrath" | "draining" | None
        self.enchant = enchant  # +N to base_attack, accumulated by Scroll of Enchant Weapon
        # Attack delay (DCSS "delay"). Higher = slower swing. Defaults by name/skill.
        from .skills import default_delay_for_weapon, default_min_delay
        self.delay = delay if delay is not None else default_delay_for_weapon(name)
        self.min_delay = min_delay if min_delay is not None else default_min_delay(self.delay)
        self.weapon_type = weapon_type  # human-readable subtype, e.g. "short_blade"
        self.magical_staff = magical_staff  # True for Staff of Flame/Frost/etc.
        # Damage bonus vs a specific enemy holiness tag (e.g., Sacred Scourge
        # vs undead = +50%). Keys: "undead" | "demonic" | "holy" | "natural".
        # Values are added to the base damage roll (e.g., 0.5 = +50%).
        self.dmg_pct_vs_holiness = dmg_pct_vs_holiness or {}


class DungeonThrowable(DungeonItem):
    """A stackable thrown weapon: consumed from the pack, fired without being equipped."""

    symbol = "/"

    def __init__(
        self,
        name: str,
        description: str,
        cost: int,
        base_attack: int,
        attack_range: list,
        accuracy: int,
        texts: DungeonWeaponTexts,
        range: int = 4,
        count: int = 1,
    ) -> None:
        super().__init__(name=name, description=description, cost=cost, actions=[])
        self.base_attack = base_attack
        self.attack_range = attack_range
        self.accuracy = accuracy
        self.texts = texts
        self.range = range
        self.ranged = True
        self.on_hit = {}
        self.count = count
        self.brand = None
        self.enchant = 0
        # Throwables throw instantly (cost = TURN).
        self.delay = 10
        self.min_delay = 10


class DungeonPotion(DungeonItem):
    """A consumable potion: heals HP and/or applies a status effect."""

    symbol = "!"

    def __init__(self, name: str, description: str, cost: int, hp_change: int = 0,
                 effect: str | None = None, duration: int = 0, potency: int = 0) -> None:
        super().__init__(name=name, description=description, cost=cost, actions=[ItemUseType.USE])
        self.hp_change = hp_change
        self.effect = effect
        self.duration = duration
        self.potency = potency


class DungeonScroll(DungeonItem):
    """A consumable scroll with a named effect resolved by the game."""

    symbol = "?"

    def __init__(self, name: str, description: str, cost: int, effect: str, weight: int = 1) -> None:
        super().__init__(name=name, description=description, cost=cost, actions=[ItemUseType.USE])
        self.effect = effect
        self.weight = max(1, weight)


class ArmourSlot(str, Enum):
    BODY = "body"
    SHIELD = "shield"
    HELMET = "helmet"
    CLOAK = "cloak"
    GLOVES = "gloves"
    BOOTS = "boots"


class DungeonArmour(DungeonItem):
    """An equippable piece of armour. Body armour and shields carry an encumbrance
    rating that penalizes evasion, stealth, and ranged attack speed; every other
    slot is free to wear."""

    symbol = "["

    def __init__(
        self,
        name: str,
        description: str,
        cost: int,
        slot: str,
        ac: int = 0,
        sh: int = 0,
        encumbrance: int = 0,
        enchant: int = 0,
    ) -> None:
        super().__init__(name=name, description=description, cost=cost, actions=[ItemUseType.EQUIP])
        self.slot = slot
        self.ac = ac
        self.sh = sh
        self.encumbrance = encumbrance
        self.enchant = enchant  # +N to ac, accumulated by Scroll of Enchant Armour
        # Ego system: spawned with one of the DCSS-tier armour egos (Stealth, rF+,
        # rC+, SInv, Will+, Parrying, Archery). Each ego grants one or more of:
        self.ego: str | None = None
        self.resistances: dict[str, int] = {}  # damage_type -> resistance level
        self.ev_bonus: int = 0                  # +EV (Stealth)
        self.sh_bonus: int = 0                  # +SH (Parrying)
        self.ranged_dmg_bonus: float = 0.0      # +% ranged damage (Archery)
        self.grant_see_invisible: bool = False  # helmet flag (SInv)


class DungeonSpell:
    """A spell the player can memorise and cast."""

    def __init__(
        self,
        name: str,
        schools: list[str],
        level: int,
        base_difficulty: int,
        mp_cost: int,
        range: int,
        effect: str,
        damage: list | None = None,
        damage_type: str = "",
        status: dict | None = None,
        description: str = "",
        cast_text: str = "",
        **kwargs,
    ) -> None:
        self.name = name
        self.schools = schools
        self.level = level
        self.base_difficulty = base_difficulty
        self.mp_cost = mp_cost
        self.range = range
        self.effect = effect
        self.damage = damage
        self.damage_type = damage_type
        self.status = status
        self.description = description
        self.cast_text = cast_text
        self.extra = kwargs


class DungeonSpellBook(DungeonItem):
    """A book that teaches one or more spells when read."""

    symbol = "?"

    def __init__(self, name: str, description: str, cost: int, spells: list[str]) -> None:
        super().__init__(name=name, description=description, cost=cost, actions=[ItemUseType.USE])
        self.spells = spells


class DungeonShard(DungeonItem):
    """One fragment of the Broken Sigil. Collect all three to unlock the exit."""

    symbol = "*"

    DEPTHS: dict[int, str] = {
        6: "Shard of Flame",
        7: "Shard of Stone",
        8: "Shard of Shadow",
    }

    def __init__(self, name: str) -> None:
        super().__init__(
            name=name,
            description="A fragment of the Broken Sigil, warm to the touch. Find the other pieces.",
            cost=0,
            actions=[],
        )
