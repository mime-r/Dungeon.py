from tinydb import TinyDB, Query


class get:
    def __init__(self):

        self.potions = TinyDB('potions.json')
        self.weapons = TinyDB('weapons.json')

    def get(self, typeOfThing, namething):
        chooser = Query()
        if typeOfThing == "potions":
            return self.potions.search(chooser.name == namething)[0]
