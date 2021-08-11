from database import db
from random import randint
from .items import DungeonItemDatabase


class people:
    def __init__(self):
        self.potions = db().allOfIt("potions")

    class chemist:
        def __init__(self):
            p = people()
            self.type = "chemist"
            self.name = people().generate_name()
            self.stuff = []
            self.potential_sales = [
                TraderSales(
                    item=DungeonItemDatabase.search_item(name="Weak Healing Potion"),
                    chance=100
                ),
                TraderSales(
                    item=DungeonItemDatabase.search_item(name="Medium Healing Potion"),
                    chance=100
                ),
                TraderSales(
                    item=DungeonItemDatabase.search_item(name="Strong Healing Potion"),
                    chance=50
                ),
                TraderSales(
                    item=DungeonItemDatabase.search_item(name="Cloth Bag"),
                    chance=50
                )
            ]
            for sell in self.potential_sales:
                if randint(1, 100) < sell.chance:
                    self.stuff.append(sell.item)

    def generate_name(self):
        try:
            import names
            if randint(1, 2) == 1:
                gender = "male"
            else:
                gender = "female"
            return str(names.get_full_name(gender))
        except:
            return "John Doe"

class TraderSales:
    def __init__(self, item, chance):
        self.item = item
        self.chance = chance

class things:
    def __init__(self):
        self.stones = {}

        """ Idea?
        self.redbull_drink = {
            "name": "redbull",
            "description": "This sugar-loaded drink increases your attack by 50\% for the next 15 turns.",
            "cost": 10,
            "type": "health-potion",
            "use": ["use"],
            "increase-health-by": 25
        }
        """
