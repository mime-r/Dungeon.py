class StyleConfig:
    wall = "bold #666666"
    grid_num = "#444444"
    controls = "#61B3FF"
    action = "#61D5FF"
    player = "#FFB300"
    chemist = "#FFD900"
    target = "#0DFF00"
    unknown = "#000000"
    game_header = "bold red"
    move_count = "bold green"
    health_count = "bold cyan"
    xp_count = "bold magenta"
    coin_count = "bold yellow"
    inventory_count = "bold green"
    time_count = "bold green"
    fail = "#FF0000"
    success = "#00FF00"

class SymbolConfig:
    
    # Map Features Symbols
    empty = "."
    wall = "#"
    target = "$"

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

class MapConfig:
    width = 25
    height = 25

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