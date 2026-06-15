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


# ------------------------------------------------------------------ dispatcher

def generate_level(is_last: bool = False, depth: int = 1) -> LevelLayout:
    """Pick a random generator and produce one floor.

    Deeper floors are more likely to use complex layouts and are slightly larger.
    """
    w = random.randint(config.map.min_width, config.map.max_width)
    h = random.randint(config.map.min_height, config.map.max_height)

    weights = {"rooms": 40, "cave": 30, "bsp": 30}
    choice = random.choices(list(weights.keys()), weights=list(weights.values()), k=1)[0]

    if choice == "cave":
        return _generate_cave(w, h, is_last)
    if choice == "bsp":
        return _generate_bsp(w, h, is_last)
    return _generate_rooms(w, h, is_last)


# ------------------------------------------------------------ rooms & corridors

def _generate_rooms(w: int, h: int, is_last: bool) -> LevelLayout:
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
    _place_stairs_and_vault(layout, grid, rooms, interior_floor, is_last, w, h)
    return layout


# ---------------------------------------------------------- cellular automata

def _generate_cave(w: int, h: int, is_last: bool) -> LevelLayout:
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
    _build_floor_cells(layout, grid, w, h)
    return layout


# ------------------------------------------------------ binary space partition

class _BSPNode:
    def __init__(self, x: int, y: int, w: int, h: int) -> None:
        self.x, self.y, self.w, self.h = x, y, w, h
        self.left: _BSPNode | None = None
        self.right: _BSPNode | None = None
        self.room: Room | None = None


def _generate_bsp(w: int, h: int, is_last: bool) -> LevelLayout:
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
    _place_stairs_and_vault(layout, grid, rooms, interior_floor, is_last, w, h)
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

def _place_stairs_and_vault(layout, grid, rooms, interior_floor, is_last, w, h) -> None:
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


def _build_floor_cells(layout, grid, w, h) -> None:
    reserved = set(layout.vault_cells) | set(layout.temple_cells)
    if layout.altar:
        reserved.add(layout.altar)
    occupied = {layout.stairs_up, layout.stairs_down}
    for y in range(h):
        for x in range(w):
            if grid[y][x] == T.FLOOR and (y, x) not in reserved and (y, x) not in occupied:
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
