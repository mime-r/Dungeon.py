

class db:
    def __init__(self):
        from tinydb import TinyDB, Query
        self.potions = TinyDB('potions.json').all()

    def allOfIt(self, typeOfThing):
        if typeOfThing == "potions":
            return self.potions


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
