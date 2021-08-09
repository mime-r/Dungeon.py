# Standard Lib Imports
import datetime
import os
import sys
import time
import operator
import traceback

# Lib Imports
import keyboard
from tinydb import TinyDB, Query
from pandas import *
from termcolor import colored as color
from rich.console import Console
from rich.theme import Theme

# App Imports
from Application.classes.get import get
from Application.classes.weapons import weapons
from Application.classes.people import people
from Application.classes.enemies import orc
from Application.config import config
from Application.maze import Maze
from Application.loggers import LogType

import random
print("Loading...")
chemist = people().chemist

class Dungeon:
    def __init__(self, logger):

        # instantiate logger
        self.logger = logger
        self.log_info = lambda info: self.logger.log(LogType.INFO, info)
        self.log_debug = lambda debug: self.logger.log(LogType.DEBUG, debug)
        self.log_fatal = lambda fatal: self.logger.log(LogType.FATAL, fatal)
        self.log_info("logging functions set up is done")

        #sets console size and clears console
        os.system("mode 100, 38 && cls")
        self.log_info("resized console & cleared")

        # Set up rich styles
        self.rich_console = Console(
            theme=Theme(config.styles)
        )
        self.log_info("rich console & styles set up")

        # Empty tile
        self.current_loc = []

        # Game vars init
        self.moves = 1
        self.firsttime = True
        self.start_time = time.time()

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

        # init weapons
        # name, base attack, startrandom, endrandom, chanceofhit, hittextsucessful, hittextweak, hittextmiss
        self.equipped = weapons().give("default")

        # Fill inventory with starter potions
        for i in range(2):
            self.inventory.append(get().get("potions", "weak healing potion"))

        self.log_info("init dungeon variables")
        
        # generate unique session id for highscore leaderboard
        while True:
            self.session_id = random.getrandbits(10000)
            if len(self.leaderboard.search(self.leaderboardQuery.session_id == self.session_id)) == 0:  # check for repeating
                break
        self.log_info("generated session id")

        self.generate_map()
        self.log_info("generated map")
        self.print_map()
        self.log_debug(f"Raw Map String:\n{self.base_map_str}")

    def generate_map(self):
        '''
        generates the game map
        '''
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
        self.log_info("generated base map string")

        #self.matrix = [[[config.symbols.empty, 0, []] for x in range(config.map.width)] for y in range(config.map.height)]

        # Fill map (Bad Orcs)
        for count in range(config.count.orc):
            found = False
            while not found:
                x, y = random.randint(1, config.map.width-2), random.randint(1, config.map.height-2)
                if self.matrix[x][y][0] != config.symbols.wall:
                    self.matrix[x][y] = [config.symbols.orc, 0, []]
                    found = True
        self.log_info("filled map with orcs")

        # Fill map (chemists)
        for count in range(config.count.chemist):
            found = False
            while not found:
                x, y = random.randint(1, config.map.width-2), random.randint(1, config.map.height-2)
                if not self.matrix[x][y][0] == config.symbols.wall:
                    self.matrix[x][y] = [
                        config.symbols.chemist, 0, [people().chemist()]]
                    found = True
        self.log_info("filled map with chemists")

        # Scatter potions
        for count in range(config.count.floor_potions):
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
        self.log_info("filled map with potions")

        # init player
        found = False
        while not found:
            x, y = random.randint(0, config.map.width-1), random.randint(0, config.map.height-1)
            if not self.matrix[x][y][0] == config.symbols.wall:
                self.matrix[x][y] = [config.symbols.player, 1, self.matrix[x][y]]
                found = True
        self.current_loc = [x, y]

        self.name = input("Hello adventurer, what is your name? (Enter for random name)\n> ")
        if not self.name:
            self.name = people().generate_name()
            print("Your name is: {}".format(self.name))
        self.deactivate_seen_tiles()
        self.log_info("initiated player")

        # init target
        found = False
        while not found:
            x, y = random.randint(1, config.map.width-2), random.randint(1, config.map.height-2)
            if self.matrix[x][y][0] != config.symbols.wall:
                """
                to maintain at least a solid 13 distance between goal and player
                """
                # if abs(x-self.current_loc[0])+abs(y-self.current_loc[1]) > 13:
                if abs(x-self.current_loc[0])+abs(y-self.current_loc[1]) > config.map.min_distance:
                    #self.matrix[x][y] = [config.symbols.target, 0, self.matrix[x][y]]
                    self.matrix[x][y] = [config.symbols.target, 0]
                    found = True

        self.log_info("put target on map")
        
        base_map = []
        index = -1
        for row in self.matrix:
            base_map.append([])
            index += 1
            for cell in row:
                if cell[0] != config.symbols.empty:
                    base_map[index].append(cell[0])
                elif len(cell[2]) > 0 and isinstance(cell[2][0], dict):
                    obj_type = cell[2][0]["object"]
                    base_map[index].append({
                        "weapons": config.symbols.weapons,
                        "potions": config.symbols.potions
                    }.get(obj_type))
                else:
                    base_map[index].append(cell[0])
        self.base_map_str = str(DataFrame(base_map)).replace(config.symbols.unknown, ' ')

    def event(self):
        time.sleep(0.1)  # Time Lag
        self.moves += 1
        # print("\n"*100) # comment thi to make it smoother, unless your pc does not support cls
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
            os.system('cls')
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
            self.rich_console.print(self.orcs.texts.death)
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
                self.rich_console.print(enemy.texts.critical_hit)
            else:
                self.rich_console.print(enemy.texts.hit)
            return (self.health - self.current_attack_damage)
        else:
            self.rich_console.print(enemy.texts.missed_hit)
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
        os.system('cls')
        self.rich_console.print("[Dungeon]", style="game_header", end=" ", highlight=False)
        self.rich_console.print(f"Move: {self.moves}", style="move_count", end=" ", highlight=False)
        self.rich_console.print(f"Health: ({self.health} / {self.max_health})", style="health_count", end=" ", highlight=False)
        self.rich_console.print(f"XP: {self.xp}", style="xp_count", end=" ", highlight=False)
        self.rich_console.print(f"Coins: {self.coins}", style="coin_count", end=" ", highlight=False)
        self.rich_console.print(f"Inventory ({len(self.inventory)} / {self.max_inventory})", style="inventory_count", end=" ", highlight=False)
        self.rich_console.print(f"Time: {(time.time()-self.start_time):.2f}s", style="time_count", highlight=False)
        temp_map = []
        index = -1
        for row in self.matrix:
            temp_map.append([])
            index += 1
            for cell in row:
                if cell[1] == 0:
                    temp_map[index].append(config.symbols.unknown)
                elif cell[1] == 1:
                    # Make enemy hidden
                    if cell[0] in config.symbols.enemies:
                        temp_map[index].append(config.symbols.empty)
                    elif cell[0] != config.symbols.empty:
                        temp_map[index].append(cell[0])
                    elif len(cell[2]) > 0 and isinstance(cell[2][0], dict):
                        obj_type = cell[2][0]["object"]
                        temp_map[index].append({
                            "weapons": config.symbols.weapons,
                            "potions": config.symbols.potions
                        }.get(obj_type))
                    else:
                        temp_map[index].append(cell[0])

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
def main(logger):
    try:
        d = Dungeon(
            logger=logger
        )
        d.log_info("dungeon set up is done")
        d.gameloop()
    except KeyboardInterrupt:
        print("Exiting [Dungeon]...")
        sys.exit()
    except Exception as e:
        logger.log(LogType.FATAL, f"\n{''.join(traceback.format_tb(e.__traceback__))}\n\n{str(e)}")
