import random
import collections
f = lambda s, e: s.replace("{}", f"[enemy]{e}[/enemy]")

class DungeonEnemy:
    def __init__(self, name, health, coin_drop, texts, xp_drop, attack_base, attack_range, accuracy, game):
        self.name = name
        self.xp_drop = xp_drop
        self.attack_base = attack_base
        self.attack_range = attack_range
        self.accuracy = accuracy
        self.health = health
        self.coin_drop = coin_drop
        self.texts = texts
        self.game = game

    def attack_turn(self):
        if random.randint(1, 100) < self.accuracy:
            attack_damage = self.attack_base + \
                random.randint(self.attack_range[0], self.attack_range[1])
            if attack_damage == self.attack_base + self.attack_range[1]:
                # Max Damage
                self.game.print(self.texts.critical_hit)
            else:
                self.game.print(self.texts.hit)
            #self.print(f"\n[player]Your[/player] health [hp_drop]-{attack_damage}[/hp_drop]\n", highlight=False)
            return (self.game.player.health - attack_damage), attack_damage
        else:
            self.game.print(self.texts.missed_hit)
            return self.game.player.health, 0

class DungeonEnemyLoader:
    def __init__(self, game, data):
        self.game = game
        self.enemy_data = data

    def load(self):
        enemy_data = self.enemy_data
        min_hp, max_hp = enemy_data.health_range
        min_coin, max_coin = enemy_data.coin_drop_range
        health = random.randint(min_hp, max_hp)
        coin_drop = random.randint(min_coin, max_coin)

        if hasattr(enemy_data, 'sub_enemies'):
            for sub_enemy in enemy_data.sub_enemies:
                min_hp, max_hp = sub_enemy['health_range']
                if health not in range(min_hp, max_hp+1):
                    continue

                enemy_data = collections.namedtuple(
                    "EnemyData",
                    [
                        'name',
                        'xp_drop',
                        'attack_base',
                        'attack_range',
                        'accuracy',
                        'texts'
                    ]
                )(
                    name=sub_enemy['name'],
                    xp_drop=sub_enemy['xp_drop'],
                    attack_base=sub_enemy['attack_base'],
                    attack_range=sub_enemy['attack_range'],
                    accuracy=sub_enemy['accuracy'],
                    texts=enemy_data.texts
                )
                break

        enemy_data = enemy_data._replace(
            texts=EnemyTexts(
                *enemy_data.texts.values(),
                enemy_data.name
            )
        )

        return DungeonEnemy(
            name=enemy_data.name,
            xp_drop=enemy_data.xp_drop,
            coin_drop=coin_drop,
            health=health,
            attack_base=enemy_data.attack_base,
            attack_range=enemy_data.attack_range,
            accuracy=enemy_data.accuracy,
            texts=enemy_data.texts,
            game=self.game
        )

class EnemyTexts:
    def __init__(self, critical_hit, hit, missed_hit, death, enemy_name):
        e = enemy_name
        self.critical_hit = f(critical_hit, e)
        self.hit = f(hit, e)
        self.missed_hit = f(missed_hit, e)
        self.death = f(death, e)