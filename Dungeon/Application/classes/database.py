from .items import *
from .people import *
from .decoder import DungeonJSONDecoder

class DungeonDatabase:
    def __init__(self, game):
        self.game = game
        self.decoder = DungeonJSONDecoder(game=self.game)

        self.item_db = DungeonItemDatabase(global_db=self)
        self.enemy_db = DungeonEnemyDatabase(global_db=self)
        self.people_db = DungeonPeopleDatabase(global_db=self)

class DungeonEnemyDatabase:
    def __init__(self, global_db):
        self.global_db = global_db
        self.enemies = self.global_db.decoder.fetch_enemies()

    def search_enemy(self, name=None, symbol=None):
        results = list(filter(
            lambda enemy_loader: enemy_loader.data.name == name if name else enemy_loader.data.symbol == symbol,
            self.enemies
        ))
        if len(results) == 0:
            return None
        return results[0]

class DungeonPeopleDatabase:
    def __init__(self, global_db):
        self.global_db = global_db
        self.people = self.global_db.decoder.fetch_people()

    def search_people(self, occupation, type=DungeonPeople):
        results = list(filter(
            lambda people_loader: (True if type == DungeonPeople else people_loader.type == type) and people_loader.data.occupation == occupation,
            self.people
        ))
        if len(results) == 0:
            return None
        return results[0]

    def search_trader(self, occupation):
        return self.search_people(occupation, type=DungeonTrader)


class DungeonItemDatabase:
    def __init__(self, global_db):
        self.global_db = global_db
        self.potions = self.global_db.decoder.fetch_potions()
        self.weapons = self.global_db.decoder.fetch_weapons()
        self.inventory = self.global_db.decoder.fetch_inventory()
        self.items = self.potions + self.weapons + self.inventory

    def search_item(self, name, type=DungeonItem):
        search_list = {
            DungeonItem: self.items,
            DungeonInventory: self.inventory,
            DungeonPotion: self.potions,
            DungeonWeapon: self.weapons
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
