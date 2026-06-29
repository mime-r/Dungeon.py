import random

from .items import (
    DungeonItem, DungeonWeapon, DungeonPotion, DungeonScroll,
    DungeonThrowable, DungeonArmour, DungeonSpell, DungeonSpellBook,
)
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
        self.backgrounds = self.decoder.fetch_backgrounds()
        self.skills_data = self.decoder.fetch_skill_defs()


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

    def all_for_depth(self, depth: int) -> list:
        """Return all spawnable enemy loaders valid for a given depth (unweighted)."""
        result = []
        for e in self.enemies:
            if getattr(e.data, "spawn_weight", 0) <= 0:
                continue
            lo, hi = getattr(e.data, "depth", [1, 99])
            if lo <= depth <= hi:
                result.append(e)
        return result

    def random_biased(self, depth: int, preferred_names: list[str]):
        """Like random_for_depth but biases towards preferred_names when possible."""
        candidates = [e for e in self.all_for_depth(depth) if e.data.name in preferred_names]
        if not candidates:
            return self.random_for_depth(depth)
        return random.choice(candidates)


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
        self.throwables: list[DungeonThrowable] = self.global_db.decoder.fetch_throwables()
        self.scrolls: list[DungeonScroll] = self.global_db.decoder.fetch_scrolls()
        self.armour: list[DungeonArmour] = self.global_db.decoder.fetch_armour()
        self.spells: list[DungeonSpell] = self.global_db.decoder.fetch_spells()
        self.spellbooks: list[DungeonSpellBook] = self.global_db.decoder.fetch_spellbooks()
        self.items: list[DungeonItem] = (
            self.potions + self.weapons + self.throwables
            + self.scrolls + self.armour + self.spellbooks
        )

    def search_item(self, name: str, type=DungeonItem):
        search_list = {
            DungeonItem: self.items,
            DungeonPotion: self.potions,
            DungeonWeapon: self.weapons,
            DungeonThrowable: self.throwables,
            DungeonScroll: self.scrolls,
            DungeonArmour: self.armour,
            DungeonSpellBook: self.spellbooks,
        }.get(type, self.items)
        results = [item for item in search_list if item.name == name]
        return results[0] if results else None

    def search_spell(self, name: str) -> DungeonSpell | None:
        results = [s for s in self.spells if s.name == name]
        return results[0] if results else None
