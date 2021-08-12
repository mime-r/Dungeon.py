class StyleConfig:
    # map features
    wall = "bold #666666"
    empty = "#444444"
    unknown = "#0C0C0C"
    grid_num = "#444444"

    target = "#0DFF00"

    potions = "#ff6bf8"
    weapons = "#6bc6ff"

    player = "#70D2FF"
    
    chemist = "#FFD900"

    # game vars
    move_count = "#FF63D6"
    health = "#00F521"
    xp_count = "#00C8FF"
    coin = "#FFDD00"
    inventory = "#00FFC8"
    time_count = "#B199FF"

    # text colours
    fail = "#FF0000"
    success = "#00FF00"
    enemy = "bold #FF2424"
    occupation = "bold green"
    name = "bold magenta"
    item = "#A4FF42"

    # ui elements
    game_header = "bold red"
    hp_drop = "bold red"
    menu_header = "bold green"
    controls = "#61B3FF"
    action = "#61D5FF"

class SymbolConfig:
    
    # Map Features Symbols
    empty = "."
    wall = "#"
    target = "$"
    unknown = '⠀'
    potions = "!"
    weapons = "\\"

    # Player Symbol
    player = "@"

    # NPC Symbols
    chemist = "C"

    # Enemy Symbols
    orc = "o"   

    enemies = [
        orc
    ]

    traders = [
        chemist
    ]

class DungeonCountConfig:
    orc = 20
    chemist = 5
    floor_potions = 6

class MapConfig:
    width = 25
    height = 25
    min_distance = 13

    max_x = width-1
    max_y = height-1

class PlayerConfig:
    max_inventory = 3
    health = 30
    max_health = 30
    coins = 100
    xp = 0

class Config:

    # set up styles config
    styles = dict(StyleConfig.__dict__)
    for key in StyleConfig.__dict__.keys():
        if '__' in key: styles.pop(key)

    symbols = SymbolConfig
    count = DungeonCountConfig
    map = MapConfig
    player = PlayerConfig

config = Config