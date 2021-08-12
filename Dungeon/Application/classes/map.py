# -*- coding: utf-8 -*-

# Credits: https://github.com/boppreh/maze/blob/master/maze.py
# I edited a lil bit
import random
from ..utils import style_text
from .items import DungeonItem

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
        self.game = game

    def print_inventory(self):
        self.game.rich_print(f"Inventory ({len(self.inventory)} / {self.max_inventory})\n", style="inventory", highlight=False)
        if len(self.inventory) == 0:
            print("You have nothing in your inventory!\n")
        else:
            for index, item in enumerate(self.inventory):
                self.game.rich_print("{0}: {1}\n\t{2}".format(index+1, style_text(item.name, 'item'), item.description))

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
            self.game.rich_print("You see a {} here.".format(constructor))

class Cell(object):
    """
    Class for each individual cell. Knows only its position and which walls are
    still standing.
    """

    def __init__(self, x, y, walls):
        self.x = x
        self.y = y
        self.walls = set(walls)

    def __repr__(self):
        # <15, 25 (es  )>
        return '<{}, {} ({:4})>'.format(self.x, self.y, ''.join(sorted(self.walls)))

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


class Map(object):
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
