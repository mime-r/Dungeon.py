# Standard Lib Imports
import datetime
import os
import sys
import time
import operator

# Lib Imports
import keyboard
import fuckit
from tinydb import TinyDB, Query
from pandas import *
from termcolor import colored as color

# App Imports
from src.get import get
from src.weapons import weapons
from src.people import people
from src.enemies import orc
from config import config

import random
print("Loading...")


# Game objects

# Get


chemist = people().chemist


class Dungeon:
    def __init__(self):
        #sets console size and clears console
        os.system("mode 100, 38 && cls")

        # Set up rich styles
        from rich.console import Console
        from rich.theme import Theme
        self.rich_console = Console(
            theme=Theme(config.styles)
        )

        # Game Map [Start]


        # Empty tile
        self.current_loc = []

        # Game vars init
        self.moves = 1
        self.firsttime = True

        # Init Player Stat Vars
        self.inventory = []
        self.max_inventory = config.player.max_inventory
        self.health = config.player.health
        self.max_health = config.player.max_health
        self.coins = config.player.coins
        self.xp = config.player.xp

        # Leaderboard
        self.leaderboard = TinyDB("leaderboard.json")
        self.leaderboardQuery = Query()
        
        # generate unique session id for highscore leaderboard
        while True:
            self.session_id = random.getrandbits(10000)
            if len(self.leaderboard.search(self.leaderboardQuery.session_id == self.session_id)) == 0:  # check for repeating
                break

        # init weapons
        # name, base attack, startrandom, endrandom, chanceofhit, hittextsucessful, hittextweak, hittextmiss
        self.equipped = weapons().give("default")

        self.generate_map()
        # Game Map [End]

        # Fill inventory with starter potions
        for i in range(2):
            self.inventory.append(get().get("potions", "weak healing potion"))
        os.system("cls")
        self.start_time = time.time()
        self.print_map()

        # self.leaderboard.truncate()
        # print(DataFrame(self.matrix))

    def generate_map(self):
        '''
        generates the game map
        '''
        from maze import Maze
        m = Maze(int(config.map.width/2), int(config.map.height/2))
        m.randomize()
        self.matrix = []

        skinnyMatrix = m._to_str_matrix()
        for i, row in enumerate(skinnyMatrix):
            self.matrix.append([])
            for n, cell in enumerate(row):
                if cell == "O":
                    self.matrix[i].append([config.symbols.wall, 0, []])
                else:
                    self.matrix[i].append([config.symbols.empty, 0, []])

        #self.matrix = [[[config.symbols.empty, 0, []] for x in range(config.map.width)] for y in range(config.map.height)]

        # Fill map (Bad Orcs)
        for count in range(config.count.orc):
            found = False
            while not found:
                x, y = random.randint(1, config.map.width-2), random.randint(1, config.map.height-2)
                if self.matrix[x][y][0] != config.symbols.wall:
                    self.matrix[x][y] = [config.symbols.orc, 0, []]
                    found = True

        # Fill map (chemists)
        for count in range(config.count.chemist):
            found = False
            while not found:
                x, y = random.randint(1, config.map.width-2), random.randint(1, config.map.height-2)
                if not self.matrix[x][y][0] == config.symbols.wall:
                    self.matrix[x][y] = [
                        config.symbols.chemist, 0, [people().chemist()]]
                    found = True

        # Scatter potions
        self.count_floor_potions = 6
        for count in range(config.count.chemist):
            found = False
            while not found:
                x, y = random.randint(1, config.map.width-2), random.randint(1, config.map.height-2)
                if not self.matrix[x][y][0] == config.symbols.wall:
                    rc_num = random.randint(0, 6)
                    if rc_num < 3:
                        chosen_potion = get().get("potions", "weak healing potion")
                    elif rc_num < 6:
                        chosen_potion = get().get("potions", "medium healing potion")
                    else:
                        chosen_potion = get().get("potions", "strong healing potion")
                    self.matrix[x][y][2].append(chosen_potion)
                    found = True

        # init player
        self.init_player(1)

        # init target
        found = False
        while not found:
            x, y = random.randint(1, config.map.width-2), random.randint(1, config.map.height-2)
            if self.matrix[x][y][0] != config.symbols.wall:
                """
                to maintain at least a solid 13 distance between goal and player
                """
                # if abs(x-self.current_loc[0])+abs(y-self.current_loc[1]) > 13:
                if abs(x-self.current_loc[0])+abs(y-self.current_loc[1]) > 13:
                    #self.matrix[x][y] = [config.symbols.target, 0, self.matrix[x][y]]
                    self.matrix[x][y] = [config.symbols.target, 0]
                    found = True

    def event(self):
        time.sleep(0.1)  # Time Lag
        self.moves += 1
        # print("\n"*100) # comment thi to make it smoother, unless your pc does not support cls
        os.system("cls")
        self.print_map()
        self.check()

    def check(self):
        self.playerontile_type = self.matrix[self.current_loc[0]
                                             ][self.current_loc[1]][2][0]
        # print(self.playerontile_type)
        if self.playerontile_type == config.symbols.target:
            self.game_over("exit")
        if self.playerontile_type == config.symbols.orc:
            self.attack("orc")
        if self.playerontile_type == config.symbols.chemist:
            thechemist = self.matrix[self.current_loc[0]
                                     ][self.current_loc[1]][2][2][0]
            self.trader_screen("chemist", thechemist)
        # inv list
        self.playerontile_inv = self.matrix[self.current_loc[0]
                                            ][self.current_loc[1]][2][2]
        if len(self.playerontile_inv) > 0:
            self.print_tile_inv()

    def print_tile_inv(self):
        constructor = ""
        # print(self.playerontile_inv)
        # time.sleep(1)
        if len(self.playerontile_inv) == 1:
            constructor = self.playerontile_inv[0]
        elif len(self.playerontile_inv) > 1:
            # Credits: https://stackoverflow.com/questions/32008737/how-to-efficiently-join-a-list-with-commas-and-add-and-before-the-last-element
            constructor = '{} and {}'.format(
                ', '.join(self.playerontile_inv[:-1]), self.playerontile_inv[-1])
        if not self.playerontile_type == config.symbols.chemist:
            print("You see a {} here.".format(constructor["name"]))

    def print_leaderboard(self):
        self.leaderboard.insert({
            "name": self.name,
            "time": round(time.time() - self.start_time, 3),
            "moves": self.moves,
            "datetime": str(datetime.datetime.now()),
            "sessionid": self.session_id
        })
        self.leaderboardList = self.leaderboard.all()

        self.leaderboardList.sort(key=operator.itemgetter('time'))
        print(color("[Leaderboard]\n", "magenta"))
        for i, element in enumerate(self.leaderboardList):
            self.prefix_text = ""
            if element["sessionid"] == self.session_id:  # show current game score
                self.prefix_text = color("< This Game > ", "green")
            print("{the_prefix}{index}: [{name}]\n\tTime: {time}\n\tMoves: {moves}\n\tDate and Time: {datetime}".format(
                the_prefix=self.prefix_text, index=str(i+1), name=element["name"], time=element["time"], moves=element["moves"], datetime=element["datetime"]))

    def game_over(self, how):
        if how == "exit":
            self.rich_console.print(r"You have [success]successfully[/success] escaped the [game_header][DUNGEON][/game_header]", highlight=False)
            self.print_leaderboard()
        elif how == "dead":
            self.rich_console.print(r"You have [fail]failed[/fail] to escape the [game_header][DUNGEON][/game_header], you'll do better next time.", highlight=False)
        self.rich_console.input(r"[controls][Enter][/controls] to [action]exit[/action]")
        sys.exit()

    def trader_screen(self, typeofperson, obj):
        print("You have met a {0}, a {1}!".format(obj.name, typeofperson))
        time.sleep(1)
        self.traders = obj
        os.system("cls")
        print("{0} - {1}".format(color(obj.name, "magenta"),
              color(typeofperson.title(), "green")))
        for index, item in enumerate(self.traders.stuff):
            print("{0}: {1} {2}".format(
                index+1, item["name"].title(), color("[{}]".format(item["cost"]), "magenta")))
            print(color("\t {}".format(item["description"])))
        self.print_inventory()
        print(color("Press [e] to exit.", "magenta"))

        while True:
            try:
                pressed = keyboard.read_key()
                if pressed.isdigit():
                    pressed = int(pressed)
                    if self.coins >= self.traders.stuff[pressed-1]["cost"]:
                        if len(self.inventory) == self.max_inventory:
                            print("Your inventory is full.")
                        else:
                            print("You have bought the {}".format(
                                self.traders.stuff[pressed-1]["name"].title()))
                            self.inventory.append(
                                self.traders.stuff[pressed-1])
                            self.print_inventory()
                    else:
                        print("You do not have enough money to buy the {}.".format(
                            self.traders.stuff[pressed-1]["name"].title()))
                    time.sleep(0.3)
                if pressed == "e":
                    os.system("cls")
                    self.print_map()
                    self.gameloop()
            except IndexError:
                print("You have chosen an invalid choice.")
                time.sleep(0.5)

    def attack(self, enemy_type):  # He protecc he attacc he also like to snacc
        if enemy_type == "orc":
            print("You have met an orc!")
            self.orcs = orc()
            time.sleep(1)
            os.system("cls")
            print(color("Enemy: ", "red") + color(self.orcs.name, "green"))
            print("{0}: Health - {1}".format(self.orcs.name, self.orcs.health))
            print("You: Health - {0}\n".format(self.health))
            print(color("Press [a] to attack.", "green"))
            while self.orcs.health > 0:
                if keyboard.is_pressed("a"):
                    self.orcs.health = self.hit(self.orcs)
                    print(
                        "{0}: Health - {1}".format(self.orcs.name, self.orcs.health))
                    print("You: Health - {0}\n".format(self.health))
                    if self.orcs.health <= 0:
                        break
                    self.health = self.enemy_hit(self.orcs)
                    print(
                        "\n{0}: Health - {1}".format(self.orcs.name, self.orcs.health))
                    print("You: Health - {0}\n".format(self.health))
                    time.sleep(0.15)
                    if self.health <= 0:
                        self.game_over("dead")
            self.xp += self.orcs.xp_gained
            print(self.orcs.texts[3].format(self.orcs.name))
            self.matrix[self.current_loc[0]][self.current_loc[1]][2] = [
                config.symbols.empty, 1, []]

            # print(self.matrix[self.current_loc[0]][self.current_loc[1]])

            print(color("The {0} drops {1} coins.".format(
                self.orcs.name, self.orcs.coins), "yellow"))
            self.coins += self.orcs.coins
            time.sleep(1.5)
            os.system("cls")
            self.print_map()
            self.gameloop()

    def enemy_hit(self, enemy):
        if not random.randint(1, 100) < enemy.percentage:
            self.current_attack_damage = enemy.attack_base + \
                random.randint(enemy.attack_range[0], enemy.attack_range[1])
            if self.current_attack_damage == enemy.attack_base + enemy.attack_range[1]:
                # Max Damage
                print(enemy.texts[0].format(enemy.name))
            else:
                print(enemy.texts[1].format(enemy.name))
            return (self.health - self.current_attack_damage)
        else:
            print(enemy.texts[2].format(enemy.name))
            return self.health

    def hit(self, enemy):
        if not random.randint(1, 100) < self.equipped["chance-of-hit"]:
            self.current_attack_damage = self.equipped["base-attack"] + random.randint(
                self.equipped["random-attack"][0], self.equipped["random-attack"][1])
            if self.current_attack_damage == self.equipped["base-attack"] + self.equipped["random-attack"][1]:
                # Max Damage
                print(
                    self.equipped["text-critical"].format(self.equipped["name"]))
            else:
                print(
                    self.equipped["text-normal"].format(enemy.name, self.equipped["name"]))
            return (enemy.health - self.current_attack_damage)
        else:
            print(self.equipped["text-miss"].format(enemy.name))
            return enemy.health

    def gameloop(self):
        self.inventoryscreen = False
        while True:
            if keyboard.is_pressed("right"):
                self.player_move("e")
                self.event()
            elif keyboard.is_pressed("left"):
                self.player_move("w")
                self.event()
            elif keyboard.is_pressed("up"):
                self.player_move("n")
                self.event()
            elif keyboard.is_pressed("down"):
                self.player_move("s")
                self.event()
            elif keyboard.is_pressed("esc"):
                print("Exiting [Dungeon]...")
                sys.exit()
            elif keyboard.is_pressed("u"):
                self.equip_menu()
            elif keyboard.is_pressed("d"):
                self.drop_menu()
            elif not self.inventoryscreen:
                if keyboard.is_pressed("i"):
                    self.inventoryscreen = True
                    self.print_inventory_wrapper()

    def equip_menu(self):
        os.system("cls")
        print(color("Use/Equip Menu", "green"))
        self.print_inventory()
        print(color("Press [e] to exit.", "magenta"))
        while True:
            try:
                pressed = keyboard.read_key()
                if pressed.isnumeric():
                    pressed = int(pressed)
                    self.to_use = self.inventory[pressed-1]
                    if self.to_use["type"] == "bag":
                        print("You sling the {} over your shoulders.".format(
                            self.to_use["name"]))
                        del self.inventory[pressed-1]
                        self.max_inventory += 4
                    elif self.to_use["type"] == "health-potion":
                        if self.health == self.max_health:
                            print(
                                "You are already at maximum health. Try drinking a maximum-health increasing potion.")
                        else:
                            if (self.health + self.to_use["increase-health-by"]) > self.max_health:
                                self.health = self.max_health
                            else:
                                self.health += self.to_use["increase-health-by"]
                            print("You drink the {}. The strong elixir makes you feel rejuvenated.\n".format(
                                self.to_use["name"]))
                            del self.inventory[pressed-1]

                    time.sleep(0.2)
                    self.print_inventory()
                if pressed == "e":
                    os.system("cls")
                    self.print_map()
                    self.gameloop()
            except IndexError:
                print("You have chosen an invalid choice.")
                time.sleep(0.5)

    def drop_menu(self):
        os.system("cls")
        print(color("Drop Menu", "green"))
        self.print_inventory()
        print(color("Press [e] to exit.", "magenta"))
        while True:
            try:
                pressed = keyboard.read_key()
                if pressed.isnumeric():
                    pressed = int(pressed)
                    self.to_use = self.inventory[pressed-1]
                    print("Do you want to drop the {0}?\n{1}".format(self.to_use["name"].title(
                    ), color("Press [y] for Yes and [n] for No.", "magenta")))
                    while True:
                        if keyboard.is_pressed("y"):
                            del self.inventory[pressed-1]

                            print("You have dropped the {}!".format(
                                self.to_use["name"].title()))
                            break
                        elif keyboard.is_pressed("n"):
                            print("You do not drop the {}.".format(
                                self.to_use["name"].title()))
                            break
                    time.sleep(0.2)
                    self.print_inventory()
                if pressed == "e":
                    os.system("cls")
                    self.print_map()
                    self.gameloop()
            except IndexError:
                print("You have chosen an invalid choice.")
                time.sleep(0.5)

    def print_inventory(self):
        print(color(
            "Inventory ({0} / {1})".format(len(self.inventory), self.max_inventory), "green"))
        if len(self.inventory) == 0:
            print("You have nothing in your inventory!")
        else:
            for index, item in enumerate(self.inventory):
                print("{0}: {1}\n\t{2}".format(
                    index+1, item["name"].title(), item["description"]))

    def print_inventory_wrapper(self, *args):
        os.system("cls")
        self.print_inventory()
        print(color("Press [e] to exit.", "magenta"))
        # time.sleep(0.5)
        while True:
            if keyboard.is_pressed("e"):
                break
        os.system("cls")
        self.print_map()
        self.gameloop()

    @fuckit
    def player_move(self, direction):
        if direction == "e":
            if self.current_loc[1] < (config.map.width-1):
                if self.matrix[self.current_loc[0]][self.current_loc[1]+1][0] != config.symbols.wall:
                    self.matrix[self.current_loc[0]][self.current_loc[1]
                                                     ] = self.matrix[self.current_loc[0]][self.current_loc[1]][2]
                    self.matrix[self.current_loc[0]][self.current_loc[1]+1] = [config.symbols.player,
                                                                               1, self.matrix[self.current_loc[0]][self.current_loc[1]+1]]
                    self.current_loc = [
                        self.current_loc[0], self.current_loc[1]+1]
        if direction == "w":
            if self.current_loc[1] > 0:
                if self.matrix[self.current_loc[0]][self.current_loc[1]-1][0] != config.symbols.wall:
                    self.matrix[self.current_loc[0]][self.current_loc[1]
                                                     ] = self.matrix[self.current_loc[0]][self.current_loc[1]][2]
                    self.matrix[self.current_loc[0]][self.current_loc[1]-1] = [config.symbols.player,
                                                                               1, self.matrix[self.current_loc[0]][self.current_loc[1]-1]]
                    self.current_loc = [
                        self.current_loc[0], self.current_loc[1]-1]
        if direction == "n":
            if self.current_loc[0] > 0:
                if self.matrix[self.current_loc[0]-1][self.current_loc[1]][0] != config.symbols.wall:
                    self.matrix[self.current_loc[0]][self.current_loc[1]
                                                     ] = self.matrix[self.current_loc[0]][self.current_loc[1]][2]
                    self.matrix[self.current_loc[0]-1][self.current_loc[1]] = [config.symbols.player,
                                                                               1, self.matrix[self.current_loc[0]-1][self.current_loc[1]]]
                    self.current_loc = [
                        self.current_loc[0]-1, self.current_loc[1]]
        if direction == "s":
            if self.current_loc[0] < (config.map.height-1):
                if self.matrix[self.current_loc[0]+1][self.current_loc[1]][0] != config.symbols.wall:
                    self.matrix[self.current_loc[0]][self.current_loc[1]
                                                     ] = self.matrix[self.current_loc[0]][self.current_loc[1]][2]
                    self.matrix[self.current_loc[0]+1][self.current_loc[1]] = [config.symbols.player,
                                                                               1, self.matrix[self.current_loc[0]+1][self.current_loc[1]]]
                    self.current_loc = [
                        self.current_loc[0]+1, self.current_loc[1]]
        self.deactivate_seen_tiles()

    def print_map(self):
        self.rich_console.print("[Dungeon]", style="game_header", end=" ", highlight=False)
        self.rich_console.print(f"Move: {self.moves}", style="move_count", end=" ", highlight=False)
        self.rich_console.print(f"Health: ({self.health} / {self.max_health})", style="health_count", end=" ", highlight=False)
        self.rich_console.print(f"XP: {self.xp}", style="xp_count", end=" ", highlight=False)
        self.rich_console.print(f"Coins: {self.coins}", style="coin_count", end=" ", highlight=False)
        self.rich_console.print(f"Inventory ({len(self.inventory)} / {self.max_inventory})", style="inventory_count", end=" ", highlight=False)
        self.rich_console.print(f"Time: {(time.time()-self.start_time):.2f}s", style="time_count", highlight=False)
        self.Map = []
        index = -1
        for row in self.matrix:
            self.Map.append([])
            index += 1
            for cell in row:
                if len(cell) < 4:
                    if cell[1] == 0:
                        self.Map[index].append("⠀")
                    elif cell[1] == 1:
                        # Make enemy hidden
                        if cell[0] in config.symbols.enemies:
                            self.Map[index].append(config.symbols.empty)
                        else:
                            self.Map[index].append(cell[0])
                            continue
                        # Display item inv
                        # TYPES OF OBJECTS
                        if cell[0] == config.symbols.player:  # if scanning player
                            # print(cell[2])
                            temp_cell = cell[2][2]
                        else:
                            temp_cell = cell[2]
                        if len(temp_cell) > 0:  # cell[2][0] is obj
                            get_obj = temp_cell[0]["object"]
                            if get_obj == "weapons":
                                self.Map[index].append("\\")
                            elif get_obj == "potions":
                                self.Map[index].append("!")
                else:
                    # Assume Player is there
                    self.Map[index].append(cell[0])

        map_str = str(DataFrame(self.Map))
        styling = [
            ("⠀", "unknown"),
            (config.symbols.wall, "wall"),
            (config.symbols.chemist, "chemist"),
            (config.symbols.player, "player"),
            (config.symbols.target, "target")
        ]
        for symbol, style in styling:
            map_str = map_str.replace(symbol, f"[{style}]{symbol}[/{style}]")
        for num in "0123456789":
            map_str = map_str.replace(num, f"[grid_num]{num}[/grid_num]")
        self.rich_console.print(map_str, highlight=False)
        self.rich_console.print(r"""
Press [controls]\[arrow keys][/controls] to [action]move[/action].
Press [controls]\[i][/controls] for [action]inventory[/action].
Press [controls]\[esc][/controls] to [action]exit[/action].
Press [controls]\[u][/controls] to [action]equip/use items[/action].
Press [controls]\[d][/controls] to [action]drop items[/action].
""", highlight=False)

    def init_player(self, state):

        if state == 1:
            found = False
            while not found:
                global x, y
                x, y = random.randint(0, config.map.width-1), random.randint(0, config.map.height-1)
                if not self.matrix[x][y][0] == config.symbols.wall:
                    self.matrix[x][y] = [config.symbols.player, 1, self.matrix[x][y]]
                    found = True
            self.current_loc = [x, y]

            self.name = input(
                "Hello adventurer, what is your name? (Enter for random name)\n> ")

            if not self.name:
                self.name = people().generate_name()
                print("Your name is: {}".format(self.name))
            time.sleep(1)
        self.deactivate_seen_tiles()

    # @fuckit
    def deactivate_seen_tiles(self):
        self.matrix[self.current_loc[0] -
                    1][self.current_loc[1]-1][1] = 1  # North West
        self.matrix[self.current_loc[0] +
                    1][self.current_loc[1]-1][1] = 1  # South West
        self.matrix[self.current_loc[0]][self.current_loc[1]-1][1] = 1  # West
        self.matrix[self.current_loc[0] -
                    1][self.current_loc[1]+1][1] = 1  # North East
        self.matrix[self.current_loc[0] +
                    1][self.current_loc[1]+1][1] = 1  # South East
        self.matrix[self.current_loc[0]][self.current_loc[1]+1][1] = 1  # East
        self.matrix[self.current_loc[0]-1][self.current_loc[1]][1] = 1  # North
        self.matrix[self.current_loc[0]+1][self.current_loc[1]][1] = 1  # South
        """
        # Prevent Border Sneak-peaking
        if not self.current_loc[1] == 0:
            if not self.current_loc[0] == 0:
                self.matrix[self.current_loc[0]-1][self.current_loc[1]-1][1] = 1 # North West
            if not self.current_loc[1] == (config.map.height - 1):
                self.matrix[self.current_loc[0]+1][self.current_loc[1]-1][1] = 1 # South West
            self.matrix[self.current_loc[0]][self.current_loc[1]-1][1] = 1 # West
        if not self.current_loc[1] == (config.map.width):
            if not self.current_loc[0] == 0:
                self.matrix[self.current_loc[0]-1][self.current_loc[1]+1][1] = 1 # North East
            if not self.current_loc[1] == (config.map.height - 1): ###
                self.matrix[self.current_loc[0]+1][self.current_loc[1]+1][1] = 1 # South East
            self.matrix[self.current_loc[0]][self.current_loc[1]+1][1] = 1 # East
        if not self.current_loc[0] == 0:
            self.matrix[self.current_loc[0]-1][self.current_loc[1]][1] = 1 # North
        if not self.current_loc[1] == (config.map.height - 1):
            self.matrix[self.current_loc[0]+1][self.current_loc[1]][1] = 1 # South
        """


# if __name__ == "__main__":
try:
    d = Dungeon()
    d.gameloop()
except KeyboardInterrupt:
    print("Exiting [Dungeon]...")
    sys.exit()
