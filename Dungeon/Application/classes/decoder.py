import json
import types
from pathlib import Path

from .items import DungeonItem, DungeonWeapon, DungeonPotion, DungeonInventory, DungeonScroll
from .weapons import DungeonWeaponTexts
from .enemies import DungeonEnemyLoader
from .people import DungeonPeopleLoader

DATA_DIR = Path(__file__).parent.parent.parent / "data"


class DungeonJSONDecoder:
    """Loads and parses JSON data files into game objects."""

    def __init__(self, game) -> None:
        self.game = game

    def _load(self, file: Path) -> list[dict]:
        with open(file, "r") as f:
            return json.load(f)

    def _fetch_loaders(self, data_file: Path, loader_class) -> list:
        decoded = []
        for data in self._load(data_file):
            decoded.append(loader_class(game=self.game, data=types.SimpleNamespace(**data)))
        return decoded

    def fetch_enemies(self) -> list:
        return self._fetch_loaders(DATA_DIR / "enemies.json", DungeonEnemyLoader)

    def fetch_people(self) -> list:
        return self._fetch_loaders(DATA_DIR / "people.json", DungeonPeopleLoader)

    def fetch_potions(self) -> list[DungeonPotion]:
        return [DungeonPotion(**data) for data in self._load(DATA_DIR / "potions.json")]

    def fetch_weapons(self) -> list[DungeonWeapon]:
        decoded = []
        for data in self._load(DATA_DIR / "weapons.json"):
            data["texts"] = DungeonWeaponTexts(*data["texts"].values())
            decoded.append(DungeonWeapon(**data))  # keyword construction tolerates optional fields
        return decoded

    def fetch_inventory(self) -> list[DungeonInventory]:
        return [DungeonInventory(*data.values()) for data in self._load(DATA_DIR / "inventory.json")]

    def fetch_scrolls(self) -> list[DungeonScroll]:
        return [DungeonScroll(*data.values()) for data in self._load(DATA_DIR / "scrolls.json")]

    def fetch_backgrounds(self) -> list[dict]:
        return self._load(DATA_DIR / "backgrounds.json")
