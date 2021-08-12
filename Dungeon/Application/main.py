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
from rich.console import Console
from rich.theme import Theme

# App Imports
from .classes.weapons import *
from .classes.people import *
from .classes.enemies import Orc
from .config import config
from .classes.map import Map, DungeonCell
from .loggers import LogType
from .classes.items import *
from .classes.database import DungeonItemDatabase

import random
print("Loading...")

# convenient lambda functions
random_yx = lambda: (random.randint(1, config.map.max_y), random.randint(1, config.map.max_x))
style_text = lambda t, s: f"[{s}]{t}[/{s}]"
controls_style = lambda t: style_text(chr(92)+f"[{t}]", 'controls')

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
        self.rich_print = self.rich_console.print
        self.log_info("rich console & styles set up")

        # Empty tile
        self.player_loc = []

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
        self.equipped = DungeonItemDatabase.search_item(name="Fists")

        # Fill inventory with starter potions
        for i in range(2):
            self.inventory.append(
                DungeonItemDatabase.search_item(
                    name="Weak Healing Potion"
                )
            )

        self.log_info("init dungeon variables")
        
        # generate unique session id for highscore leaderboard
        while True:
            self.session_id = random.getrandbits(10000)
            if len(self.leaderboard.search(self.leaderboardQuery.session_id == self.session_id)) == 0:  # check for repeating
                break
        self.log_info("generated session id")

        self.generate_map()
        self.log_info("generated map")
        self.log_debug(f"Raw Map String:\n{self.base_map_str}")

    def generate_map(self):
        '''
        generates the game map
        '''
        m = Map(int(config.map.width/2), int(config.map.height/2))
        m.randomize()
        self.matrix = []

        skinnyMatrix = m._to_str_matrix()
        for i, row in enumerate(skinnyMatrix):
            self.matrix.append([])
            for n, cell in enumerate(row):
                if cell == "O":
                    self.matrix[i].append(DungeonCell(symbol=config.symbols.wall))
                else:
                    self.matrix[i].append(DungeonCell(symbol=config.symbols.empty))
        self.log_info("generated base map string")

        #self.matrix = [[[config.symbols.empty, 0, []] for x in range(config.map.width)] for y in range(config.map.height)]

        # Fill map (Bad Orcs)
        for count in range(config.count.orc):
            while True:
                x, y = random_yx()
                if self.matrix[y][x].symbol != config.symbols.wall:
                    self.matrix[y][x] = DungeonCell(symbol=config.symbols.orc)
                    break
        self.log_info("filled map with orcs")

        # Fill map (chemists)
        for count in range(config.count.chemist):
            while True:
                x, y = random_yx()
                if self.matrix[y][x].symbol != config.symbols.wall:
                    self.matrix[y][x] = DungeonCell(
                        symbol=config.symbols.chemist,
                        inventory=[Chemist()]
                    )
                    break
        self.log_info("filled map with chemists")

        # Scatter potions
        for count in range(config.count.floor_potions):
            while True:
                y, x = random_yx()
                if self.matrix[y][x].symbol != config.symbols.wall:
                    cell = self.matrix[y][x]
                    rc_num = random.randint(0, 6)
                    if rc_num < 3:
                        chosen_potion = DungeonItemDatabase.search_item(
                            name="Weak Healing Potion"
                        )
                    elif rc_num < 6:
                        chosen_potion = DungeonItemDatabase.search_item(
                            name="Medium Healing Potion"
                        )
                    else:
                        chosen_potion = DungeonItemDatabase.search_item(
                            name="Strong Healing Potion"
                        )
                    self.matrix[y][x].inventory.append(chosen_potion)
                    break
        self.log_info("filled map with potions")

        # init player
        while True:
            y, x = random_yx()
            if self.matrix[y][x].symbol != config.symbols.wall:
                self.matrix[y][x] = DungeonCell(
                    symbol=config.symbols.player,
                    explored=True,
                    inventory=self.matrix[y][x]
                )
                break
        self.player_loc = (y, x)

        self.player_name = input("Hello adventurer, what is your name? (Enter for random name)\n> ")
        if not self.player_name:
            self.player_name = People.generate_name()
            print("Your name is: {}".format(self.player_name))
        self.deactivate_seen_tiles()
        self.log_info("initiated player")

        # init target
        while True:
            y, x = random_yx()
            if self.matrix[y][x].symbol != config.symbols.wall:
                """
                to maintain at least a solid 13 distance between goal and player
                """
                # if abs(x-self.player_loc[0])+abs(y-self.player_loc[1]) > 13:
                if abs(y-self.player_loc[0])+abs(x-self.player_loc[1]) > config.map.min_distance:
                    #self.matrix[x][y] = [config.symbols.target, 0, self.matrix[x][y]]
                    self.matrix[y][x] = DungeonCell(symbol=config.symbols.target)
                    break
        self.log_info("put target on map")
        self.base_map_str = self.gen_debug_map()       

    def gen_debug_map(self):
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

    def event(self):
        time.sleep(0.1)  # Time Lag
        self.moves += 1
        # print("\n"*100) # comment thi to make it smoother, unless your pc does not support cls
        self.print_map()
        self.check()

    def check(self):
        player_cell = self.matrix[self.player_loc[0]][self.player_loc[1]].inventory
        # print(self.playerontile_type)
        if player_cell.symbol == config.symbols.target:
            self.game_over("exit")
        if player_cell.symbol in config.symbols.enemies:
            self.attack(enemy_symbol=player_cell.symbol)
            self.print_map()
        if player_cell.symbol in config.symbols.traders:
            trader = player_cell.inventory[0]
            self.rich_print(f"You have met a {style_text(trader.name, 'name')}, a {style_text(trader.occupation, 'occupation')}!")
            time.sleep(1)
            self.inventory_item_menu(
                print_header=lambda: self.trader_screen_header(trader=trader),
                menu_function=self.trader_menu_function,
                trader=trader
            )
            self.print_map()
        # inv list
        if len(player_cell.inventory) > 0 and isinstance(player_cell.inventory[0], DungeonItem):
            self.print_cell_inv(
                inventory=list(filter(
                    lambda x: isinstance(x, DungeonItem),
                    player_cell.inventory
                ))
            )


    def print_cell_inv(self, inventory):
        constructor = ""
        # print(self.playerontile_inv)
        # time.sleep(1)
        if len(inventory) == 1:
            constructor = style_text(inventory[0].name, 'item')
        elif len(inventory) > 1:
            constructor = '{} and {}'.format(', '.join(map(lambda obj: style_text(obj.name, 'item'), inventory[:-1])), style_text(inventory[-1].name, 'item'))
        self.rich_print("You see a {} here.".format(constructor))

    def print_leaderboard(self):
        self.leaderboard.insert({
            "name": self.player_name,
            "time": round(time.time() - self.start_time, 3),
            "moves": self.moves,
            "datetime": str(datetime.datetime.now()),
            "sessionid": self.session_id
        })
        self.leaderboardList = self.leaderboard.all()

        self.leaderboardList.sort(key=operator.itemgetter('time'))
        self.rich_print(f"{style_text('[Leaderboard]', 'magenta')}\n", highlight=False)
        for i, element in enumerate(self.leaderboardList):
            self.prefix_text = ""
            if element["sessionid"] == self.session_id:  # show current game score
                self.prefix_text = style_text("< This Game > ", 'green')
            self.rich_print("{the_prefix}{index}: [{name}]\n\tTime: {time}\n\tMoves: {moves}\n\tDate and Time: {datetime}".format(
                the_prefix=self.prefix_text,
                index=str(i+1),
                name=element["name"],
                time=element["time"],
                moves=element["moves"],
                datetime=element["datetime"]
            ), highlight=False)

    def game_over(self, how):
        if how == "exit":
            os.system('cls')
            self.rich_print(f"You have {style_text('successfully', 'success')} escaped the {style_text('[DUNGEON]', 'game_header')}", highlight=False)
            self.print_leaderboard()
        elif how == "dead":
            self.rich_print(f"You have {style_text('failed', 'fail')} to escape the {style_text('[DUNGEON]', 'game_header')}, you'll do better next time.", highlight=False)
        self.rich_console.input(f"{style_text('[Enter]', 'controls')} to {style_text('exit', 'action')}")
        sys.exit()

    def trader_screen_header(self, trader):
        os.system('cls')
        self.rich_print(f"{style_text(trader.name, 'name')} - {style_text(trader.occupation, 'occupation')}\n", highlight=False)
        for index, item in enumerate(trader.stuff):
            self.rich_print(f"{index+1}: {style_text(item.name, 'item')} {style_text(item.cost, 'coin')}", highlight=False)
            self.rich_print(f"\t {item.description}")
        print("\n")

    def trader_menu_function(self, selected_item, pressed=None, print_header=None):
        if self.coins >= selected_item.cost:
            if len(self.inventory) == self.max_inventory:
                print("Your inventory is full.\n")
            else:
                print("You have bought the {}\n".format(selected_item.name))
                self.inventory.append(selected_item)
                self.coins -= selected_item.cost
        else:
            print("You do not have enough money to buy the {}.\n".format(style_text(selected_item.name, 'item')))

    def attack(self, enemy_symbol):  # He protecc he attacc he also like to snacc
        enemy = {
            config.symbols.orc: Orc
        }.get(enemy_symbol)()
        print_header = lambda: self.rich_print(f"Enemy: {enemy.name}\n", style="enemy", highlight=False)
        print_health = lambda enemy_hp_drop=None, player_hp_drop=None: (
            self.rich_print(f"{style_text(enemy.name, 'enemy')}: Health - {style_text(enemy.health, 'health')}{style_text(' ( -'+str(enemy_hp_drop)+' )', 'hp_drop') if enemy_hp_drop else ''}", highlight=False),
            self.rich_print(f"{style_text('You', 'player')}: Health - {style_text(self.health, 'health')}{style_text(' ( -'+str(player_hp_drop)+' )', 'hp_drop') if player_hp_drop else ''}\n", highlight=False)
        )
        print_footer = lambda: self.rich_print(f"Press {controls_style('a')} to {style_text('attack', 'action')}.", highlight=False)

        self.rich_print(f"You have met an {style_text(enemy.name, 'enemy')}!", highlight=False)
        time.sleep(1)
        os.system("cls")
        print_header();print_health();print_footer()
        while enemy.health > 0:
            if keyboard.is_pressed("a"):
                os.system('cls')
                print_header()
                time.sleep(0.15)
                enemy.health, enemy_hp_drop = self.hit(enemy)
                print_health(enemy_hp_drop=enemy_hp_drop)
                if enemy.health <= 0:
                    break
                time.sleep(0.15)
                self.health, player_hp_drop = self.enemy_hit(enemy)
                print_health(player_hp_drop=player_hp_drop)
                print_footer()
                time.sleep(0.15)
                if self.health <= 0:
                    self.game_over("dead")
        self.xp += enemy.xp_drop
        self.rich_print(f"{enemy.texts.death}")
        self.matrix[self.player_loc[0]][self.player_loc[1]].inventory = DungeonCell(
            symbol=config.symbols.empty,
            explored=True
        )

        # print(self.matrix[self.player_loc[0]][self.player_loc[1]])
        self.rich_print(f"The {style_text(enemy.name, 'enemy')} drops {style_text(enemy.coin_drop, 'coin')} coins.", highlight=False)
        self.coins += enemy.coin_drop
        time.sleep(2)

    def enemy_hit(self, enemy):
        if random.randint(1, 100) < enemy.accuracy:
            attack_damage = enemy.attack_base + \
                random.randint(enemy.attack_range[0], enemy.attack_range[1])
            if attack_damage == enemy.attack_base + enemy.attack_range[1]:
                # Max Damage
                self.rich_print(enemy.texts.critical_hit)
            else:
                self.rich_print(enemy.texts.hit)
            #self.rich_print(f"\n[player]Your[/player] health [hp_drop]-{attack_damage}[/hp_drop]\n", highlight=False)
            return (self.health - attack_damage), attack_damage
        else:
            self.rich_print(enemy.texts.missed_hit)
            return self.health, 0

    def hit(self, enemy):
        if not random.randint(1, 100) < self.equipped.accuracy:
            attack_damage = self.equipped.base_attack + random.randint(
                self.equipped.attack_range[0], self.equipped.attack_range[1])
            if attack_damage == self.equipped.base_attack + self.equipped.attack_range[1]:
                # Max Damage
                self.rich_print(
                    self.equipped.texts.critical_hit.format(style_text(self.equipped.name, 'weapons')), highlight=False)
            else:
                self.rich_print(
                    self.equipped.texts.hit.format(style_text(enemy.name, 'enemy'), style_text(self.equipped.name, 'weapons')), highlight=False)
            #self.rich_print(f"\n[enemy]{enemy.name}\'s[/enemy] health [hp_drop]-{attack_damage}[/hp_drop]\n", highlight=False)
            return (enemy.health - attack_damage), attack_damage
        else:
            self.rich_print(self.equipped.texts.missed_hit.format(style_text(enemy.name, 'enemy')), highlight=False)
            return enemy.health, 0

    def gameloop(self):
        self.print_map()
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
                #self.equip_menu()
                self.inventory_item_menu(
                    print_header=lambda: self.menu_header(menu_name="Use/Equip"),
                    menu_function=self.equip_menu_function
                )
                self.print_map()
            elif keyboard.is_pressed("d"):
                self.inventory_item_menu(
                    print_header=lambda: self.menu_header(menu_name="Drop"),
                    menu_function=self.drop_menu_function
                )
                self.print_map()
            elif keyboard.is_pressed("i"):
                self.print_inventory_wrapper()
                self.print_map()

    def menu_header(self, menu_name):
        os.system('cls')
        self.rich_print(f"{menu_name} Menu\n", style="menu_header", highlight=False)

    def inventory_item_menu(self, print_header, menu_function, trader=None):
        print_footer = lambda: (
            self.print_inventory(),
            self.rich_print(f"\nPress {controls_style('e')} to {style_text('exit', 'action')}.", highlight=False)
        )
        print_header()
        print_footer()
        while True:
            pressed = keyboard.read_key()
            if pressed.isnumeric():
                pressed = int(pressed)
                print_header()
                inv = trader.stuff if trader else self.inventory
                if not ((pressed < len(inv)+1) and (1 <= pressed)):
                    print("You have chosen an invalid choice.\n")
                    time.sleep(0.2)
                    print_footer()
                    continue
                selected_item = trader.stuff[pressed-1] if trader else self.inventory[pressed-1]
                menu_function(selected_item=selected_item, pressed=pressed, print_header=print_header)
                time.sleep(0.2)
                print_footer()
            if pressed == "e":
                break

    def equip_menu_function(self, selected_item, pressed=None, print_header=None):
        if isinstance(selected_item, DungeonInventory):
            self.rich_print("You sling the {} over your shoulders.\n".format(
                style_text(selected_item.name, 'item')))
            del self.inventory[pressed-1]
            self.max_inventory += selected_item.inventory
        elif isinstance(selected_item, DungeonPotion):
            if self.health == self.max_health:
                print(
                    "You are already at maximum health. Try drinking a maximum-health increasing potion.\n")
            else:
                if (self.health + selected_item.hp_change) > self.max_health:
                    self.health = self.max_health
                else:
                    self.health += selected_item.hp_change
                self.rich_print("You drink the {}. The strong elixir makes you feel rejuvenated.\n".format(style_text(selected_item.name, 'item')))
                del self.inventory[pressed-1]

    def drop_menu_function(self, selected_item, pressed=None, print_header=None):
        self.rich_print(f"Do you want to drop the {style_text(selected_item.name, 'item')}?\nPress {controls_style('y')} for {style_text('Yes', 'action')} and {controls_style('n')} for {style_text('No', 'action')}.", highlight=False)
        while True:
            if keyboard.is_pressed("y"):
                os.system('cls')
                print_header()
                del self.inventory[pressed-1]
                self.rich_print(f"You have dropped the {style_text(selected_item.name, 'item')}!\n")
                break
            elif keyboard.is_pressed("n"):
                os.system('cls')
                print_header()
                self.rich_print(f"You do not drop the {style_text(selected_item.name, 'item')}.\n")
                break

    def print_inventory(self):
        self.rich_print(f"Inventory ({len(self.inventory)} / {self.max_inventory})\n", style="inventory", highlight=False)
        if len(self.inventory) == 0:
            print("You have nothing in your inventory!\n")
        else:
            for index, item in enumerate(self.inventory):
                self.rich_print("{0}: {1}\n\t{2}".format(index+1, style_text(item.name, 'item'), item.description))

    def print_inventory_wrapper(self, *args):
        os.system("cls")
        self.print_inventory()
        self.rich_print(f"Press {controls_style('e')} to {style_text('exit', 'action')}.", highlight=False)
        # time.sleep(0.5)
        while True:
            if keyboard.is_pressed("e"):
                break

    def player_move(self, direction):
        y, x = self.player_loc
        condition, new_y, new_x = {
            "e": ((x < (config.map.max_x)), y, x+1),
            "w": ((x > 0), y, x-1),
            "n": ((y > 0), y-1, x),
            "s": ((y < (config.map.max_y)), y+1, x)
        }.get(direction)
        if condition:
            if self.matrix[new_y][new_x].symbol != config.symbols.wall:
                self.matrix[y][x] = self.matrix[y][x].inventory
                self.matrix[new_y][new_x] = DungeonCell(
                    symbol=config.symbols.player,
                    explored=True,
                    inventory=self.matrix[new_y][new_x]
                )

                self.player_loc = (new_y, new_x)
        self.deactivate_seen_tiles()

    def print_map(self):
        os.system('cls')
        self.rich_print("[Dungeon]", style="game_header", end=" ", highlight=False)
        self.rich_print(f"Move: {self.moves}", style="move_count", end=" ", highlight=False)
        self.rich_print(f"Health: ({self.health} / {self.max_health})", style="health", end=" ", highlight=False)
        self.rich_print(f"XP: {self.xp}", style="xp_count", end=" ", highlight=False)
        self.rich_print(f"Coins: {self.coins}", style="coin", end=" ", highlight=False)
        self.rich_print(f"Inventory ({len(self.inventory)} / {self.max_inventory})", style="inventory", end=" ", highlight=False)
        self.rich_print(f"Time: {(time.time()-self.start_time):.2f}s", style="time_count", highlight=False)
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
        self.rich_print(map_str, highlight=False)
        self.rich_print(f"""
Press {controls_style('arrow keys')} to {style_text('move', 'action')}.
Press {controls_style('i')} for {style_text('inventory', 'action')}.
Press {controls_style('esc')} to {style_text('exit', 'action')}.
Press {controls_style('u')} to {style_text('equip/use items', 'action')}.
Press {controls_style('d')} to {style_text('drop items', 'action')}.
""", highlight=False)

    def deactivate_seen_tiles(self):
        y, x = self.player_loc
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
        if not self.player_loc[1] == 0:
            if not self.player_loc[0] == 0:
                self.matrix[self.player_loc[0]-1][self.player_loc[1]-1][1] = 1 # North West
            if not self.player_loc[1] == (config.map.height - 1):
                self.matrix[self.player_loc[0]+1][self.player_loc[1]-1][1] = 1 # South West
            self.matrix[self.player_loc[0]][self.player_loc[1]-1][1] = 1 # West
        if not self.player_loc[1] == (config.map.width):
            if not self.player_loc[0] == 0:
                self.matrix[self.player_loc[0]-1][self.player_loc[1]+1][1] = 1 # North East
            if not self.player_loc[1] == (config.map.height - 1): ###
                self.matrix[self.player_loc[0]+1][self.player_loc[1]+1][1] = 1 # South East
            self.matrix[self.player_loc[0]][self.player_loc[1]+1][1] = 1 # East
        if not self.player_loc[0] == 0:
            self.matrix[self.player_loc[0]-1][self.player_loc[1]][1] = 1 # North
        if not self.player_loc[1] == (config.map.height - 1):
            self.matrix[self.player_loc[0]+1][self.player_loc[1]][1] = 1 # South
        """


# if __name__ == "__main__":
def main(logger):
    try:
        d = Dungeon(
            logger=logger
        )
        d.log_info("dungeon set up is done, starting game")
        d.gameloop()
    except KeyboardInterrupt:
        print("Exiting [Dungeon]...")
        logger.log(LogType.INFO, "game exited")
        sys.exit()
    except Exception as e:
        logger.log(LogType.FATAL, f"\n{''.join(traceback.format_tb(e.__traceback__))}\n\n{str(e)}")
