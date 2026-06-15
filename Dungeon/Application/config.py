"""Central game configuration: colours, symbols, terrain, map size, depth and spawns."""


class StyleConfig:
    """Rich markup styles. Each attribute name is usable as ``[name]...[/name]``."""

    # --- terrain / map tiles ---
    wall: str = "bold #5a5a5a"
    floor: str = "#3a3a3a"
    unknown: str = "#0C0C0C"
    door: str = "#c08a3e"
    stairs: str = "bold #ffe066"
    player: str = "bold #70D2FF"
    target: str = "bold #0DFF00"

    # --- items on the floor ---
    potions: str = "#ff6bf8"
    scroll: str = "#e8e0c0"
    weapons: str = "#6bc6ff"
    bag: str = "#c9a06b"
    gold: str = "#FFD900"
    orb: str = "bold #fffb00"

    # --- npcs ---
    chemist: str = "bold #FFD900"
    blacksmith: str = "bold #ff9d5c"
    healer: str = "bold #7CFFCB"
    merchant: str = "bold #C9B3FF"

    # --- enemies (rendered by tier colour) ---
    enemy: str = "bold #FF2424"
    enemy_weak: str = "#9be36b"
    enemy_mid: str = "#ffb14e"
    enemy_strong: str = "#ff6b6b"
    enemy_boss: str = "bold #ff1e6e"

    # --- HUD / text ---
    grid_num: str = "#444444"
    move_count: str = "#FF63D6"
    health: str = "#00F521"
    hp_bar: str = "#00F521"
    hp_bar_low: str = "#FF3030"
    xp_count: str = "#00C8FF"
    coin: str = "#FFDD00"
    inventory: str = "#00FFC8"
    time_count: str = "#B199FF"
    depth: str = "bold #FF9E2C"
    fail: str = "bold #FF0000"
    success: str = "bold #00FF00"
    occupation: str = "bold green"
    name: str = "bold magenta"
    item: str = "#A4FF42"
    game_header: str = "bold #FF4444"
    hp_drop: str = "bold red"
    heal: str = "bold #7CFFCB"
    menu_header: str = "bold green"
    controls: str = "#61B3FF"
    action: str = "#61D5FF"
    flavor: str = "italic #b9a98c"
    warn: str = "bold #FFD166"


class TerrainConfig:
    """Logical terrain types stored on each cell."""

    FLOOR = "floor"
    WALL = "wall"
    DOOR_CLOSED = "door_closed"
    DOOR_OPEN = "door_open"
    SECRET_DOOR = "secret_door"
    STAIRS_DOWN = "stairs_down"
    STAIRS_UP = "stairs_up"

    walkable = {FLOOR, DOOR_OPEN, STAIRS_DOWN, STAIRS_UP}
    blocks_sight = {WALL, DOOR_CLOSED, SECRET_DOOR}


class SymbolConfig:
    """Single-character glyphs used to render the map."""

    empty: str = "."          # floor
    wall: str = "#"
    door_closed: str = "+"
    door_open: str = "'"
    stairs_down: str = ">"
    stairs_up: str = "<"
    unknown: str = " "        # unexplored / fog

    player: str = "@"
    gold: str = "$"
    potions: str = "!"
    scrolls: str = "?"
    weapons: str = ")"
    bag: str = "("
    orb: str = "0"

    # npcs
    chemist: str = "C"
    blacksmith: str = "B"
    healer: str = "H"
    merchant: str = "M"
    traders: list[str] = [chemist, blacksmith, merchant]
    npcs: list[str] = [chemist, blacksmith, healer, merchant]

    # enemies (symbol set is data-driven via enemies.json; this is the render hint set)
    enemies: list[str] = ["r", "b", "k", "g", "o", "z", "s", "O", "W", "T", "&"]

    # terrain -> glyph
    terrain_glyph: dict = {
        TerrainConfig.FLOOR: empty,
        TerrainConfig.WALL: wall,
        TerrainConfig.DOOR_CLOSED: door_closed,
        TerrainConfig.DOOR_OPEN: door_open,
        TerrainConfig.SECRET_DOOR: wall,        # disguised as wall until found
        TerrainConfig.STAIRS_DOWN: stairs_down,
        TerrainConfig.STAIRS_UP: stairs_up,
    }

    # glyph -> style name (for terrain & static features)
    tile_style: dict = {
        empty: "floor",
        wall: "wall",
        door_closed: "door",
        door_open: "door",
        stairs_down: "stairs",
        stairs_up: "stairs",
        player: "player",
        gold: "gold",
        potions: "potions",
        scrolls: "scroll",
        weapons: "weapons",
        bag: "bag",
        orb: "orb",
        chemist: "chemist",
        blacksmith: "blacksmith",
        healer: "healer",
        merchant: "merchant",
    }


class MapConfig:
    """Per-floor map dimension ranges. Actual dimensions vary per level."""

    min_width: int = 50
    max_width: int = 75
    min_height: int = 22
    max_height: int = 32
    min_distance: int = 18  # min Chebyshev distance between up/down stairs


class DepthConfig:
    """Multi-floor descent settings."""

    floors: int = 8                 # floor 1 = surface entrance, last floor holds the Orb
    sight_radius: int = 6           # how far the player sees (and wakes monsters)


class SpawnConfig:
    """How many of each thing to place per floor (scaled by depth where noted)."""

    enemies_base: int = 6           # +enemies_per_depth * (depth-1)
    enemies_per_depth: int = 2
    npcs_per_floor: int = 2         # traders / healers (none on the Orb floor)
    floor_potions: int = 3
    floor_scrolls: int = 2
    gold_piles: int = 5
    floor_weapons: int = 2


class PlayerConfig:
    """Player starting statistics."""

    max_inventory: int = 8
    health: int = 30
    max_health: int = 30
    coins: int = 30
    xp: int = 0


class Config:
    """Aggregates all config sub-objects into a single access point."""

    styles: dict = {k: v for k, v in StyleConfig.__dict__.items() if not k.startswith("__")
                    and isinstance(v, str)}
    symbols = SymbolConfig
    terrain = TerrainConfig
    map = MapConfig
    depth = DepthConfig
    spawn = SpawnConfig
    player = PlayerConfig


config = Config
