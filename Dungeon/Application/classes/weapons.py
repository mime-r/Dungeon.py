from enum import Enum


class WeaponType(str, Enum):
    MELEE = "melee"
    RANGED = "ranged"


class DungeonWeaponTexts:
    """Combat text templates for a weapon."""

    def __init__(self, critical_hit: str, hit: str, missed_hit: str) -> None:
        self.critical_hit = critical_hit
        self.hit = hit
        self.missed_hit = missed_hit
