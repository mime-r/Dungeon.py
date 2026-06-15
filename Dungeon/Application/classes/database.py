import random

from .items import DungeonItem, DungeonWeapon, DungeonPotion, DungeonInventory, DungeonScroll
from .people import DungeonPeople, DungeonTrader, DungeonHealer
from .decoder import DungeonJSONDecoder


class DungeonDatabase:
    """Root database that aggregates item, enemy, and people sub-databases."""

    def __init__(self, game) -> None:
        self.game = game
        self.decoder = DungeonJSONDecoder(game=self.game)
        self.item_db = DungeonItemDatabase(global_db=self)
        self.enemy_db = DungeonEnemyDatabase(global_db=self)
        self.people_db = DungeonPeopleDatabase(global_db=self)


class DungeonEnemyDatabase:
    """Stores and searches enemy loader instances."""

    def __init__(self, global_db: DungeonDatabase) -> None:
        self.global_db = global_db
        self.enemies = self.global_db.decoder.fetch_enemies()

    def search_enemy(self, name: str | None = None, symbol: str | None = None):
        results = [
            e for e in self.enemies
            if (e.data.name == name if name else e.data.symbol == symbol)
        ]
        return results[0] if results else None

    def random_for_depth(self, depth: int):
        """Pick a spawnable enemy loader appropriate for the given floor (weighted)."""
        candidates = []
        weights = []
        for e in self.enemies:
            weight = getattr(e.data, "spawn_weight", 0)
            lo, hi = getattr(e.data, "depth", [1, 99])
            if weight > 0 and lo <= depth <= hi:
                candidates.append(e)
                weights.append(weight)
        if not candidates:
            return None
        return random.choices(candidates, weights=weights, k=1)[0]


class DungeonPeopleDatabase:
    """Stores and searches NPC loader instances."""

    def __init__(self, global_db: DungeonDatabase) -> None:
        self.global_db = global_db
        self.people = self.global_db.decoder.fetch_people()

    def search_people(self, occupation: str | None = None, type=DungeonPeople):
        results = [
            p for p in self.people
            if (type == DungeonPeople or p.type == type)
            and (occupation is None or p.data.occupation == occupation)
        ]
        return results

    def search_trader(self, occupation: str):
        results = [p for p in self.search_people(occupation, type=DungeonTrader)]
        return results[0] if results else None

    def traders(self) -> list:
        """All loaders that sell or provide a service (traders + healers)."""
        return [p for p in self.people if p.type in (DungeonTrader, DungeonHealer)]


class DungeonItemDatabase:
    """Stores and searches all item instances."""

    def __init__(self, global_db: DungeonDatabase) -> None:
        self.global_db = global_db
        self.potions: list[DungeonPotion] = self.global_db.decoder.fetch_potions()
        self.weapons: list[DungeonWeapon] = self.global_db.decoder.fetch_weapons()
        self.inventory: list[DungeonInventory] = self.global_db.decoder.fetch_inventory()
        self.scrolls: list[DungeonScroll] = self.global_db.decoder.fetch_scrolls()
        self.items: list[DungeonItem] = self.potions + self.weapons + self.inventory + self.scrolls

    def search_item(self, name: str, type=DungeonItem):
        search_list = {
            DungeonItem: self.items,
            DungeonInventory: self.inventory,
            DungeonPotion: self.potions,
            DungeonWeapon: self.weapons,
            DungeonScroll: self.scrolls,
        }.get(type, self.items)
        results = [item for item in search_list if item.name == name]
        return results[0] if results else None
