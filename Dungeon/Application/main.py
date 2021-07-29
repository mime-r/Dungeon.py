import datetime
import os
import sys
import time
import keyboard
import fuckit
from Application.src.get import get
import operator
from Application.src.weapons import weapons
from Application.src.people import people
from Application.src.enemies import orc
from tinydb import TinyDB, Query
from pandas import *
from termcolor import colored as color
import random
print("Loading...")


# Game objects

# Get


chemist = people().chemist


class Dungeon:
    def __init__(self):
        os.system("cls")

        # Game Map [Start]

        # Orcs
        self.count_orcs = 20
        self.symbol_orcs = "o"

        # Chemists
        self.count_chemists = 5
        self.symbol_chemists = "C"

        # Map Size
        self.w, self.h = 25, 25

        # Empty tile
        self.symbol_empty = "·"
        self.current_loc = []

        # Walls
        self.symbol_walls = "#"

        # Game vars init
        self.moves = 1
        self.firsttime = True

        # All enemy types
        self.enemytypes = ["o"]

        # Player Stats
        self.inventory = []
        self.maxinventory = 3
        self.health = 30
        self.maxhealth = 30
        self.coins = 100
        self.xp = 0

        # Leaderboard
        self.leaderboard = TinyDB("leaderboard.json")
        self.leaderboardQuery = Query()
        # idk seed?
        random.seed()
        """
        Session id for highscore leaderboard.
        """
        while True:
            self.session_id = random.getrandbits(10000)
            if len(self.leaderboard.search(self.leaderboardQuery.session_id == self.session_id)) == 0:  # check for repeating
                break

        # init weapons

        # name, base attack, startrandom, endrandom, chanceofhit, hittextsucessful, hittextweak, hittextmiss
        self.equipped = weapons().give("default")

        # Generate blank map

        from Application.maze import Maze
        m = Maze(int(self.w/2), int(self.h/2))
        m.randomize()
        self.Matrix = []

        skinnyMatrix = m._to_str_matrix()
        for i, row in enumerate(skinnyMatrix):
            self.Matrix.append([])
            for n, cell in enumerate(row):
                if cell == "O":
                    self.Matrix[i].append([self.symbol_walls, 0, []])
                else:
                    self.Matrix[i].append([self.symbol_empty, 0, []])

        #self.Matrix = [[[self.symbol_empty, 0, []] for x in range(self.w)] for y in range(self.h)]

        # Fill map (Bad Orcs)
        for count in range(self.count_orcs):
            found = False
            while not found:
                x, y = random.randint(1, self.w-2), random.randint(1, self.h-2)
                if self.Matrix[x][y][0] != self.symbol_walls:
                    self.Matrix[x][y] = [self.symbol_orcs, 0, []]
                    found = True

        # Fill map (chemists)
        for count in range(self.count_chemists):
            found = False
            while not found:
                x, y = random.randint(1, self.w-2), random.randint(1, self.h-2)
                if not self.Matrix[x][y][0] == "#":
                    self.Matrix[x][y] = [
                        self.symbol_chemists, 0, [people().chemist()]]
                    found = True

        # Scatter potions
        self.count_floor_potions = 6
        for count in range(self.count_chemists):
            found = False
            while not found:
                x, y = random.randint(1, self.w-2), random.randint(1, self.h-2)
                if not self.Matrix[x][y][0] == "#":
                    rc_num = random.randint(0, 6)
                    if rc_num < 3:
                        chosen_potion = get().get("potions", "weak healing potion")
                    elif rc_num < 6:
                        chosen_potion = get().get("potions", "medium healing potion")
                    else:
                        chosen_potion = get().get("potions", "strong healing potion")
                    self.Matrix[x][y][2].append(chosen_potion)
                    found = True

        # init player
        self.player(1)

        # init target

        self.symbol_target = "$"
        found = False
        while not found:
            x, y = random.randint(1, self.w-2), random.randint(1, self.h-2)
            if self.Matrix[x][y][0] != "#":
                """
                to maintain at least a solid 13 distance between goal and player
                """
                # if abs(x-self.current_loc[0])+abs(y-self.current_loc[1]) > 13:
                if abs(x-self.current_loc[0])+abs(y-self.current_loc[1]) > 13:
                    #self.Matrix[x][y] = ["$", 0, self.Matrix[x][y]]
                    self.Matrix[x][y] = ["$", 0]
                    found = True

        # Game Map [End]

        # Fill inventory with starter potions
        for i in range(2):
            self.inventory.append(get().get("potions", "weak healing potion"))
        os.system("cls")
        self.time = time.time()
        self.printmap()

        # self.leaderboard.truncate()
        # print(DataFrame(self.Matrix))

    def event(self):
        time.sleep(0.1)  # Time Lag
        self.moves += 1
        # print("\n"*100) # comment thi to make it smoother, unless your pc does not support cls
        os.system("cls")
        self.printmap()
        self.check()

    def check(self):
        self.playerontile_type = self.Matrix[self.current_loc[0]
                                             ][self.current_loc[1]][2][0]
        # print(self.playerontile_type)
        if self.playerontile_type == self.symbol_target:
            self.gameOver("exit")
        if self.playerontile_type == self.symbol_orcs:
            self.attack("orc")
        if self.playerontile_type == self.symbol_chemists:
            thechemist = self.Matrix[self.current_loc[0]
                                     ][self.current_loc[1]][2][2][0]
            self.traderscreen("chemist", thechemist)
        # inv list
        self.playerontile_inv = self.Matrix[self.current_loc[0]
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
        if not self.playerontile_type == self.symbol_chemists:
            print("You see a {} here.".format(constructor["name"]))

    def printleaderboard(self):
        self.leaderboard.insert({
            "name": self.name,
            "time": round(time.time() - self.time, 3),
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

    def gameOver(self, how):
        if how == "exit":
            print("You have successfully escaped the [DUNGEON]")
            self.printleaderboard()
            sys.exit()
        elif how == "dead":
            print(
                "You have failed to escape the [DUNGEON], you'll do better next time.")
            sys.exit()

    def traderscreen(self, typeofperson, obj):
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
        self.printinventory()
        print(color("Press [e] to exit.", "magenta"))

        while True:
            try:
                pressed = keyboard.read_key()
                if pressed.isdigit():
                    pressed = int(pressed)
                    if self.coins >= self.traders.stuff[pressed-1]["cost"]:
                        if len(self.inventory) == self.maxinventory:
                            print("Your inventory is full.")
                        else:
                            print("You have bought the {}".format(
                                self.traders.stuff[pressed-1]["name"].title()))
                            self.inventory.append(
                                self.traders.stuff[pressed-1])
                            self.printinventory()
                    else:
                        print("You do not have enough money to buy the {}.".format(
                            self.traders.stuff[pressed-1]["name"].title()))
                    time.sleep(0.3)
                if pressed == "e":
                    os.system("cls")
                    self.printmap()
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
                    self.health = self.enemyhit(self.orcs)
                    print(
                        "\n{0}: Health - {1}".format(self.orcs.name, self.orcs.health))
                    print("You: Health - {0}\n".format(self.health))
                    time.sleep(0.15)
                    if self.health <= 0:
                        self.gameOver("dead")
            self.xp += self.orcs.xp_gained
            print(self.orcs.texts[3].format(self.orcs.name))
            self.Matrix[self.current_loc[0]][self.current_loc[1]][2] = [
                self.symbol_empty, 1, []]

            # print(self.Matrix[self.current_loc[0]][self.current_loc[1]])

            print(color("The {0} drops {1} coins.".format(
                self.orcs.name, self.orcs.coins), "yellow"))
            self.coins += self.orcs.coins
            time.sleep(1.5)
            os.system("cls")
            self.printmap()
            self.gameloop()

    def enemyhit(self, enemy):
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
                self.equipmenu()
            elif keyboard.is_pressed("d"):
                self.dropmenu()
            elif not self.inventoryscreen:
                if keyboard.is_pressed("i"):
                    self.inventoryscreen = True
                    self.printinventory_wrapper()

    def equipmenu(self):
        os.system("cls")
        print(color("Use/Equip Menu", "green"))
        self.printinventory()
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
                        self.maxinventory += 4
                    elif self.to_use["type"] == "health-potion":
                        if self.health == self.maxhealth:
                            print(
                                "You are already at maximum health. Try drinking a maximum-health increasing potion.")
                        else:
                            if (self.health + self.to_use["increase-health-by"]) > self.maxhealth:
                                self.health = self.maxhealth
                            else:
                                self.health += self.to_use["increase-health-by"]
                            print("You drink the {}. The strong elixir makes you feel rejuvenated.\n".format(
                                self.to_use["name"]))
                            del self.inventory[pressed-1]

                    time.sleep(0.2)
                    self.printinventory()
                if pressed == "e":
                    os.system("cls")
                    self.printmap()
                    self.gameloop()
            except IndexError:
                print("You have chosen an invalid choice.")
                time.sleep(0.5)

    def dropmenu(self):
        os.system("cls")
        print(color("Drop Menu", "green"))
        self.printinventory()
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
                    self.printinventory()
                if pressed == "e":
                    os.system("cls")
                    self.printmap()
                    self.gameloop()
            except IndexError:
                print("You have chosen an invalid choice.")
                time.sleep(0.5)

    def printinventory(self):
        print(color(
            "Inventory ({0} / {1})".format(len(self.inventory), self.maxinventory), "green"))
        if len(self.inventory) == 0:
            print("You have nothing in your inventory!")
        else:
            for index, item in enumerate(self.inventory):
                print("{0}: {1}\n\t{2}".format(
                    index+1, item["name"].title(), item["description"]))

    def printinventory_wrapper(self, *args):
        os.system("cls")
        self.printinventory()
        print(color("Press [e] to exit.", "magenta"))
        # time.sleep(0.5)
        while True:
            if keyboard.is_pressed("e"):
                break
        os.system("cls")
        self.printmap()
        self.gameloop()

    @fuckit
    def player_move(self, direction):
        if direction == "e":
            if self.current_loc[1] < (self.w-1):
                if self.Matrix[self.current_loc[0]][self.current_loc[1]+1][0] != "#":
                    self.Matrix[self.current_loc[0]][self.current_loc[1]
                                                     ] = self.Matrix[self.current_loc[0]][self.current_loc[1]][2]
                    self.Matrix[self.current_loc[0]][self.current_loc[1]+1] = ["@",
                                                                               1, self.Matrix[self.current_loc[0]][self.current_loc[1]+1]]
                    self.current_loc = [
                        self.current_loc[0], self.current_loc[1]+1]
        if direction == "w":
            if self.current_loc[1] > 0:
                if self.Matrix[self.current_loc[0]][self.current_loc[1]-1][0] != "#":
                    self.Matrix[self.current_loc[0]][self.current_loc[1]
                                                     ] = self.Matrix[self.current_loc[0]][self.current_loc[1]][2]
                    self.Matrix[self.current_loc[0]][self.current_loc[1]-1] = ["@",
                                                                               1, self.Matrix[self.current_loc[0]][self.current_loc[1]-1]]
                    self.current_loc = [
                        self.current_loc[0], self.current_loc[1]-1]
        if direction == "n":
            if self.current_loc[0] > 0:
                if self.Matrix[self.current_loc[0]-1][self.current_loc[1]][0] != "#":
                    self.Matrix[self.current_loc[0]][self.current_loc[1]
                                                     ] = self.Matrix[self.current_loc[0]][self.current_loc[1]][2]
                    self.Matrix[self.current_loc[0]-1][self.current_loc[1]] = ["@",
                                                                               1, self.Matrix[self.current_loc[0]-1][self.current_loc[1]]]
                    self.current_loc = [
                        self.current_loc[0]-1, self.current_loc[1]]
        if direction == "s":
            if self.current_loc[0] < (self.h-1):
                if self.Matrix[self.current_loc[0]+1][self.current_loc[1]][0] != "#":
                    self.Matrix[self.current_loc[0]][self.current_loc[1]
                                                     ] = self.Matrix[self.current_loc[0]][self.current_loc[1]][2]
                    self.Matrix[self.current_loc[0]+1][self.current_loc[1]] = ["@",
                                                                               1, self.Matrix[self.current_loc[0]+1][self.current_loc[1]]]
                    self.current_loc = [
                        self.current_loc[0]+1, self.current_loc[1]]
        self.deactivateSeentiles()

    def printmap(self):
        print("{0} {1} {2} {3} {4} {5} {6}".format(color("[Dungeon]", "red"), color("Move: {}".format(self.moves), "green"), color("Health: ({0} / {1})".format(self.health, self.maxhealth), "cyan"), color("XP: {}".format(
            self.xp), "magenta"), color("Coins: {}".format(self.coins), "yellow"), color("Inventory ({0} / {1})".format(len(self.inventory), self.maxinventory), "green"), color("Time: {}".format(time.time()-self.time), "green")))
        self.Map = []
        index = -1
        for row in self.Matrix:
            self.Map.append([])
            index += 1
            for cell in row:
                if len(cell) < 4:
                    if cell[1] == 0:
                        self.Map[index].append("⠀")
                    elif cell[1] == 1:
                        # Make enemy hidden
                        if cell[0] in self.enemytypes:
                            self.Map[index].append(self.symbol_empty)
                        else:
                            self.Map[index].append(cell[0])
                            continue
                        # Display item inv
                        # TYPES OF OBJECTS
                        if cell[0] == "@":  # if scanning player
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
        print(DataFrame(self.Map))
        print("""Press [arrow keys] to move.
Press [i] for inventory.
Press [esc] to exit.
Press [u] to equip/use items.
Press [d] to drop items.
""")

    def player(self, state):

        if state == 1:
            found = False
            while not found:
                global x, y
                x, y = random.randint(0, self.w-1), random.randint(0, self.h-1)
                if not self.Matrix[x][y][0] == "#":
                    self.Matrix[x][y] = ["@", 1, self.Matrix[x][y]]
                    found = True
            self.current_loc = [x, y]

            self.name = input(
                "Hello adventure, what is your name? (Enter for random name)\n> ")

            if not self.name:
                self.name = people().generate_name()
                print("Your name is: {}".format(self.name))
            time.sleep(1)
        self.deactivateSeentiles()

    # @fuckit
    def deactivateSeentiles(self):
        self.Matrix[self.current_loc[0] -
                    1][self.current_loc[1]-1][1] = 1  # North West
        self.Matrix[self.current_loc[0] +
                    1][self.current_loc[1]-1][1] = 1  # South West
        self.Matrix[self.current_loc[0]][self.current_loc[1]-1][1] = 1  # West
        self.Matrix[self.current_loc[0] -
                    1][self.current_loc[1]+1][1] = 1  # North East
        self.Matrix[self.current_loc[0] +
                    1][self.current_loc[1]+1][1] = 1  # South East
        self.Matrix[self.current_loc[0]][self.current_loc[1]+1][1] = 1  # East
        self.Matrix[self.current_loc[0]-1][self.current_loc[1]][1] = 1  # North
        self.Matrix[self.current_loc[0]+1][self.current_loc[1]][1] = 1  # South
        """
        # Prevent Border Sneak-peaking
        if not self.current_loc[1] == 0:
            if not self.current_loc[0] == 0:
                self.Matrix[self.current_loc[0]-1][self.current_loc[1]-1][1] = 1 # North West
            if not self.current_loc[1] == (self.h - 1):
                self.Matrix[self.current_loc[0]+1][self.current_loc[1]-1][1] = 1 # South West
            self.Matrix[self.current_loc[0]][self.current_loc[1]-1][1] = 1 # West
        if not self.current_loc[1] == (self.w):
            if not self.current_loc[0] == 0:
                self.Matrix[self.current_loc[0]-1][self.current_loc[1]+1][1] = 1 # North East
            if not self.current_loc[1] == (self.h - 1): ###
                self.Matrix[self.current_loc[0]+1][self.current_loc[1]+1][1] = 1 # South East
            self.Matrix[self.current_loc[0]][self.current_loc[1]+1][1] = 1 # East
        if not self.current_loc[0] == 0:
            self.Matrix[self.current_loc[0]-1][self.current_loc[1]][1] = 1 # North
        if not self.current_loc[1] == (self.h - 1):
            self.Matrix[self.current_loc[0]+1][self.current_loc[1]][1] = 1 # South
        """


# if __name__ == "__main__":
try:
    d = Dungeon()
    d.gameloop()
except KeyboardInterrupt:
    print("Exiting [Dungeon]...")
    sys.exit()
