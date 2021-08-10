class StyleConfig:
    wall = "bold #666666"
    empty = "dim #444444"
    grid_num = "#444444"
    potions = "#ff6bf8"
    weapons = "#6bc6ff"
    controls = "#61B3FF"
    action = "#61D5FF"
    player = "#70D2FF"
    chemist = "#FFD900"
    target = "#0DFF00"
    unknown = "#0C0C0C"
    game_header = "bold red"
    move_count = "#FF63D6"
    health = "#00F521"
    xp_count = "#00C8FF"
    coin = "#FFDD00"
    inventory = "#00FFC8"
    time_count = "#B199FF"
    fail = "#FF0000"
    success = "#00FF00"
    enemy = "bold #FF2424"
    hp_drop = "bold red"
    menu_header = "bold green"

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