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
from rich.console import Console
from rich.theme import Theme

# App Imports
from .classes.weapons import *
from .classes.people import *
from .classes.enemies import Orc
from .config import config
from .utils import random_yx, style_text, controls_style
from .classes.map import GeneratedMap, DungeonMap, DungeonCell, DungeonPlayer
from .loggers import LogType
from .classes.items import *
from .classes.database import DungeonItemDatabase

import random
print("Loading...")

class Dungeon:
    def __init__(self, logger):

        # instantiate logger
        self.log = logger
        self.log.info("logging functions set up is done")

        #sets console size and clears console
        os.system("mode 100, 38 && cls")
        self.log.info("resized console & cleared")

        # Set up rich styles
        self.rich_console = Console(
            theme=Theme(config.styles)
        )
        self.print = self.rich_console.print
        self.log.info("rich console & styles set up")

        # Game vars init
        self.moves = 1

        # Leaderboard
        self.leaderboard = TinyDB("leaderboard.json")
        self.leaderboardQuery = Query()

        # Init Player Stat Vars
        # name, base attack, startrandom, endrandom, chanceofhit, hittextsucessful, hittextweak, hittextmiss
        self.player = DungeonPlayer(
            health=config.player.health,
            max_health=config.player.max_health,
            max_inventory=config.player.max_inventory,
            coins=config.player.coins,
            xp=config.player.xp,
            equipped=DungeonItemDatabase.search_item(name="Fists"),
            game=self
        )

        # Fill inventory with starter potions
        for i in range(2):
            self.player.inventory.append(
                DungeonItemDatabase.search_item(
                    name="Weak Healing Potion"
                )
            )

        self.log.info("init dungeon and player variables")
        
        # generate unique session id for highscore leaderboard
        while True:
            self.session_id = random.getrandbits(10000)
            if len(self.leaderboard.search(self.leaderboardQuery.session_id == self.session_id)) == 0:  # check for repeating
                break
        self.log.info("generated session id")

        self.generate_map()
        self.log.info("generated map")
        self.log.debug(f"Raw Map String:\n{self.map.get_debug_map()}")

    def generate_map(self):
        '''
        generates the game map
        '''

        self.map = DungeonMap(game=self)
        self.log.info("initialised map")

        #self.map.matrix = [[[config.symbols.empty, 0, []] for x in range(config.map.width)] for y in range(config.map.height)]

        # Fill map (Bad Orcs)
        for count in range(config.count.orc):
            while True:
                x, y = random_yx()
                if self.map.matrix[y][x].symbol != config.symbols.wall:
                    self.map.matrix[y][x] = DungeonCell(symbol=config.symbols.orc, game=self)
                    break
        self.log.info("filled map with orcs")

        # Fill map (chemists)
        for count in range(config.count.chemist):
            while True:
                x, y = random_yx()
                if self.map.matrix[y][x].symbol != config.symbols.wall:
                    self.map.matrix[y][x] = DungeonCell(
                        symbol=config.symbols.chemist,
                        game=self,
                        inventory=[Chemist()]
                    )
                    break
        self.log.info("filled map with chemists")

        # Scatter potions
        for count in range(config.count.floor_potions):
            while True:
                y, x = random_yx()
                if self.map.matrix[y][x].symbol != config.symbols.wall:
                    cell = self.map.matrix[y][x]
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
                    self.map.matrix[y][x].inventory.append(chosen_potion)
                    break
        self.log.info("filled map with potions")

        # init player
        while True:
            y, x = random_yx()
            if self.map.matrix[y][x].symbol != config.symbols.wall:
                self.map.matrix[y][x] = DungeonCell(
                    symbol=config.symbols.player,
                    game=self,
                    explored=True,
                    inventory=self.map.matrix[y][x]
                )
                break
        self.player.location = (y, x)

        self.player.name = input("Hello adventurer, what is your name? (Enter for random name)\n> ")
        if not self.player.name:
            self.player.name = People.generate_name()
            print("Your name is: {}".format(self.player.name))
            time.sleep(1.5)
        self.map.update_adjacent_cells()
        self.log.info("initiated player")

        # init target
        while True:
            y, x = random_yx()
            if self.map.matrix[y][x].symbol != config.symbols.wall:
                """
                to maintain at least a solid 13 distance between goal and player
                """
                # if abs(x-self.player.y)+abs(y-self.player.x) > 13:
                if abs(y-self.player.y)+abs(x-self.player.x) > config.map.min_distance:
                    #self.map.matrix[x][y] = [config.symbols.target, 0, self.map.matrix[x][y]]
                    self.map.matrix[y][x] = DungeonCell(symbol=config.symbols.target, game=self)
                    break
        self.log.info("put target on map")

    def event(self):
        time.sleep(0.1)  # Time Lag
        self.moves += 1
        # print("\n"*100) # comment thi to make it smoother, unless your pc does not support cls
        self.map.print()
        self.check()

    def check(self):
        player_cell = self.map.matrix[self.player.y][self.player.x].inventory
        # print(self.playerontile_type)
        if player_cell.symbol == config.symbols.target:
            self.game_over("exit")
        if player_cell.symbol in config.symbols.enemies:
            self.attack(enemy_symbol=player_cell.symbol)
            self.map.print()
        if player_cell.symbol in config.symbols.traders:
            trader = player_cell.inventory[0]
            self.print(f"You have met a {style_text(trader.name, 'name')}, a {style_text(trader.occupation, 'occupation')}!")
            time.sleep(1)
            self.inventory_item_menu(
                print_header=lambda: self.trader_screen_header(trader=trader),
                menu_function=self.trader_menu_function,
                trader=trader
            )
            self.map.print()
        # inv list
        player_cell.print_inventory()

    def print_leaderboard(self):
        self.leaderboard.insert({
            "name": self.player.name,
            "time": round(time.time() - self.start_time, 3),
            "moves": self.moves,
            "datetime": str(datetime.datetime.now()),
            "sessionid": self.session_id
        })
        self.leaderboardList = self.leaderboard.all()

        self.leaderboardList.sort(key=operator.itemgetter('time'))
        self.print(f"{style_text('[Leaderboard]', 'magenta')}\n", highlight=False)
        for i, element in enumerate(self.leaderboardList):
            self.prefix_text = ""
            if element["sessionid"] == self.session_id:  # show current game score
                self.prefix_text = style_text("< This Game > ", 'green')
            self.print("{the_prefix}{index}: [{name}]\n\tTime: {time}\n\tMoves: {moves}\n\tDate and Time: {datetime}".format(
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
            self.print(f"You have {style_text('successfully', 'success')} escaped the {style_text('[DUNGEON]', 'game_header')}", highlight=False)
            self.print_leaderboard()
        elif how == "dead":
            self.print(f"You have {style_text('failed', 'fail')} to escape the {style_text('[DUNGEON]', 'game_header')}, you'll do better next time.", highlight=False)
        self.rich_console.input(f"{style_text('[Enter]', 'controls')} to {style_text('exit', 'action')}")
        sys.exit()

    def trader_screen_header(self, trader):
        os.system('cls')
        self.print(f"{style_text(trader.name, 'name')} - {style_text(trader.occupation, 'occupation')}\n", highlight=False)
        for index, item in enumerate(trader.stuff):
            self.print(f"{index+1}: {style_text(item.name, 'item')} {style_text(item.cost, 'coin')}", highlight=False)
            self.print(f"\t {item.description}")
        print("\n")

    def trader_menu_function(self, selected_item, pressed=None, print_header=None):
        if self.player.coins >= selected_item.cost:
            if len(self.player.inventory) == self.player.max_inventory:
                print("Your inventory is full.\n")
            else:
                print("You have bought the {}\n".format(selected_item.name))
                self.player.inventory.append(selected_item)
                self.player.coins -= selected_item.cost
        else:
            print("You do not have enough money to buy the {}.\n".format(style_text(selected_item.name, 'item')))

    def attack(self, enemy_symbol):  # He protecc he attacc he also like to snacc
        enemy = {
            config.symbols.orc: Orc
        }.get(enemy_symbol)(game=self)
        print_header = lambda: self.print(f"Enemy: {enemy.name}\n", style="enemy", highlight=False)
        print_health = lambda enemy_hp_drop=None, player_hp_drop=None: (
            self.print(f"{style_text(enemy.name, 'enemy')}: Health - {style_text(enemy.health, 'health')}{style_text(' ( -'+str(enemy_hp_drop)+' )', 'hp_drop') if enemy_hp_drop else ''}", highlight=False),
            self.print(f"{style_text('You', 'player')}: Health - {style_text(self.player.health, 'health')}{style_text(' ( -'+str(player_hp_drop)+' )', 'hp_drop') if player_hp_drop else ''}\n", highlight=False)
        )
        print_footer = lambda: self.print(f"Press {controls_style('a')} to {style_text('attack', 'action')}.", highlight=False)

        self.print(f"You have met an {style_text(enemy.name, 'enemy')}!", highlight=False)
        time.sleep(1)
        os.system("cls")
        print_header();print_health();print_footer()
        while enemy.health > 0:
            if keyboard.is_pressed("a"):
                os.system('cls')
                print_header()
                time.sleep(0.15)
                enemy.health, enemy_hp_drop = self.player.attack_turn(enemy)
                print_health(enemy_hp_drop=enemy_hp_drop)
                if enemy.health <= 0:
                    break
                time.sleep(0.15)
                self.player.health, player_hp_drop = enemy.attack_turn()
                print_health(player_hp_drop=player_hp_drop)
                print_footer()
                time.sleep(0.15)
                if self.player.health <= 0:
                    self.game_over("dead")
        self.player.xp += enemy.xp_drop
        self.print(f"{enemy.texts.death}")
        self.map.matrix[self.player.y][self.player.x].inventory = DungeonCell(
            symbol=config.symbols.empty,
            game=self,
            explored=True
        )

        # print(self.map.matrix[self.player.y][self.player.x])
        self.print(f"The {style_text(enemy.name, 'enemy')} drops {style_text(f'{enemy.coin_drop} coins', 'coin')}.", highlight=False)
        self.player.coins += enemy.coin_drop
        time.sleep(2)

    def gameloop(self):
        self.start_time = time.time()
        self.log.info(f"started game at {time.time():.2f}")
        self.map.print()
        while True:
            if keyboard.read_key():
                if keyboard.is_pressed("right"):
                    self.player.move("e")
                elif keyboard.is_pressed("left"):
                    self.player.move("w")
                elif keyboard.is_pressed("up"):
                    self.player.move("n")
                elif keyboard.is_pressed("down"):
                    self.player.move("s")
                elif keyboard.is_pressed("esc"):
                    print("Exiting [Dungeon]...")
                    self.log.info(f"game exited at {time.time():.2f}")
                    sys.exit()
                elif keyboard.is_pressed("u"):
                    self.log.time_logged(
                        start="use/equip menu opened",
                        func=lambda: self.inventory_item_menu(
                            print_header=lambda: self.menu_header(menu_name="Use/Equip"),
                            menu_function=self.equip_menu_function
                        ),
                        end="use/equip menu closed"
                    )
                    self.map.print()
                elif keyboard.is_pressed("d"):
                    self.log.time_logged(
                        start="drop menu opened",
                        func=lambda: self.inventory_item_menu(
                            print_header=lambda: self.menu_header(menu_name="Drop"),
                            menu_function=self.drop_menu_function
                        ),
                        end="drop menu closed"
                    )
                    self.map.print()
                elif keyboard.is_pressed("i"):
                    self.log.time_logged(
                        start="inventory opened",
                        func=lambda: self.print_inventory_wrapper(),
                        end="inventory closed"
                    )
                    self.map.print()

    def menu_header(self, menu_name):
        os.system('cls')
        self.print(f"{menu_name} Menu\n", style="menu_header", highlight=False)

    def inventory_item_menu(self, print_header, menu_function, trader=None):
        print_footer = lambda: (
            self.player.print_inventory(),
            self.print(f"\nPress {controls_style('e')} to {style_text('exit', 'action')}.", highlight=False)
        )
        print_header()
        print_footer()
        while True:
            pressed = keyboard.read_key()
            if pressed.isnumeric():
                pressed = int(pressed)
                print_header()
                inv = trader.stuff if trader else self.player.inventory
                if not ((pressed < len(inv)+1) and (1 <= pressed)):
                    print("You have chosen an invalid choice.\n")
                    time.sleep(0.2)
                    print_footer()
                    continue
                selected_item = trader.stuff[pressed-1] if trader else self.player.inventory[pressed-1]
                menu_function(selected_item=selected_item, pressed=pressed, print_header=print_header)
                time.sleep(0.2)
                print_footer()
            if pressed == "e":
                break

    def equip_menu_function(self, selected_item, pressed=None, print_header=None):
        if isinstance(selected_item, DungeonInventory):
            self.print("You sling the {} over your shoulders.\n".format(
                style_text(selected_item.name, 'item')))
            del self.player.inventory[pressed-1]
            self.player.max_inventory += selected_item.inventory
        elif isinstance(selected_item, DungeonPotion):
            if self.player.health == self.player.max_health:
                print(
                    "You are already at maximum health. Try drinking a maximum-health increasing potion.\n")
            else:
                if (self.player.health + selected_item.hp_change) > self.player.max_health:
                    self.player.health = self.player.max_health
                else:
                    self.player.health += selected_item.hp_change
                self.print("You drink the {}. The strong elixir makes you feel rejuvenated.\n".format(style_text(selected_item.name, 'item')))
                del self.player.inventory[pressed-1]

    def drop_menu_function(self, selected_item, pressed=None, print_header=None):
        self.print(f"Do you want to drop the {style_text(selected_item.name, 'item')}?\nPress {controls_style('y')} for {style_text('Yes', 'action')} and {controls_style('n')} for {style_text('No', 'action')}.", highlight=False)
        while True:
            if keyboard.is_pressed("y"):
                os.system('cls')
                print_header()
                del self.player.inventory[pressed-1]
                self.print(f"You have dropped the {style_text(selected_item.name, 'item')}!\n")
                break
            elif keyboard.is_pressed("n"):
                os.system('cls')
                print_header()
                self.print(f"You do not drop the {style_text(selected_item.name, 'item')}.\n")
                break

    def print_inventory_wrapper(self, *args):
        os.system("cls")
        self.player.print_inventory()
        self.print(f"\nPress {controls_style('e')} to {style_text('exit', 'action')}.", highlight=False)
        # time.sleep(0.5)
        while True:
            if keyboard.is_pressed("e"):
                break

# if __name__ == "__main__":
def main(logger):
    try:
        d = Dungeon(
            logger=logger
        )
        d.log.info("dungeon set up is done, starting game")
        d.gameloop()
    except KeyboardInterrupt:
        print("Exiting [Dungeon]...")
        logger.info(f"game exited by KeyboardInterrupt at {time.time():.2f}")
        sys.exit()
    except Exception as e:
        logger.fatal(f"\n{''.join(traceback.format_tb(e.__traceback__))}\n\n{str(e)}")
