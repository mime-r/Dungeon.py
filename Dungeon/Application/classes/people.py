import copy
import json
import random
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent.parent / "data"

_NAME_POOL: dict | None = None

# Brand tier multiplier for price calculation (applied to base cost).
_BRAND_PRICE_MULT: dict[int, float] = {
    1: 0.3,   # venom, protection
    2: 0.5,   # flaming, freezing, electrocution
    3: 0.8,   # vampiric, spectral, heavy, pain, holy_wrath, draining, distortion
    4: 1.2,   # speed, antimagic, chaos
}
_ARMOUR_EGO_PRICE: dict[str, float] = {
    "stealth": 0.3,
    "res_fire": 0.5,
    "res_cold": 0.5,
    "will": 0.8,
    "see_invisible": 0.8,
    "archery": 0.8,
    "parrying": 1.0,
}


def _name_pool() -> dict:
    global _NAME_POOL
    if _NAME_POOL is None:
        try:
            with open(DATA_DIR / "names.json", "r", encoding="utf-8") as f:
                _NAME_POOL = json.load(f)
        except Exception:
            _NAME_POOL = {"first": ["Adventurer"], "surname": ["Nameless"], "epithet": []}
    return _NAME_POOL


class DungeonPeople:
    """Base NPC class with a randomly generated name."""

    def __init__(self, occupation: str, personality: str = "") -> None:
        self.name = DungeonPeople.generate_name()
        self.occupation = occupation
        self.personality = personality
        self.symbol: str = "?"
        self.style: str = "occupation"

    @staticmethod
    def generate_name() -> str:
        """Build a varied fantasy name from curated lists (no external dependency)."""
        pool = _name_pool()
        first = random.choice(pool["first"])
        if pool.get("epithet") and random.randint(1, 4) == 1:
            return f"{first} {random.choice(pool['epithet'])}"
        return f"{first} {random.choice(pool['surname'])}"


class DungeonTrader(DungeonPeople):
    """A trader NPC with a randomized inventory of items for sale."""

    def __init__(self, potential_sales, occupation: str = "trader", personality: str = "") -> None:
        super().__init__(occupation=occupation, personality=personality)
        # Filter None items (defensive: handles missing-from-DB cases) and roll
        # each sale's chance independently.
        self.stuff = [
            sale.item for sale in potential_sales
            if sale.item is not None and random.randint(1, 100) <= sale.chance
        ]


class DungeonHealer(DungeonPeople):
    """A healer NPC who restores HP in exchange for coins."""

    def __init__(self, heal_cost_per_hp: int = 1, occupation: str = "Healer", personality: str = "") -> None:
        super().__init__(occupation=occupation, personality=personality)
        self.heal_cost_per_hp = heal_cost_per_hp


class DungeonPeopleLoader:
    """Builds a DungeonPeople instance from JSON data."""

    def __init__(self, game, data) -> None:
        self.game = game
        self.data = data
        self.type = {"TRADER": DungeonTrader, "HEALER": DungeonHealer}.get(self.data.type)

    def _stock_item(self, name: str):
        """Resolve a sale by name; throwables, weapons, and armour get a fresh copy
        so mutations don't share the database singleton.
        Returns None if the item is missing from the DB - callers must filter."""
        from .items import DungeonThrowable, DungeonWeapon, DungeonArmour
        item = self.game.db.item_db.search_item(name=name)
        if item is None:
            return None
        if isinstance(item, (DungeonThrowable, DungeonWeapon, DungeonArmour)):
            return copy.copy(item)
        return item

    def load(self):
        people_data = self.data
        if self.type == DungeonTrader:
            potential_sales = (
                TraderSales(
                    item=stocked,
                    chance=sale_dict["chance"],
                )
                for sale_dict in people_data.potential_sales
                if (stocked := self._stock_item(sale_dict["item"])) is not None
            )
            trader = DungeonTrader(
                potential_sales=potential_sales,
                occupation=people_data.occupation,
                personality=getattr(people_data, "personality", ""),
            )
            # Apply brands/enchants to weapons and armour in the trader's stock,
            # scaling with floor depth.
            self._enchant_stock(trader.stuff, getattr(self.game, "depth", 1))
            return trader
        if self.type == DungeonHealer:
            return DungeonHealer(
                heal_cost_per_hp=getattr(people_data, "heal_cost_per_hp", 1),
                occupation=people_data.occupation,
                personality=getattr(people_data, "personality", ""),
            )


    @staticmethod
    def _enchant_stock(stuff: list, depth: int) -> None:
        """Apply depth-scaled brands/enchants to weapons and armour in a trader's
        inventory. Also updates the item's cost to reflect enchant value."""
        from .items import DungeonWeapon, DungeonArmour
        from .item_egos import maybe_brand_weapon, maybe_ego_armour, BRAND_TIER, ARMOUR_EGO_TIER

        for item in stuff:
            if isinstance(item, DungeonWeapon) and not getattr(item, "brand", None):
                maybe_brand_weapon(item, depth, vault_bonus=1)
                enchant = getattr(item, "enchant", 0)
                brand = getattr(item, "brand", None)
                mult = 1.0 + enchant * 0.5
                if brand:
                    tier = BRAND_TIER.get(brand, 1)
                    mult += _BRAND_PRICE_MULT.get(tier, 0.3)
                item.cost = max(1, int(item.cost * mult))
            elif isinstance(item, DungeonArmour) and not getattr(item, "ego", None):
                maybe_ego_armour(item, depth, vault_bonus=1)
                enchant = getattr(item, "enchant", 0)
                ego = getattr(item, "ego", None)
                mult = 1.0 + enchant * 0.5
                if ego:
                    mult += _ARMOUR_EGO_PRICE.get(ego, 0.3)
                item.cost = max(1, int(item.cost * mult))


class TraderSales:
    """Pairs an item with its stock probability (0-100)."""

    def __init__(self, item, chance: int) -> None:
        self.item = item
        self.chance = chance
