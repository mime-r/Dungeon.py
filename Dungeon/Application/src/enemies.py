import random


class orc:
    def __init__(self):
        self.health = 3 + random.randint(1, 7)
        if self.health < 5:
            self.name = "Weak Orc"
            self.xp_gained = 1
            self.attack = 2
            self.percentage = 20
            self.attack_base = 1
            self.attack_range = [0, 1]
        elif self.health < 9:
            self.name = "Orc"
            self.xp_gained = 2
            self.percentage = 40
            self.attack_base = 1
            self.attack_range = [0, 1]
        else:
            self.name = "Chief Orc"
            self.xp_gained = 3
            self.percentage = 50
            self.attack_base = 1
            self.attack_range = [0, 2]
        # hitcritical, hitmedium, miss, uponded
        e = f"[enemy]{self.name}[/enemy]"
        self.texts = EnemyTexts(
            critical_hit=f"The {e} lashes out at you, hitting you squarely in the stomach. You double up in pain.",
            hit=f"The {e} aims, at you, delivering a fierce punch.",
            missed_hit=f"The {e} misses you by inches.",
            death=f"The {e} falls to the ground with a grunt. The corpse disappears upon touching the ground."
        )
        self.coins = random.randint(0, 2)

class EnemyTexts:
    def __init__(self, critical_hit, hit, missed_hit, death):
        self.critical_hit = critical_hit
        self.hit = hit
        self.missed_hit = missed_hit
        self.death = death