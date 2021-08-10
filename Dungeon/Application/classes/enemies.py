import random
f = lambda s, e: s.replace("{}", f"[enemy]{e}[/enemy]")
class DungeonEnemy:
    def __init__(self, name, xp_drop, attack_base, attack_range, accuracy):
        self.name = name
        self.xp_drop = xp_drop
        self.attack_base = attack_base
        self.attack_range = attack_range
        self.accuracy = accuracy
        self.health = None
        self.coin_drop = None
        self.texts = None


class Orc(DungeonEnemy):
    def __init__(self):
        health = 3 + random.randint(1, 7)
        if health < 5:
            super().__init__(
                name="Weak Orc",
                xp_drop=1,
                attack_base=1,
                attack_range=(0, 1),
                accuracy=80
            )
        elif health < 9:
            super().__init__(
                name="Orc",
                xp_drop=2,
                attack_base=1,
                attack_range=(0, 1),
                accuracy=60
            )
        else:
            super().__init__(
                name="Chief Orc",
                xp_drop=3,
                attack_base=1,
                attack_range=(0, 2),
                accuracy=50
            )
        # hitcritical, hitmedium, miss, uponded
        self.health = health
        self.texts = EnemyTexts(
            critical_hit="The {} lashes out at you, hitting you squarely in the stomach. You double up in pain.",
            hit="The {} aims, at you, delivering a fierce punch.",
            missed_hit="The {} misses you by inches.",
            death="The {} falls to the ground with a grunt. The corpse disappears upon touching the ground.",
            enemy_name=self.name
        )
        self.coin_drop = random.randint(0, 2)

class EnemyTexts:
    def __init__(self, critical_hit, hit, missed_hit, death, enemy_name):
        e = enemy_name
        self.critical_hit = f(critical_hit, e)
        self.hit = f(hit, e)
        self.missed_hit = f(missed_hit, e)
        self.death = f(death, e)