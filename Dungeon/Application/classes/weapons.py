from tinydb import TinyDB, Query
class weapons:
    
    def __init__(self):
        
        self.weapons = TinyDB('weapons.json')
    
    def give(self, type_):
        chooser = Query()
        if type_ == "default":
            return self.weapons.search(chooser.name == "fists")[0]