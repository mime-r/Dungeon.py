import copy
import json
import random
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent.parent / "data"

_NAME_POOL: dict | None = None


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
        self.stuff = [sale.item for sale in potential_sales if random.randint(1, 100) <= sale.chance]


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
        """Resolve a sale by name; throwables get a fresh copy so their stack count
        doesn't mutate the shared database singleton or other traders' stock."""
        from .items import DungeonThrowable
        item = self.game.db.item_db.search_item(name=name)
        return copy.copy(item) if isinstance(item, DungeonThrowable) else item

    def load(self):
        people_data = self.data
        if self.type == DungeonTrader:
            potential_sales = (
                TraderSales(
                    item=self._stock_item(sale_dict["item"]),
                    chance=sale_dict["chance"],
                )
                for sale_dict in people_data.potential_sales
            )
            return DungeonTrader(
                potential_sales=potential_sales,
                occupation=people_data.occupation,
                personality=getattr(people_data, "personality", ""),
            )
        if self.type == DungeonHealer:
            return DungeonHealer(
                heal_cost_per_hp=getattr(people_data, "heal_cost_per_hp", 1),
                occupation=people_data.occupation,
                personality=getattr(people_data, "personality", ""),
            )


class TraderSales:
    """Pairs an item with its stock probability (0-100)."""

    def __init__(self, item, chance: int) -> None:
        self.item = item
        self.chance = chance
