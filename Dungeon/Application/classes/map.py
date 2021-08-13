# -*- coding: utf-8 -*-

# Credits: https://github.com/boppreh/maze/blob/master/maze.py
# I edited a lil bit
import random
import os
import time
from ..utils import style_text, controls_style
from ..config import config
from .items import DungeonItem, DungeonWeapon, DungeonPotion
from pandas import DataFrame

# Easy to read representation for each cardinal direction.
N, S, W, E = ('n', 's', 'w', 'e')

class DungeonPlayer:
    def __init__(self, health, max_health, max_inventory, coins, xp, equipped, game):
        self.health = health
        self.max_health = max_health
        self.xp = xp
        self.coins = coins
        self.inventory = []
        self.max_inventory = max_inventory
        self.equipped = equipped
        self.location = (0, 0)
        self.name = None
        self.game = game

    @property
    def x(self):
        return self.location[1]

    @property
    def y(self):
        return self.location[0]

    def print_inventory(self):
        self.game.print(f"Inventory ({len(self.inventory)} / {self.max_inventory})", style="inventory", highlight=False)
        self.game.print(f"Health: ({self.health} / {self.max_health})", style="health", highlight=False)
        self.game.print(f"Coins: {self.coins}\n", style="coin", highlight=False)
        if len(self.inventory) == 0:
            print("You have nothing in your inventory!\n")
        else:
            for index, item in enumerate(self.inventory):
                self.game.print("{0}: {1}\n\t{2}".format(index+1, style_text(item.name, 'item'), item.description))

    def move(self, direction):
        y, x = self.location
        condition, new_y, new_x = {
            "e": ((x < (config.map.max_x)), y, x+1),
            "w": ((x > 0), y, x-1),
            "n": ((y > 0), y-1, x),
            "s": ((y < (config.map.max_y)), y+1, x)
        }.get(direction)
        if condition:
            if self.game.map.matrix[new_y][new_x].symbol != config.symbols.wall:
                self.game.map.matrix[y][x] = self.game.map.matrix[y][x].inventory
                self.game.map.matrix[new_y][new_x] = DungeonCell(
                    symbol=config.symbols.player,
                    game=self,
                    explored=True,
                    inventory=self.game.map.matrix[new_y][new_x]
                )

                self.location = (new_y, new_x)
        self.game.log.info(f"moved {direction}")
        self.game.map.update_adjacent_cells()
        self.game.event()

class DungeonCell:
    def __init__(self, symbol, game, explored=False, inventory=None):
        self.symbol = symbol
        self.explored = explored
        self.inventory = inventory if inventory else []
        self.game = game

    def print_inventory(self):
        if len(self.inventory) > 0 and isinstance(self.inventory[0], DungeonItem):
            inventory = list(filter(
                lambda x: isinstance(x, DungeonItem),
                self.inventory
            ))
            constructor = ""
            if len(inventory) == 1:
                constructor = style_text(inventory[0].name, 'item')
            elif len(inventory) > 1:
                constructor = '{} and {}'.format(
                    ', '.join(map(
                        lambda item: style_text(item.name, 'item'),
                        inventory[:-1])
                    ),
                    style_text(inventory[-1].name, 'item')
                )
            self.game.print("You see a {} here.".format(constructor))

class DungeonMap:
    def __init__(self, game):
        self.game = game
        self.matrix = []

        for i, row in enumerate(GeneratedMap(int(config.map.width/2), int(config.map.height/2))._to_str_matrix()):
            self.matrix.append([])
            for n, cell in enumerate(row):
                if cell == "O":
                    self.matrix[i].append(DungeonCell(symbol=config.symbols.wall, game=self.game))
                else:
                    self.matrix[i].append(DungeonCell(symbol=config.symbols.empty, game=self.game))

    def get_debug_map(self):
        base_map = []
        index = -1
        for row in self.matrix:
            base_map.append([])
            index += 1
            for cell in row:
                if cell.symbol != config.symbols.empty:
                    base_map[index].append(cell.symbol)
                elif len(cell.inventory) > 0 and isinstance(cell.inventory[0], DungeonItem):
                    obj_type = type(cell.inventory[0])
                    base_map[index].append({
                        DungeonWeapon: config.symbols.weapons,
                        DungeonPotion: config.symbols.potions
                    }.get(obj_type))
                else:
                    base_map[index].append(cell.symbol)
        return str(DataFrame(base_map)).replace(config.symbols.unknown, ' ')

    def print(self):
        os.system('cls')
        self.game.print("[Dungeon]", style="game_header", end=" ", highlight=False)
        self.game.print(f"Move: {self.game.moves}", style="move_count", end=" ", highlight=False)
        self.game.print(f"Health: ({self.game.player.health} / {self.game.player.max_health})", style="health", end=" ", highlight=False)
        self.game.print(f"XP: {self.game.player.xp}", style="xp_count", end=" ", highlight=False)
        self.game.print(f"Coins: {self.game.player.coins}", style="coin", end=" ", highlight=False)
        self.game.print(f"Inventory ({len(self.game.player.inventory)} / {self.game.player.max_inventory})", style="inventory", end=" ", highlight=False)
        self.game.print(f"Time: {(time.time()-self.game.start_time):.2f}s", style="time_count", highlight=False)
        temp_map = []
        index = -1
        for row in self.matrix:
            temp_map.append([])
            index += 1
            for cell in row:
                if cell.explored == False:
                    temp_map[index].append(config.symbols.unknown)
                else:
                    # Make enemy hidden
                    if cell.symbol != config.symbols.empty and cell.symbol not in config.symbols.enemies:
                        temp_map[index].append(cell.symbol)
                    elif len(cell.inventory) > 0 and isinstance(cell.inventory[0], DungeonItem):
                        obj_type = type(cell.inventory[0])
                        temp_map[index].append({
                            "weapons": config.symbols.weapons,
                            DungeonPotion: config.symbols.potions
                        }.get(obj_type))
                    else:
                        temp_map[index].append(config.symbols.empty)

        map_str = str(DataFrame(temp_map))
        styling = [
            (config.symbols.unknown, "unknown"),
            (config.symbols.wall, "wall"),
            (config.symbols.chemist, "chemist"),
            (config.symbols.player, "player"),
            (config.symbols.target, "target"),
            (config.symbols.empty, "empty"),
            (config.symbols.potions, "potions"),
            (config.symbols.weapons, "weapons")
        ]
        for symbol, style in styling:
            map_str = map_str.replace(symbol, style_text(symbol, style))
        for num in "0123456789":
            map_str = map_str.replace(num, style_text(num, 'grid_num'))
        self.game.print(map_str, highlight=False)
        self.game.print(f"""
Press {controls_style('arrow keys')} to {style_text('move', 'action')}.
Press {controls_style('i')} for {style_text('inventory', 'action')}.
Press {controls_style('esc')} to {style_text('exit', 'action')}.
Press {controls_style('u')} to {style_text('equip/use items', 'action')}.
Press {controls_style('d')} to {style_text('drop items', 'action')}.
""", highlight=False)

    def update_adjacent_cells(self):
        y, x = self.game.player.location
        adjacent_cells = [
            (y-1, x-1), (y-1, x), (y-1, x+1),
            (y, x-1), (y, x), (y, x+1),
            (y+1, x-1), (y+1, x), (y+1, x+1)
        ]
        for y, x in adjacent_cells:
            if (y < 0 or y > config.map.max_y) or (x < 0 or x > config.map.max_x):
                continue
            self.matrix[y][x].explored = True


        """
        # Prevent Border Sneak-peaking
        if not self.player.x == 0:
            if not self.player.y == 0:
                self.map.matrix[self.player.y-1][self.player.x-1][1] = 1 # North West
            if not self.player.x == (config.map.height - 1):
                self.map.matrix[self.player.y+1][self.player.x-1][1] = 1 # South West
            self.map.matrix[self.player.y][self.player.x-1][1] = 1 # West
        if not self.player.x == (config.map.width):
            if not self.player.y == 0:
                self.map.matrix[self.player.y-1][self.player.x+1][1] = 1 # North East
            if not self.player.x == (config.map.height - 1): ###
                self.map.matrix[self.player.y+1][self.player.x+1][1] = 1 # South East
            self.map.matrix[self.player.y][self.player.x+1][1] = 1 # East
        if not self.player.y == 0:
            self.map.matrix[self.player.y-1][self.player.x][1] = 1 # North
        if not self.player.x == (config.map.height - 1):
            self.map.matrix[self.player.y+1][self.player.x][1] = 1 # South
        """

class Cell(object):
    """
    Class for each individual cell. Knows only its position and which walls are
    still standing.
    """

    def __init__(self, x, y, walls):
        self.x = x
        self.y = y
        self.walls = set(walls)

    def __contains__(self, item):
        # N in cell
        return item in self.walls

    def is_full(self):
        """
        Returns True if all walls are still standing.
        """
        return len(self.walls) == 4

    def _wall_to(self, other):
        """
        Returns the direction to the given cell from the current one.
        Must be one cell away only.
        """
        assert abs(self.x - other.x) + abs(self.y -
                                           other.y) == 1, '{}, {}'.format(self, other)
        if other.y < self.y:
            return N
        elif other.y > self.y:
            return S
        elif other.x < self.x:
            return W
        elif other.x > self.x:
            return E
        else:
            assert False

    def connect(self, other):
        """
        Removes the wall between two adjacent cells.
        """
        other.walls.remove(other._wall_to(self))
        self.walls.remove(self._wall_to(other))


class GeneratedMap(object):
    """
    Map class containing full board and maze generation algorithms.
    """

    def __init__(self, width=20, height=10):
        """
        Creates a new maze with the given sizes, with all walls standing.
        """
        self.width = width
        self.height = height
        self.cells = []
        for y in range(self.height):
            for x in range(self.width):
                self.cells.append(Cell(x, y, [N, S, E, W]))

        self.randomize()

    def __getitem__(self, index):
        """
        Returns the cell at index = (x, y).
        """
        x, y = index
        if 0 <= x < self.width and 0 <= y < self.height:
            return self.cells[x + y * self.width]
        else:
            return None

    def neighbors(self, cell):
        """
        Returns the list of neighboring cells, not counting diagonals. Cells on
        borders or corners may have less than 4 neighbors.
        """
        x = cell.x
        y = cell.y
        for new_x, new_y in [(x, y - 1), (x, y + 1), (x - 1, y), (x + 1, y)]:
            neighbor = self[new_x, new_y]
            if neighbor is not None:
                yield neighbor

    def _to_str_matrix(self):
        """
        Returns a matrix with a pretty printed visual representation of this
        maze. Example 5x5:
        OOOOOOOOOOO
        O       O O
        OOO OOO O O
        O O   O   O
        O OOO OOO O
        O   O O   O
        OOO O O OOO
        O   O O O O
        O OOO O O O
        O     O   O
        OOOOOOOOOOO
        """
        str_matrix = [['O'] * (self.width * 2 + 1)
                      for i in range(self.height * 2 + 1)]

        for cell in self.cells:
            x = cell.x * 2 + 1
            y = cell.y * 2 + 1
            str_matrix[y][x] = ' '
            if N not in cell and y > 0:
                str_matrix[y - 1][x + 0] = ' '
            if S not in cell and y + 1 < self.width:
                str_matrix[y + 1][x + 0] = ' '
            if W not in cell and x > 0:
                str_matrix[y][x - 1] = ' '
            if E not in cell and x + 1 < self.width:
                str_matrix[y][x + 1] = ' '

        new_matrix = str_matrix
        for row_index, row in enumerate(str_matrix):
            for element_index, element in enumerate(row):
                if element == "O" and random.randint(1, 2) == 1:
                    new_matrix[row_index][element_index] = " "

        return str_matrix

    def randomize(self):
        """
        Knocks down random walls to build a random perfect maze.
        Algorithm from http://mazeworks.com/mazegen/mazetut/index.htm
        """
        cell_stack = []
        cell = random.choice(self.cells)
        n_visited_cells = 1

        while n_visited_cells < len(self.cells):
            neighbors = [c for c in self.neighbors(cell) if c.is_full()]
            if len(neighbors):
                neighbor = random.choice(neighbors)
                cell.connect(neighbor)
                cell_stack.append(cell)
                cell = neighbor
                n_visited_cells += 1
            else:
                cell = cell_stack.pop()
