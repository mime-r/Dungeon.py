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
    ) -> None:
        super().__init__(name=name, description=description, cost=cost, actions=[ItemUseType.EQUIP])
        self.type = type
        self.base_attack = base_attack
        self.attack_range = attack_range
        self.accuracy = accuracy
        self.texts = texts


class DungeonInventory(DungeonItem):
    """An inventory bag that expands carrying capacity."""

    symbol = "("

    def __init__(self, name: str, description: str, cost: int, inventory: int) -> None:
        super().__init__(name=name, description=description, cost=cost, actions=[ItemUseType.EQUIP])
        self.inventory = inventory


class DungeonPotion(DungeonItem):
    """A consumable potion that changes player HP."""

    symbol = "!"

    def __init__(self, name: str, description: str, cost: int, hp_change: int) -> None:
        super().__init__(name=name, description=description, cost=cost, actions=[ItemUseType.USE])
        self.hp_change = hp_change


class DungeonScroll(DungeonItem):
    """A consumable scroll with a named effect resolved by the game."""

    symbol = "?"

    def __init__(self, name: str, description: str, cost: int, effect: str) -> None:
        super().__init__(name=name, description=description, cost=cost, actions=[ItemUseType.USE])
        self.effect = effect


class DungeonOrb(DungeonItem):
    """The Orb of Zot: the win objective. Cannot be sold or dropped casually."""

    symbol = "0"

    def __init__(self) -> None:
        super().__init__(
            name="Orb of Zot",
            description="A heavy sphere of crystallised power. Carry it to the surface to win.",
            cost=0,
            actions=[],
        )
