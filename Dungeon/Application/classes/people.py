from random import randint
from .database import DungeonItemDatabase


class People:
    def __init__(self, occupation):
        self.name = People.generate_name()
        self.occupation = occupation

    @staticmethod
    def generate_name():
        try:
            import names
            if randint(1, 2) == 1:
                gender = "male"
            else:
                gender = "female"
            return str(names.get_full_name(gender))
        except:
            return "John Doe"

class Trader(People):
    def __init__(self, potential_sales, occupation="trader"):
        super().__init__(occupation=occupation)
        self.stuff = []
        for sale in potential_sales:
            if randint(1, 100) < sale.chance:
                self.stuff.append(sale.item)

class Chemist(Trader):
    def __init__(self):
        super().__init__(
            potential_sales=[
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
            ],
            occupation="Chemist"
        )

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
