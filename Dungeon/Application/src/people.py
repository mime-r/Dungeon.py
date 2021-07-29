from database import db
from random import randint


class people:
    def __init__(self):
        self.potions = db().allOfIt("potions")

    class chemist:
        def __init__(self):
            p = people()
            self.type = "chemist"
            self.name = people().generate_name()
            self.stuff = []
            for potion in p.potions:
                if randint(1, 100) <= potion["probability"]:
                    self.stuff.append(potion)

    def generate_name(self):
        from random import randint as r
        import names
        if r(1, 2) == 1:
            gender = "male"
        else:
            gender = "female"
        return str(names.get_full_name(gender))


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
