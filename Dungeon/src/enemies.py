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
        self.texts = ["The {} lashes out at you, hitting you squarely in the stomach. You double up in pain.", "The {} aims, at you, delivering a fierce punch.", "The {} misses you by inches.", "The {} falls to the ground with a grunt. The corpse disappears upon touching the ground."]
        self.coins = random.randint(0, 2)
