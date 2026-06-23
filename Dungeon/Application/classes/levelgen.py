"""Procedural dungeon level generator — multi-algorithm, variable-size floors.

Produces a terrain grid plus structural metadata (rooms, stairs, a hidden vault, and
the list of spawnable floor cells) that :class:`DungeonMap` turns into live cells and
that the game populates with monsters, items and NPCs.

Three layout algorithms are randomly chosen each floor:
  * ``rooms`` — enhanced rooms-and-corridors with rectangular and oval rooms
  * ``cave``  — cellular-automata caverns for organic, winding spaces
  * ``bsp``   — binary space partition for structured, interlocking rooms
"""

import math
import random

from ..config import config

T = config.terrain


class Room:
    """A rectangular or oval room on the grid."""

    def __init__(self, x: int, y: int, w: int, h: int, shape: str = "rect") -> None:
        self.x, self.y, self.w, self.h = x, y, w, h
        self.shape = shape          # "rect" or "oval"

    @property
    def cx(self) -> int:
        return self.x + self.w // 2

    @property
    def cy(self) -> int:
        return self.y + self.h // 2

    @property
    def center(self) -> tuple[int, int]:
        return (self.cy, self.cx)

    def interior(self) -> list[tuple[int, int]]:
        if self.shape == "oval":
            return self._oval_interior()
        return [(y, x) for y in range(self.y, self.y + self.h) for x in range(self.x, self.x + self.w)]

    def _oval_interior(self) -> list[tuple[int, int]]:
        rx = self.w / 2
        ry = self.h / 2
        cxf, cyf = self.x + rx - 0.5, self.y + ry - 0.5
        cells = []
        for y in range(self.y, self.y + self.h):
            for x in range(self.x, self.x + self.w):
                dx, dy = x - cxf, y - cyf
                if (dx * dx) / (rx * rx) + (dy * dy) / (ry * ry) <= 0.9:
                    cells.append((y, x))
        return cells

    def intersects(self, other: "Room", pad: int = 1) -> bool:
        return (
            self.x - pad < other.x + other.w
            and self.x + self.w + pad > other.x
            and self.y - pad < other.y + other.h
            and self.y + self.h + pad > other.y
        )


class LevelLayout:
    """The finished level: terrain grid + structural anchors for spawning."""

    def __init__(self, w: int, h: int) -> None:
        self.width = w
        self.height = h
        self.terrain: list[list[str]] = []
        self.rooms: list[Room] = []
        self.stairs_up: tuple[int, int] | None = None
        self.stairs_down: tuple[int, int] | None = None
        self.vault_cells: list[tuple[int, int]] = []
        self.temple_cells: list[tuple[int, int]] = []
        self.altar: tuple[int, int] | None = None
        self.floor_cells: list[tuple[int, int]] = []
        self.scenery_features: list[tuple[int, int, str]] = []


# ------------------------------------------------------------------ dispatcher

def generate_level(
    is_last: bool = False,
    depth: int = 1,
    layout_hint: str = "any",
    structures: list | None = None,
    terrain_features: list | None = None,
    water_density: str = "small",
) -> LevelLayout:
    """Pick a random generator and produce one floor.

    Deeper floors are more likely to use complex layouts and are slightly larger.
    layout_hint biases algorithm selection: "cave" | "rooms" | "bsp" | "any".
    structures / terrain_features are LLM-supplied biome hints passed to scenery generation.
    water_density controls ambient pond size: "small" | "medium" | "large".
    """
    w = random.randint(config.map.min_width, config.map.max_width)
    h = random.randint(config.map.min_height, config.map.max_height)

    weights = {"rooms": 40, "cave": 30, "bsp": 30}
    if layout_hint in ("cave", "rooms", "bsp"):
        weights = {k: (100 if k == layout_hint else 5) for k in weights}
    choice = random.choices(list(weights.keys()), weights=list(weights.values()), k=1)[0]

    if choice == "cave":
        return _generate_cave(w, h, is_last, structures=structures, terrain_features=terrain_features, water_density=water_density)
    if choice == "bsp":
        return _generate_bsp(w, h, is_last, structures=structures, terrain_features=terrain_features, water_density=water_density)
    return _generate_rooms(w, h, is_last, structures=structures, terrain_features=terrain_features, water_density=water_density)


# ------------------------------------------------------------ rooms & corridors

def _generate_rooms(w: int, h: int, is_last: bool,
                    structures=None, terrain_features=None,
                    water_density: str = "small") -> LevelLayout:
    """Classic rooms-and-corridors with a mix of rectangular and oval rooms."""
    grid = [[T.WALL for _ in range(w)] for _ in range(h)]
    layout = LevelLayout(w, h)

    interior_floor: set[tuple[int, int]] = set()
    rooms: list[Room] = []
    attempts = 0
    area = w * h
    target = max(10, min(30, area // 220))   # scale room count with the larger maps
    while len(rooms) < target and attempts < 800:
        attempts += 1
        rw, rh = random.randint(4, 12), random.randint(4, 9)
        rx, ry = random.randint(1, w - rw - 2), random.randint(1, h - rh - 2)
        shape = "oval" if random.random() < 0.25 else "rect"
        room = Room(rx, ry, rw, rh, shape=shape)
        if any(room.intersects(other) for other in rooms):
            continue
        rooms.append(room)
        for (cy, cx) in room.interior():
            grid[cy][cx] = T.FLOOR
            interior_floor.add((cy, cx))

    for a, b in zip(rooms, rooms[1:]):
        _carve_corridor(grid, interior_floor, a.center, b.center, w, h)

    layout.terrain = grid
    layout.rooms = rooms
    _place_stairs_and_vault(layout, grid, rooms, interior_floor, is_last, w, h,
                            structures=structures, terrain_features=terrain_features,
                            water_density=water_density)
    return layout


# ---------------------------------------------------------- cellular automata

def _generate_cave(w: int, h: int, is_last: bool,
                   structures=None, terrain_features=None,
                   water_density: str = "small") -> LevelLayout:
    """Organic cave system via cellular automata with noise caverns."""
    grid = [[T.WALL for _ in range(w)] for _ in range(h)]
    layout = LevelLayout(w, h)

    for y in range(1, h - 1):
        for x in range(1, w - 1):
            grid[y][x] = T.FLOOR if random.random() < 0.50 else T.WALL

    for _pass in range(4):
        next_grid = [[T.WALL for _ in range(w)] for _ in range(h)]
        for y in range(1, h - 1):
            for x in range(1, w - 1):
                wall_count = 0
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        if dy == 0 and dx == 0:
                            continue
                        if grid[y + dy][x + dx] == T.WALL:
                            wall_count += 1
                next_grid[y][x] = T.FLOOR if wall_count < 5 else T.WALL
        grid = next_grid

    for y in range(1, h - 1):
        for x in range(1, w - 1):
            wall_count = sum(
                1 for dy in (-1, 0, 1) for dx in (-1, 0, 1)
                if not (dy == 0 and dx == 0) and grid[y + dy][x + dx] == T.WALL
            )
            if wall_count >= 5:
                grid[y][x] = T.WALL

    for _ in range(random.randint(3, 6)):
        rw, rh = random.randint(3, 6), random.randint(2, 4)
        rx = random.randint(2, w - rw - 2)
        ry = random.randint(2, h - rh - 2)
        for dy in range(ry, ry + rh):
            for dx in range(rx, rx + rw):
                if 0 < dy < h - 1 and 0 < dx < w - 1:
                    grid[dy][dx] = T.FLOOR

    _keep_largest_region(grid, w, h)

    interior_floor = set()
    rooms: list[Room] = []
    for y in range(h):
        for x in range(w):
            if grid[y][x] == T.FLOOR and 0 < y < h - 1 and 0 < x < w - 1:
                interior_floor.add((y, x))

    layout.terrain = grid
    layout.rooms = rooms

    floor_list = sorted(interior_floor)
    if len(floor_list) >= 2:
        layout.stairs_up = floor_list[len(floor_list) // 4]
        layout.stairs_down = None if is_last else floor_list[3 * len(floor_list) // 4]
        if layout.stairs_up in interior_floor:
            gy, gx = layout.stairs_up
            grid[gy][gx] = T.STAIRS_UP
        if layout.stairs_down and layout.stairs_down in interior_floor:
            gy, gx = layout.stairs_down
            grid[gy][gx] = T.STAIRS_DOWN

    _place_cave_vault(layout, grid, interior_floor, is_last, w, h)
    _scatter_scenery(layout, grid, w, h,
                     structures=structures, terrain_features=terrain_features,
                     water_density=water_density)
    _build_floor_cells(layout, grid, w, h)
    return layout


# ------------------------------------------------------ binary space partition

class _BSPNode:
    def __init__(self, x: int, y: int, w: int, h: int) -> None:
        self.x, self.y, self.w, self.h = x, y, w, h
        self.left: _BSPNode | None = None
        self.right: _BSPNode | None = None
        self.room: Room | None = None


def _generate_bsp(w: int, h: int, is_last: bool,
                  structures=None, terrain_features=None,
                  water_density: str = "small") -> LevelLayout:
    """BSP-based layout: tree of partitions generates varied, interlocking rooms."""
    grid = [[T.WALL for _ in range(w)] for _ in range(h)]
    layout = LevelLayout(w, h)

    root = _BSPNode(1, 1, w - 2, h - 2)
    _bsp_split(root, min_size=8, min_aspect=4)

    rooms: list[Room] = []
    _bsp_place_rooms(root, rooms)

    interior_floor: set[tuple[int, int]] = set()
    for room in rooms:
        for (cy, cx) in room.interior():
            grid[cy][cx] = T.FLOOR
            interior_floor.add((cy, cx))

    _bsp_connect(root, grid, interior_floor)

    layout.terrain = grid
    layout.rooms = rooms
    _place_stairs_and_vault(layout, grid, rooms, interior_floor, is_last, w, h,
                            structures=structures, terrain_features=terrain_features,
                            water_density=water_density)
    return layout


def _bsp_split(node: _BSPNode, min_size: int, min_aspect: int) -> None:
    if node.w < min_size * 2 and node.h < min_size * 2:
        return
    horizontal = node.h > node.w and node.w >= min_size * 2
    vertical = node.w > node.h and node.h >= min_size * 2
    if not horizontal and not vertical:
        horizontal = node.h >= min_size * 2
        vertical = node.w >= min_size * 2
        if horizontal and vertical:
            horizontal = random.random() < 0.5

    if horizontal and node.h >= min_size * 2:
        split = random.randint(int(node.h * 0.35), int(node.h * 0.65))
        node.left = _BSPNode(node.x, node.y, node.w, split)
        node.right = _BSPNode(node.x, node.y + split, node.w, node.h - split)
    elif vertical and node.w >= min_size * 2:
        split = random.randint(int(node.w * 0.35), int(node.w * 0.65))
        node.left = _BSPNode(node.x, node.y, split, node.h)
        node.right = _BSPNode(node.x + split, node.y, node.w - split, node.h)
    else:
        return
    _bsp_split(node.left, min_size, min_aspect)
    _bsp_split(node.right, min_size, min_aspect)


def _bsp_place_rooms(node: _BSPNode, rooms: list[Room]) -> None:
    if node.left or node.right:
        if node.left:
            _bsp_place_rooms(node.left, rooms)
        if node.right:
            _bsp_place_rooms(node.right, rooms)
        return
    rw = max(3, random.randint(node.w // 3, node.w - 2))
    rh = max(3, random.randint(node.h // 3, node.h - 2))
    rx = node.x + random.randint(1, max(1, node.w - rw - 1))
    ry = node.y + random.randint(1, max(1, node.h - rh - 1))
    shape = "oval" if random.random() < 0.2 else "rect"
    node.room = Room(rx, ry, rw, rh, shape=shape)
    rooms.append(node.room)


def _bsp_connect(node: _BSPNode, grid, interior_floor) -> None:
    if node.left and node.right:
        _bsp_connect(node.left, grid, interior_floor)
        _bsp_connect(node.right, grid, interior_floor)
        lc = _bsp_leaf_center(node.left)
        rc = _bsp_leaf_center(node.right)
        if lc and rc:
            _carve_corridor(grid, interior_floor, lc, rc, node.x + node.w, node.y + node.h)


def _bsp_leaf_center(node: _BSPNode) -> tuple[int, int] | None:
    if node.room:
        return node.room.center
    if node.left and node.right:
        return _bsp_leaf_center(node.left) or _bsp_leaf_center(node.right)
    if node.left:
        return _bsp_leaf_center(node.left)
    if node.right:
        return _bsp_leaf_center(node.right)
    return None


# ------------------------------------------------------------ shared utilities

def _place_stairs_and_vault(layout, grid, rooms, interior_floor, is_last, w, h,
                            structures=None, terrain_features=None,
                            water_density: str = "small") -> None:
    if not rooms:
        return
    layout.stairs_up = rooms[0].center
    grid[rooms[0].cy][rooms[0].cx] = T.STAIRS_UP

    down_room = None
    if not is_last:
        for room in sorted(rooms[1:], key=lambda r: -(
                max(abs(r.cy - rooms[0].cy), abs(r.cx - rooms[0].cx)))):
            if max(abs(room.cy - rooms[0].cy), abs(room.cx - rooms[0].cx)) >= config.map.min_distance:
                down_room = room
                break
        down_room = down_room or (rooms[-1] if len(rooms) > 1 else rooms[0])
        layout.stairs_down = down_room.center
        grid[down_room.cy][down_room.cx] = T.STAIRS_DOWN

    used = {rooms[0]}
    if down_room:
        used.add(down_room)
    vault_candidates = [r for r in rooms if r not in used]
    if vault_candidates:
        vault = random.choice(vault_candidates)
        used.add(vault)
        layout.vault_cells = vault.interior()
        if not is_last:
            for (vy, vx) in _mouths_of(grid, vault, w, h):
                grid[vy][vx] = T.SECRET_DOOR

    # A pillared temple may appear, guarded but rewarding, with a healing altar at its heart.
    if random.random() < 0.30:
        candidates = [r for r in rooms if r not in used and r.w >= 6 and r.h >= 5]
        if candidates:
            _carve_temple(layout, grid, random.choice(candidates))

    _scatter_scenery(layout, grid, w, h,
                     structures=structures, terrain_features=terrain_features,
                     water_density=water_density)
    _build_floor_cells(layout, grid, w, h)


def _carve_temple(layout, grid, room) -> None:
    """Turn a room into a pillared temple: a grid of pillars with a central altar."""
    floor_cells = []
    for y in range(room.y, room.y + room.h):
        for x in range(room.x, room.x + room.w):
            on_edge = (y == room.y or y == room.y + room.h - 1
                       or x == room.x or x == room.x + room.w - 1)
            if not on_edge and (y - room.y) % 2 == 0 and (x - room.x) % 2 == 0:
                grid[y][x] = T.WALL          # a pillar
            else:
                grid[y][x] = T.FLOOR
                floor_cells.append((y, x))
    altar = (room.cy, room.cx)
    if grid[altar[0]][altar[1]] != T.FLOOR:  # never bury the altar in a pillar
        altar = (room.cy, room.cx + 1)
    grid[altar[0]][altar[1]] = T.FLOOR
    layout.altar = altar
    layout.temple_cells = [c for c in floor_cells if c != altar]


def _place_cave_vault(layout, grid, interior_floor, is_last, w, h) -> None:
    floor_list = sorted(interior_floor)
    if len(floor_list) < 6:
        return
    vault_center = floor_list[random.randint(len(floor_list) // 3, 2 * len(floor_list) // 3)]
    cy, cx = vault_center
    vault_cells = []
    for dy in range(-2, 3):
        for dx in range(-2, 3):
            ny, nx = cy + dy, cx + dx
            if 0 < ny < h - 1 and 0 < nx < w - 1:
                if grid[ny][nx] == T.FLOOR or grid[ny][nx] == T.WALL:
                    grid[ny][nx] = T.FLOOR
                    vault_cells.append((ny, nx))
    layout.vault_cells = vault_cells
    if not is_last and vault_cells:
        for (vy, vx) in vault_cells:
            for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                ny, nx = vy + dy, vx + dx
                if 0 <= ny < h and 0 <= nx < w and grid[ny][nx] == T.FLOOR and (ny, nx) not in vault_cells:
                    grid[ny][nx] = T.SECRET_DOOR
                    break


_SPAWNABLE = {T.FLOOR, T.GRASS, T.MUD}


def _build_floor_cells(layout, grid, w, h) -> None:
    reserved = set(layout.vault_cells) | set(layout.temple_cells)
    if layout.altar:
        reserved.add(layout.altar)
    occupied = {layout.stairs_up, layout.stairs_down}
    for y in range(h):
        for x in range(w):
            if grid[y][x] in _SPAWNABLE and (y, x) not in reserved and (y, x) not in occupied:
                layout.floor_cells.append((y, x))


def _keep_largest_region(grid, w, h) -> None:
    visited: set[tuple[int, int]] = set()
    regions: list[set[tuple[int, int]]] = []
    for y in range(1, h - 1):
        for x in range(1, w - 1):
            if grid[y][x] != T.FLOOR or (y, x) in visited:
                continue
            region: set[tuple[int, int]] = set()
            stack = [(y, x)]
            while stack:
                cy, cx = stack.pop()
                if (cy, cx) in visited or grid[cy][cx] != T.FLOOR:
                    continue
                visited.add((cy, cx))
                region.add((cy, cx))
                for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1),
                                (-1, -1), (-1, 1), (1, -1), (1, 1)):
                    ny, nx = cy + dy, cx + dx
                    if 0 < ny < h - 1 and 0 < nx < w - 1 and (ny, nx) not in visited:
                        stack.append((ny, nx))
            regions.append(region)
    if not regions:
        return
    largest = max(regions, key=len)
    for region in regions:
        if region is not largest:
            for (ry, rx) in region:
                grid[ry][rx] = T.WALL


# --------------------------------------------------------- corridor / door helpers

def _carve_corridor(grid, interior_floor, start, goal, w, h) -> None:
    (sy, sx), (gy, gx) = start, goal
    horizontal_first = random.random() < 0.5
    path: list[tuple[int, int]] = []
    if horizontal_first:
        path += [(sy, x) for x in _between(sx, gx)]
        path += [(y, gx) for y in _between(sy, gy)]
    else:
        path += [(y, sx) for y in _between(sy, gy)]
        path += [(gy, x) for x in _between(sx, gx)]

    for (y, x) in path:
        if not (0 <= y < h and 0 <= x < w):
            continue
        if (y, x) in interior_floor:
            continue
        if grid[y][x] == T.FLOOR:
            continue
        if _borders_interior(interior_floor, y, x):
            grid[y][x] = T.DOOR_CLOSED
        else:
            grid[y][x] = T.FLOOR


def _between(a: int, b: int) -> range:
    return range(a, b + 1) if a <= b else range(a, b - 1, -1)


def _borders_interior(interior_floor, y: int, x: int) -> bool:
    return any((y + dy, x + dx) in interior_floor for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1)))


# ------------------------------------------------------------ scenery generation

_SPECIAL_TERRAIN = {T.STAIRS_UP, T.STAIRS_DOWN, T.DOOR_CLOSED, T.DOOR_OPEN, T.SECRET_DOOR}


def _scatter_scenery(
    layout: LevelLayout,
    grid: list,
    w: int,
    h: int,
    structures: list | None = None,
    terrain_features: list | None = None,
    water_density: str = "small",
) -> None:
    """Post-process the grid: add ponds, trees, grass/mud, floor features, then structures."""
    protected: set[tuple[int, int]] = set()
    for pos in (layout.stairs_up, layout.stairs_down):
        if pos:
            protected.update(_near(pos[0], pos[1], 2, w, h))
    protected.update(layout.vault_cells)
    protected.update(layout.temple_cells)
    if layout.altar:
        protected.update(_near(layout.altar[0], layout.altar[1], 2, w, h))

    _place_ponds(layout, grid, protected, w, h, water_density=water_density)
    _place_trees(layout, grid, protected, w, h)
    _place_grass_and_mud(layout, grid, protected, w, h)
    _place_floor_features(layout, grid, protected, w, h)

    if terrain_features:
        _apply_terrain_features(layout, grid, protected, w, h, terrain_features)
    if structures:
        _place_structures(layout, grid, protected, w, h, structures)


def _near(cy: int, cx: int, r: int, w: int, h: int) -> set[tuple[int, int]]:
    """Chebyshev-r neighbourhood of (cy, cx), clamped to map bounds."""
    return {
        (cy + dy, cx + dx)
        for dy in range(-r, r + 1) for dx in range(-r, r + 1)
        if 0 <= cy + dy < h and 0 <= cx + dx < w
    }


def _place_ponds(layout: LevelLayout, grid, protected: set, w: int, h: int,
                  water_density: str = "small") -> None:
    """Carve ambient ponds inside qualifying rooms (never in corridors).

    water_density controls the pool radius and deep-water extent:
      - small  (default): 3x3, 1 deep center + 8 shallow ring
      - medium          : 5x5, 3x3 deep center + shallow ring
      - large           : 7x7, 3x3 deep center + 25-tile shallow ring
    Larger densities require bigger rooms to fit the pool.
    """
    if not layout.rooms:
        return  # Cave maps have no rooms; corridors are irregular — skip ponds

    if water_density not in ("small", "medium", "large"):
        water_density = "small"
    # Larger pools need bigger rooms — guard against cramped placements.
    # The room's 2-cell-margin interior is what the pool must fit inside.
    min_w, min_h = {"small": (7, 5), "medium": (9, 7), "large": (11, 9)}[water_density]

    eligible = [
        r for r in layout.rooms
        if r.w >= min_w and r.h >= min_h and (r.cy, r.cx) not in protected
    ]
    if not eligible:
        return

    random.shuffle(eligible)
    num_ponds = random.randint(0, min(2, len(eligible)))

    for room in eligible[:num_ponds]:
        # Inner area with 2-cell margin from room walls — pond stays fully interior
        inner = {
            (y, x)
            for y in range(room.y + 2, room.y + room.h - 2)
            for x in range(room.x + 2, room.x + room.w - 2)
            if (y, x) not in protected and grid[y][x] == T.FLOOR
        }
        _carve_room_pond(grid, room.cy, room.cx, inner, water_density)


# (outer_shallow_radius, inner_deep_radius)
_POND_GEOMETRY: dict[str, tuple[float, float]] = {
    "small": (1.5, 0.5),
    "medium": (2.5, 1.5),
    "large": (3.5, 1.5),
}


def _carve_room_pond(grid, cy: int, cx: int, inner: set, size: str = "small") -> None:
    """Replace cells in *inner* near (cy, cx) with deep/shallow water.

    size: 'small' (3x3, 1 deep) | 'medium' (5x5, 9 deep) | 'large' (7x7, 9 deep)
    """
    outer_r, inner_r = _POND_GEOMETRY.get(size, (1.5, 0.5))
    for (ny, nx) in inner:
        dy, dx = ny - cy, nx - cx
        dist = math.sqrt(dy * dy + dx * dx)
        if dist <= inner_r:
            grid[ny][nx] = T.DEEP_WATER
        elif dist <= outer_r:
            grid[ny][nx] = T.SHALLOW_WATER


def _place_trees(layout: LevelLayout, grid, protected: set, w: int, h: int) -> None:
    """Scatter isolated trees in open floor areas (never in corridors, never adjacent)."""
    num_trees = random.randint(5, 15)
    placed: set[tuple[int, int]] = set()

    candidates = [
        (y, x) for y in range(1, h - 1) for x in range(1, w - 1)
        if grid[y][x] == T.FLOOR and (y, x) not in protected
    ]
    random.shuffle(candidates)

    for cy, cx in candidates:
        if len(placed) >= num_trees:
            break
        # All 4 cardinal neighbours must be floor — eliminates corridors and junctions
        if not all(
            0 <= cy + dy < h and 0 <= cx + dx < w
            and grid[cy + dy][cx + dx] == T.FLOOR
            for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1))
        ):
            continue
        # No other trees adjacent
        if any((cy + dy, cx + dx) in placed
               for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1),
                               (-1, -1), (-1, 1), (1, -1), (1, 1))):
            continue
        # No special terrain adjacent (doors, stairs)
        if any(
            grid[cy + dy][cx + dx] in _SPECIAL_TERRAIN
            for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1))
            if 0 <= cy + dy < h and 0 <= cx + dx < w
        ):
            continue
        grid[cy][cx] = T.TREE
        placed.add((cy, cx))


def _place_grass_and_mud(layout: LevelLayout, grid, protected: set, w: int, h: int) -> None:
    """Paint organic blobs of grass or mud over floor cells."""
    num_patches = random.randint(2, 5)
    candidates = [
        (y, x) for y in range(1, h - 1) for x in range(1, w - 1)
        if grid[y][x] == T.FLOOR and (y, x) not in protected
    ]
    if not candidates:
        return

    for _ in range(num_patches):
        if not candidates:
            break
        sy, sx = random.choice(candidates)
        variant = T.GRASS if random.random() < 0.70 else T.MUD
        radius = random.randint(2, 4)
        for dy in range(-radius, radius + 1):
            for dx in range(-radius, radius + 1):
                ny, nx = sy + dy, sx + dx
                if not (0 < ny < h - 1 and 0 < nx < w - 1):
                    continue
                if (ny, nx) in protected or grid[ny][nx] != T.FLOOR:
                    continue
                if math.sqrt(dy * dy + dx * dx) <= radius * random.uniform(0.6, 1.0):
                    grid[ny][nx] = variant
        candidates = [(y, x) for (y, x) in candidates if grid[y][x] == T.FLOOR]


def _place_floor_features(layout: LevelLayout, grid, protected: set, w: int, h: int) -> None:
    """Scatter shrubs, mushrooms, and rubble on open floor/grass/mud cells."""
    spawnable = (T.FLOOR, T.GRASS, T.MUD)
    candidates = [
        (y, x) for y in range(1, h - 1) for x in range(1, w - 1)
        if grid[y][x] in spawnable and (y, x) not in protected
    ]
    random.shuffle(candidates)
    taken: set[tuple[int, int]] = set()

    # Shrubs — prefer cells with open neighbours
    for cy, cx in candidates:
        if len([f for f in layout.scenery_features if f[2] == "shrub"]) >= random.randint(3, 8):
            break
        if (cy, cx) in taken:
            continue
        open_n = sum(
            1 for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1))
            if 0 <= cy + dy < h and 0 <= cx + dx < w
            and grid[cy + dy][cx + dx] in spawnable
        )
        if open_n >= 3:
            layout.scenery_features.append((cy, cx, "shrub"))
            taken.add((cy, cx))

    # Mushrooms — prefer corners with few open neighbours
    for cy, cx in candidates:
        if len([f for f in layout.scenery_features if f[2] == "mushroom"]) >= random.randint(2, 5):
            break
        if (cy, cx) in taken:
            continue
        open_n = sum(
            1 for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1))
            if 0 <= cy + dy < h and 0 <= cx + dx < w
            and grid[cy + dy][cx + dx] in spawnable
        )
        if open_n <= 2:
            layout.scenery_features.append((cy, cx, "mushroom"))
            taken.add((cy, cx))

    # Rubble — rare, scattered anywhere
    remaining = [(y, x) for (y, x) in candidates if (y, x) not in taken]
    random.shuffle(remaining)
    for cy, cx in remaining[:random.randint(1, 3)]:
        layout.scenery_features.append((cy, cx, "rubble"))


# ---------------------------------------------------------- structure blueprints

from dataclasses import dataclass as _dc
from typing import Callable as _Callable


@_dc
class Structure:
    """Blueprint for a Minecraft-style room structure placed by LLM biome themes."""
    name: str
    min_room_w: int
    min_room_h: int
    placer: _Callable
    max_per_floor: int = 1


def _room_inner(room: Room, margin: int = 1) -> list[tuple[int, int]]:
    return [
        (y, x)
        for y in range(room.y + margin, room.y + room.h - margin)
        for x in range(room.x + margin, room.x + room.w - margin)
    ]


def _place_shrine(layout: LevelLayout, grid, room: Room, protected: set, w: int, h: int) -> bool:
    """Altar on a floor pad flanked by four diagonal pillar-walls."""
    cy, cx = room.cy, room.cx
    if (cy - room.y < 2 or room.y + room.h - 1 - cy < 2 or
            cx - room.x < 2 or room.x + room.w - 1 - cx < 2):
        return False
    if (cy, cx) in protected or grid[cy][cx] in _SPECIAL_TERRAIN:
        return False
    pillar_pos = [(cy - 1, cx - 1), (cy - 1, cx + 1), (cy + 1, cx - 1), (cy + 1, cx + 1)]
    for (py, px) in pillar_pos:
        if (py, px) in protected or grid[py][px] in _SPECIAL_TERRAIN:
            return False
    for (py, px) in pillar_pos:
        grid[py][px] = T.WALL
    grid[cy][cx] = T.FLOOR
    layout.scenery_features.append((cy, cx, "altar"))
    if layout.altar is None:
        layout.altar = (cy, cx)
    return True


def _place_mushroom_grove(layout: LevelLayout, grid, room: Room, protected: set, w: int, h: int) -> bool:
    """Mud-floored room thick with mushrooms in the darker corners."""
    inner = [(y, x) for (y, x) in _room_inner(room, 1)
             if (y, x) not in protected and grid[y][x] == T.FLOOR]
    if len(inner) < 8:
        return False
    for (y, x) in inner:
        grid[y][x] = T.MUD
    spawnable = {T.MUD, T.FLOOR, T.GRASS}
    placed = 0
    for (y, x) in inner:
        open_n = sum(
            1 for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1))
            if 0 <= y + dy < h and 0 <= x + dx < w
            and grid[y + dy][x + dx] in spawnable
        )
        if open_n <= 2 and random.random() < 0.65:
            layout.scenery_features.append((y, x, "mushroom"))
            placed += 1
    if placed < 2:
        for (y, x) in random.sample(inner, min(3, len(inner))):
            layout.scenery_features.append((y, x, "mushroom"))
    return True


def _place_overgrown_room(layout: LevelLayout, grid, room: Room, protected: set, w: int, h: int) -> bool:
    """Grass-covered room with isolated trees and scattered shrubs."""
    inner = [(y, x) for (y, x) in _room_inner(room, 1)
             if (y, x) not in protected and grid[y][x] == T.FLOOR]
    if len(inner) < 8:
        return False
    for (y, x) in inner:
        grid[y][x] = T.GRASS
    walkable = {T.GRASS, T.FLOOR, T.MUD}
    tree_set: set[tuple[int, int]] = set()
    shuffled = list(inner)
    random.shuffle(shuffled)
    for (y, x) in shuffled:
        if len(tree_set) >= max(1, len(inner) // 8):
            break
        if not all(
            0 <= y + dy < h and 0 <= x + dx < w
            and grid[y + dy][x + dx] in walkable
            for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1))
        ):
            continue
        if any((y + dy, x + dx) in tree_set
               for dy, dx in ((-1,0),(1,0),(0,-1),(0,1),(-1,-1),(-1,1),(1,-1),(1,1))):
            continue
        if any(grid[y + dy][x + dx] in _SPECIAL_TERRAIN
               for dy, dx in ((-1,0),(1,0),(0,-1),(0,1))
               if 0 <= y + dy < h and 0 <= x + dx < w):
            continue
        grid[y][x] = T.TREE
        tree_set.add((y, x))
    for (y, x) in inner:
        if grid[y][x] == T.GRASS and (y, x) not in protected and random.random() < 0.25:
            layout.scenery_features.append((y, x, "shrub"))
    return True


def _place_ruined_hall(layout: LevelLayout, grid, room: Room, protected: set, w: int, h: int) -> bool:
    """A row of evenly-spaced wall pillars across the room with rubble debris."""
    if room.w < 7:
        return False
    pillar_row = room.cy
    pillar_cols = list(range(room.x + 2, room.x + room.w - 2, 2))
    for px in pillar_cols:
        if (pillar_row, px) not in protected and grid[pillar_row][px] not in _SPECIAL_TERRAIN:
            if grid[pillar_row][px] == T.FLOOR:
                grid[pillar_row][px] = T.WALL
    above_ok = any(
        grid[pillar_row - 1][x] == T.FLOOR
        for x in range(room.x + 1, room.x + room.w - 1)
        if 0 < pillar_row - 1 < h - 1
    )
    below_ok = any(
        grid[pillar_row + 1][x] == T.FLOOR
        for x in range(room.x + 1, room.x + room.w - 1)
        if 0 < pillar_row + 1 < h - 1
    )
    if not above_ok or not below_ok:
        for px in pillar_cols:
            if grid[pillar_row][px] == T.WALL and (pillar_row, px) not in protected:
                grid[pillar_row][px] = T.FLOOR
        return False
    inner = [(y, x) for (y, x) in _room_inner(room, 1)
             if grid[y][x] == T.FLOOR and (y, x) not in protected]
    for (y, x) in random.sample(inner, min(4, len(inner))):
        layout.scenery_features.append((y, x, "rubble"))
    return True


def _place_frozen_pond(layout: LevelLayout, grid, room: Room, protected: set, w: int, h: int) -> bool:
    """A shallow-water 'frozen' pool with rubble crackle around the rim."""
    inner = {
        (y, x)
        for y in range(room.y + 2, room.y + room.h - 2)
        for x in range(room.x + 2, room.x + room.w - 2)
        if (y, x) not in protected and grid[y][x] == T.FLOOR
    }
    if len(inner) < 4:
        return False
    cy, cx = room.cy, room.cx
    pond: set[tuple[int, int]] = set()
    for (ny, nx) in inner:
        if math.sqrt((ny - cy) ** 2 + (nx - cx) ** 2) <= 1.5:
            grid[ny][nx] = T.SHALLOW_WATER
            pond.add((ny, nx))
    if not pond:
        return False
    for (py, px) in pond:
        for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            ny, nx = py + dy, px + dx
            if ((ny, nx) not in pond and (ny, nx) not in protected
                    and 0 < ny < h - 1 and 0 < nx < w - 1
                    and grid[ny][nx] == T.FLOOR):
                layout.scenery_features.append((ny, nx, "rubble"))
    return True


def _place_campsite(layout: LevelLayout, grid, room: Room, protected: set, w: int, h: int) -> bool:
    """A grass clearing with a rubble campfire and shrub bedrolls."""
    cy, cx = room.cy, room.cx
    if (cy - room.y < 2 or room.y + room.h - 1 - cy < 2 or
            cx - room.x < 2 or room.x + room.w - 1 - cx < 2):
        return False
    if (cy, cx) in protected or grid[cy][cx] in _SPECIAL_TERRAIN:
        return False
    patch = [(cy + dy, cx + dx) for dy in (-1, 0, 1) for dx in (-1, 0, 1)]
    for (py, px) in patch:
        if ((py, px) not in protected and 0 < py < h - 1 and 0 < px < w - 1
                and grid[py][px] == T.FLOOR):
            grid[py][px] = T.GRASS
    if grid[cy][cx] not in _SPECIAL_TERRAIN and (cy, cx) not in protected:
        grid[cy][cx] = T.FLOOR
        layout.scenery_features.append((cy, cx, "rubble"))
    for (py, px) in patch:
        if grid[py][px] == T.GRASS and (py, px) != (cy, cx):
            layout.scenery_features.append((py, px, "shrub"))
    return True


def _place_poison_marsh(layout: LevelLayout, grid, room: Room, protected: set, w: int, h: int) -> bool:
    """Stagnant mud and shallow water with shrubs marking the hazardous ground."""
    inner = [(y, x) for (y, x) in _room_inner(room, 1)
             if (y, x) not in protected and grid[y][x] == T.FLOOR]
    if len(inner) < 8:
        return False
    target = int(len(inner) * random.uniform(0.6, 0.8))
    random.shuffle(inner)
    marsh = inner[:target]
    for (y, x) in marsh:
        grid[y][x] = T.SHALLOW_WATER if random.random() < 0.30 else T.MUD
    for (y, x) in marsh:
        if grid[y][x] == T.MUD and random.random() < 0.40:
            layout.scenery_features.append((y, x, "shrub"))
    return True


def _place_standing_stones(layout: LevelLayout, grid, room: Room, protected: set, w: int, h: int) -> bool:
    """Eight wall pillars in an octagonal ring around a central grass clearing."""
    if room.w < 7 or room.h < 7:
        return False
    cy, cx = room.cy, room.cx
    stone_offsets = [(-2, 0), (2, 0), (0, -2), (0, 2), (-2, -2), (-2, 2), (2, -2), (2, 2)]
    stones = [(cy + dy, cx + dx) for (dy, dx) in stone_offsets]
    for (sy, sx) in stones:
        if not (room.y + 1 <= sy <= room.y + room.h - 2 and
                room.x + 1 <= sx <= room.x + room.w - 2):
            return False
        if (sy, sx) in protected or grid[sy][sx] in _SPECIAL_TERRAIN:
            return False
    for (sy, sx) in stones:
        if grid[sy][sx] == T.FLOOR:
            grid[sy][sx] = T.WALL
    if (cy, cx) not in protected and grid[cy][cx] not in _SPECIAL_TERRAIN:
        grid[cy][cx] = T.GRASS
    passable = sum(
        1 for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1))
        if (0 <= cy + dy < h and 0 <= cx + dx < w
            and grid[cy + dy][cx + dx] in (T.FLOOR, T.GRASS, T.MUD, T.SHALLOW_WATER))
    )
    if passable < 2:
        for (sy, sx) in stones:
            if grid[sy][sx] == T.WALL and (sy, sx) not in protected:
                grid[sy][sx] = T.FLOOR
        return False
    return True


def _place_structures(layout: LevelLayout, grid, protected: set, w: int, h: int,
                      structures: list) -> None:
    """Stamp LLM-requested structure blueprints into qualifying rooms."""
    if not layout.rooms:
        return
    counts: dict[str, int] = {}
    room_pool = list(layout.rooms)
    random.shuffle(room_pool)
    for name in structures:
        spec = STRUCTURE_CATALOG.get(name)
        if spec is None or counts.get(name, 0) >= spec.max_per_floor:
            continue
        for room in room_pool:
            if room.w < spec.min_room_w or room.h < spec.min_room_h:
                continue
            if (room.cy, room.cx) in protected:
                continue
            if spec.placer(layout, grid, room, protected, w, h):
                protected.update(_near(room.cy, room.cx, 2, w, h))
                counts[name] = counts.get(name, 0) + 1
                room_pool.remove(room)
                break


_TERRAIN_FEATURE_MAP: dict[str, str] = {
    "lava_pools": T.LAVA,
    "chasms": T.CHASM,
    "water_pools": T.SHALLOW_WATER,
}

_POOL_GEOMETRY: dict[str, tuple[float, float]] = {
    # feat -> (outer_shallow_radius, inner_deep_radius)
    "lava_pools": (1.5, 0.0),
    "chasms": (1.5, 0.0),
    "water_pools": (3.5, 1.5),
}


def _apply_terrain_features(layout: LevelLayout, grid, protected: set, w: int, h: int,
                             terrain_features: list) -> None:
    """Place lava pools, chasms, or biome-scale water pools in qualifying rooms."""
    if not layout.rooms:
        return
    for feat in terrain_features:
        terrain_type = _TERRAIN_FEATURE_MAP.get(feat)
        if not terrain_type:
            continue
        outer_r, inner_r = _POOL_GEOMETRY.get(feat, (1.5, 0.0))
        candidates = [
            r for r in layout.rooms
            if r.w >= 7 and r.h >= 6 and (r.cy, r.cx) not in protected
        ]
        if not candidates:
            continue
        # Water pools need bigger rooms to fit a deeper pool
        if feat == "water_pools":
            wide = [r for r in candidates if r.w >= 10 and r.h >= 8]
            if wide:
                candidates = wide
        room = random.choice(candidates)
        cy, cx = room.cy, room.cx
        inner = {
            (y, x)
            for y in range(room.y + 2, room.y + room.h - 2)
            for x in range(room.x + 2, room.x + room.w - 2)
            if (y, x) not in protected and grid[y][x] == T.FLOOR
        }
        for (ny, nx) in inner:
            dist = math.sqrt((ny - cy) ** 2 + (nx - cx) ** 2)
            if dist <= inner_r and inner_r > 0:
                grid[ny][nx] = T.DEEP_WATER
                protected.add((ny, nx))
            elif dist <= outer_r:
                grid[ny][nx] = terrain_type
                protected.add((ny, nx))


# Populated after placement function definitions so forward-refs resolve correctly.
STRUCTURE_CATALOG: dict[str, Structure] = {
    "shrine":          Structure("shrine",          5, 5, _place_shrine,          1),
    "mushroom_grove":  Structure("mushroom_grove",  6, 5, _place_mushroom_grove,  2),
    "overgrown_room":  Structure("overgrown_room",  5, 5, _place_overgrown_room,  2),
    "ruined_hall":     Structure("ruined_hall",     7, 5, _place_ruined_hall,     1),
    "frozen_pond":     Structure("frozen_pond",     7, 6, _place_frozen_pond,     1),
    "campsite":        Structure("campsite",        5, 5, _place_campsite,        1),
    "poison_marsh":    Structure("poison_marsh",    6, 5, _place_poison_marsh,    2),
    "standing_stones": Structure("standing_stones", 7, 7, _place_standing_stones, 1),
}


# --------------------------------------------------------- corridor / door helpers

def _mouths_of(grid, room: Room, w: int, h: int) -> list[tuple[int, int]]:
    mouths = []
    interior = set(room.interior())
    for y in range(room.y - 1, room.y + room.h + 1):
        for x in range(room.x - 1, room.x + room.w + 1):
            if not (0 <= y < h and 0 <= x < w) or (y, x) in interior:
                continue
            if grid[y][x] in (T.DOOR_CLOSED, T.FLOOR, T.DOOR_OPEN):
                if any((y + dy, x + dx) in interior for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1))):
                    mouths.append((y, x))
    return mouths
