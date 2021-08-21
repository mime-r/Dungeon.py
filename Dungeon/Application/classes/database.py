from .items import *
from .decoder import DungeonJSONDecoder

class DungeonDatabase:
    def __init__(self, game):
        self.game = game
        self.decoder = DungeonJSONDecoder(
            game=self.game
        )

        self.item_db = DungeonItemDatabase
        self.enemy_db = DungeonEnemyDatabase(
            global_db=self,
            game=self.game
        )

class DungeonEnemyDatabase:
    def __init__(self, global_db, game):
        self.global_db = global_db
        self.enemies = self.global_db.decoder.fetch_enemies()

    def search_enemy(self, name):
        results = list(filter(
            lambda enemy_loader: enemy_loader.enemy_data.name == name,
            self.enemies
        ))
        if len(results) == 0:
            return None
        return results[0]


class DungeonItemDatabase:
    potions = [
        DungeonPotion(
            name="Weak Healing Potion",
            description="This berry-flavoured weak healing potion increases your health by 7",
            cost=2,
            hp_change=7
        ),
        DungeonPotion(
            name="Medium Healing Potion",
            description="This concentrated berry-flavoured medium healing potion increases your health by 15",
            cost=6,
            hp_change=15
        ),
        DungeonPotion(
            name="Strong Healing Potion",
            description="This super-concentrated berry-flavoured strong healing potion increases your health by 25",
            cost=12,
            hp_change=25
        )
    ]
    weapons = [
        DungeonWeapon(
            name="Fists",
            description="Your trusty pair of fists",
            cost=0,
            type=WeaponType.MELEE,
            base_attack=2,
            attack_range=(0, 1),
            accuracy=50,
            texts=DungeonWeaponTexts(
                critical_hit="You deliver a smashing blow with your {}.",
                hit="You hit the {0} with your {1}.",
                missed_hit="You flail your arms, failing to even touch the {}."
            )
        ),
        DungeonWeapon(
            name="Dagger",
            description="A sharp lightweight dagger",
            cost=4,
            type=WeaponType.MELEE,
            base_attack=1,
            attack_range=(0, 4),
            accuracy=50,
            texts=DungeonWeaponTexts(
                critical_hit="You stab viciously with your {}.",
                hit="You hit the {0} with your {1}.",
                missed_hit="You flail your dagger, failing to even touch the {}."
            )
        )
    ]
    inventory = [
        DungeonInventory(
            name="Cloth Bag",
            description="This useful cloth bag increases your inventory storage by 4",
            cost=5,
            inventory=4
        )
    ]
    items = potions + inventory + weapons

    @classmethod
    def search_item(cls, name, type=DungeonItem):
        search_list = {
            DungeonItem: cls.items,
            DungeonInventory: cls.inventory,
            DungeonPotion: cls.potions,
            DungeonWeapon: cls.weapons
        }.get(type)
        results = list(filter(
            lambda item: item.name == name,
            search_list
        ))
        if len(results) == 0:
            return None
        return results[0]

""""""

"""
self.bag = {
            "name": "cloth bag",
            "description": "This useful cloth bag increases your inventory storage by 4.",
            "cost": 5,
            "increaseInventory": 4,
            "use" : ["equip"],
            "type": "bag",
            "id": 1
        }
        self.weak_healing_potion = {
            "name": "weak healing potion",
            "description": "This berry-flavoured weak healing potion increases your health by 7.",
            "cost": 2,
            "type": "health-potion",
            "use": ["use"],
            "increase-health-by": 7,
            "id": 2
        }
        {
            "name": "medium healing potion",
            "description": "This concentrated berry-flavoured medium healing potion increases your health by 15.",
            "cost": 6,
            "type": "health-potion",
            "use": ["use"],
            "increase-health-by": 15,
            "id": 3
        }
        {
            "name": "strong healing potion",
            "description": "This super-concentrated berry-flavoured strong healing potion increases your health by 25.",
            "cost": 12,
            "type": "health-potion",
            "use": ["use"],
            "increase-health-by": 25,
            "id": 4
        }
"""
