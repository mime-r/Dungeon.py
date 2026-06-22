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
    armour: str = "#8fb9a8"
    throwables: str = "#d6b25c"
    bag: str = "#c9a06b"
    gold: str = "#FFD900"
    orb: str = "bold #fffb00"
    shard: str = "bold #ff9e2c"

    # --- npcs ---
    chemist: str = "bold #FFD900"
    blacksmith: str = "bold #ff9d5c"
    healer: str = "bold #7CFFCB"
    merchant: str = "bold #C9B3FF"
    fletcher: str = "bold #8CD68C"

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
    level: str = "bold #FFC74D"

    # --- status effects ---
    poison: str = "#7CFF6B"
    burn: str = "#FF7043"
    regen: str = "#6BFFB0"
    might: str = "#FF9D5C"
    haste: str = "#6BE0FF"
    slow: str = "#9aa0b0"
    confusion: str = "#C77DFF"
    petrify: str = "#9E9E9E"

    # --- terrain scenery ---
    shallow_water: str = "#4fc3f7"
    deep_water: str = "bold #0d47a1"
    lava: str = "bold #ff5722"
    tree: str = "bold #33691e"
    chasm: str = "#1a237e"
    grass: str = "#66bb6a"
    mud: str = "#795548"

    # --- floor features ---
    shrub: str = "#43a047"
    mushroom: str = "#ab47bc"
    rubble: str = "#757575"

    # --- traps / targeting / features ---
    trap: str = "bold #FF5C5C"
    altar: str = "bold #E6D8A0"
    burning: str = "bold #FF5722"
    target: str = "bold #FFE066"
    target_path: str = "#8a7d3a"
    stair_cursor: str = "bold reverse #ffe066"


class TerrainConfig:
    """Logical terrain types stored on each cell."""

    FLOOR = "floor"
    WALL = "wall"
    DOOR_CLOSED = "door_closed"
    DOOR_OPEN = "door_open"
    SECRET_DOOR = "secret_door"
    STAIRS_DOWN = "stairs_down"
    STAIRS_UP = "stairs_up"

    # --- scenery terrain ---
    SHALLOW_WATER = "shallow_water"     # wadeable, slows slightly
    DEEP_WATER = "deep_water"           # impassable, transparent
    LAVA = "lava"                       # impassable, transparent (future: burn damage)
    TREE = "tree"                       # impassable, opaque
    CHASM = "chasm"                     # impassable void, transparent
    GRASS = "grass"                     # walkable floor variant
    MUD = "mud"                         # walkable floor variant

    walkable = {FLOOR, DOOR_OPEN, STAIRS_DOWN, STAIRS_UP, SHALLOW_WATER, GRASS, MUD}
    blocks_sight = {WALL, DOOR_CLOSED, SECRET_DOOR, TREE}


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
    armour: str = "["
    throwables: str = "/"
    bag: str = "("
    orb: str = "0"
    shard: str = "*"
    trap: str = "^"          # a revealed trap
    altar: str = "_"         # a temple altar
    burning: str = "#"       # burning terrain tile

    # scenery terrain
    shallow_water: str = "~"
    deep_water: str = "≈"
    lava: str = "▒"
    tree: str = "♣"
    chasm: str = "░"
    grass: str = ","
    mud: str = ";"

    # floor features
    shrub: str = "%"
    mushroom: str = '"'
    rubble: str = ":"

    # npcs
    chemist: str = "C"
    blacksmith: str = "B"
    healer: str = "H"
    merchant: str = "M"
    fletcher: str = "F"
    traders: list[str] = [chemist, blacksmith, merchant, fletcher]
    npcs: list[str] = [chemist, blacksmith, healer, merchant, fletcher]

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
        TerrainConfig.SHALLOW_WATER: shallow_water,
        TerrainConfig.DEEP_WATER: deep_water,
        TerrainConfig.LAVA: lava,
        TerrainConfig.TREE: tree,
        TerrainConfig.CHASM: chasm,
        TerrainConfig.GRASS: grass,
        TerrainConfig.MUD: mud,
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
        armour: "armour",
        throwables: "throwables",
        bag: "bag",
        orb: "orb",
        "*": "shard",
        trap: "trap",
        altar: "altar",
        chemist: "chemist",
        blacksmith: "blacksmith",
        healer: "healer",
        merchant: "merchant",
        fletcher: "fletcher",
        # scenery terrain
        shallow_water: "shallow_water",
        deep_water: "deep_water",
        lava: "lava",
        tree: "tree",
        chasm: "chasm",
        grass: "grass",
        mud: "mud",
        # floor features
        shrub: "shrub",
        mushroom: "mushroom",
        rubble: "rubble",
    }


class MapConfig:
    """Per-floor map dimension ranges. Levels average ~70x70 and never exceed 80x80.
    Only a window of the map is shown at a time (see view_width/view_height); the player
    discovers the floor's true extent by exploring."""

    min_width: int = 60
    max_width: int = 80
    min_height: int = 60
    max_height: int = 80
    min_distance: int = 28  # min Chebyshev distance between up/down stairs

    # On-screen viewport (the map scrolls to follow the player, DCSS-style). Kept below
    # the minimum map size so the view always scrolls on BOTH axes. Odd values centre
    # the player exactly.
    view_width: int = 43
    view_height: int = 25


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
    floor_armour: int = 2
    floor_throwables: int = 2
    floor_spellbooks: int = 1
    traps_base: int = 2             # +depth // 2


class ProgressionConfig:
    """Character growth: XP curve and per-level stat gains."""

    hp_per_level: int = 5
    accuracy_per_level: int = 1     # +1% to-hit per level
    damage_every: int = 2           # +1 damage every N levels

    @staticmethod
    def xp_for(level: int) -> int:
        """XP needed to advance from *level* to the next."""
        return 8 * level + 2


class PlayerConfig:
    """Player starting statistics."""

    max_inventory: int = 42
    health: int = 20
    max_health: int = 20
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
    progression = ProgressionConfig
    player = PlayerConfig


config = Config
