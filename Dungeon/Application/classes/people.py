from random import randint


class DungeonPeople:
    def __init__(self, occupation):
        self.name = DungeonPeople.generate_name()
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

class DungeonTrader(DungeonPeople):
    def __init__(self, potential_sales, occupation="trader"):
        super().__init__(occupation=occupation)
        self.stuff = []
        for sale in potential_sales:
            if randint(1, 100) < sale.chance:
                self.stuff.append(sale.item)

class DungeonPeopleLoader:
    def __init__(self, game, data):
        self.game = game
        self.people_data = data
        self.people_type = {
            "TRADER": DungeonTrader
        }.get(self.people_data.type)

    def load(self):
        people_data = self.people_data
        if self.people_type == DungeonTrader:
            potential_sales = map(
                lambda sale_dict: TraderSales(
                    item=self.game.db.item_db.search_item(name=sale_dict["item"]),
                    chance=sale_dict["chance"],
                ),
                people_data.potential_sales
            )
            return DungeonTrader(
                potential_sales=potential_sales,
                occupation=people_data.occupation
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
