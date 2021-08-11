
class WeaponType:
    MELEE = "melee"
    RANGED = "ranged"

class DungeonWeaponTexts:
    def __init__(self, critical_hit, hit, missed_hit):
        self.critical_hit = critical_hit
        self.hit = hit
        self.missed_hit = missed_hit
