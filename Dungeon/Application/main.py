# Standard Lib Imports
import datetime
import os
import sys
import time
import operator
import traceback
import random

# Lib Imports
import keyboard
from tinydb import TinyDB, Query
from rich.console import Console
from rich.theme import Theme

# App Imports
from .config import config
from .utils import random_yx, style_text, controls_style, clear_screen
from .loggers import LogType
from .classes.map import GeneratedMap, DungeonMap, DungeonPlayer
from .classes.menus import DungeonMenu
from .classes.items import *
from .classes.database import DungeonDatabase
from .classes.misc import DungeonTimeData
from .classes.weapons import *
from .classes.people import *

print("Loading...")

class Dungeon:
    def __init__(self, logger):

        # instantiate logger
        self.log = logger
        self.log.info("logging functions set up is done")

        #sets console size and clears console
        clear_screen()
        keyboard.press("f11")
        self.log.info("resized console & cleared")

        # Set up rich styles
        self.rich_console = Console(
            theme=Theme(config.styles)
        )
        self.print = self.rich_console.print
        self.log.info("rich console & styles set up")
        self.menu = DungeonMenu(game=self)

        # Game vars init
        self.moves = 1
        self.db = DungeonDatabase(game=self)

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
            equipped=self.db.item_db.search_item(name="Fists"),
            game=self
        )

        # Fill inventory with starter potions
        for i in range(2):
            self.player.inventory.append(
                self.db.item_db.search_item(
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
        orc_loader = self.db.enemy_db.search_enemy(name="Orc")
        for count in range(config.count.orc):
            while True:
                x, y = random_yx()
                if self.map.matrix[y][x].symbol != config.symbols.wall:
                    self.map.matrix[y][x] = self.map.cell(symbol=orc_loader.data.symbol)
                    break
        self.log.info("filled map with orcs")

        # Fill map (chemists)
        chemist_loader = self.db.people_db.search_trader(occupation="Chemist")
        for count in range(config.count.chemist):
            while True:
                x, y = random_yx()
                if self.map.matrix[y][x].symbol != config.symbols.wall:
                    self.map.matrix[y][x] = self.map.cell(
                        symbol=chemist_loader.data.symbol,
                        inventory=[chemist_loader.load()]
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
                        chosen_potion = self.db.item_db.search_item(
                            name="Weak Healing Potion"
                        )
                    elif rc_num < 6:
                        chosen_potion = self.db.item_db.search_item(
                            name="Medium Healing Potion"
                        )
                    else:
                        chosen_potion = self.db.item_db.search_item(
                            name="Strong Healing Potion"
                        )
                    self.map.matrix[y][x].inventory.append(chosen_potion)
                    break
        self.log.info("filled map with potions")

        # init player
        while True:
            y, x = random_yx()
            if self.map.matrix[y][x].symbol != config.symbols.wall:
                self.map.matrix[y][x] = self.map.cell(
                    symbol=config.symbols.player,
                    explored=True,
                    inventory=self.map.matrix[y][x]
                )
                break
        self.player.location = (y, x)

        self.player.name = input("Hello adventurer, what is your name? (Enter for random name)\n> ")
        if not self.player.name:
            self.player.name = DungeonPeople.generate_name()
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
                    self.map.matrix[y][x] = self.map.cell(symbol=config.symbols.target)
                    break
        self.log.info("put target on map")

    def event(self):
        time.sleep(0.1)  # Time Lag
        self.moves += 1
        # print("\n"*100) # comment thi to make it smoother, unless your pc does not support cls
        self.map.print()
        self.cell_check()

    def cell_check(self):
        player_cell = self.player.cell
        # print(self.playerontile_type)
        if player_cell.symbol == config.symbols.target:
            self.game_over("exit")
        if player_cell.symbol in config.symbols.enemies:
            self.attack(enemy_symbol=player_cell.symbol)
            self.map.print()
        if player_cell.symbol in config.symbols.traders:
            trader = player_cell.object
            self.print(f"You see {style_text(trader.name, 'name')}, a {style_text(trader.occupation, 'occupation')}!")
        # inv list
        player_cell.print_inventory()

    def print_leaderboard(self):
        self.leaderboard.insert({
            "name": self.player.name,
            "time": round(self.time.elapsed, 3),
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
            clear_screen()
            self.log.info(f"escaped dungeon at {time.time():.2f}")
            self.print(f"You have {style_text('successfully', 'success')} escaped the {style_text('[DUNGEON]', 'game_header')}", highlight=False)
            self.print_leaderboard()
        elif how == "dead":
            self.log.info(f"died at {time.time():.2f}")
            self.print(f"You have {style_text('failed', 'fail')} to escape the {style_text('[DUNGEON]', 'game_header')}, you'll do better next time.", highlight=False)
        self.print(f"{style_text('[Enter]', 'controls')} to {style_text('exit', 'action')}")
        while True:
            if keyboard.read_key() and keyboard.is_pressed("enter"):
                break
        sys.exit()

    def attack(self, enemy_symbol):  # He protecc he attacc he also like to snacc
        enemy = self.db.enemy_db.search_enemy(symbol=enemy_symbol).load()
        print_header = lambda: self.print(f"Enemy: {enemy.name}\n", style="enemy", highlight=False)
        print_health = lambda enemy_hp_drop=None, player_hp_drop=None: (
            self.print(f"{style_text(enemy.name, 'enemy')}: Health - {style_text(enemy.health, 'health')}{style_text(' ( -'+str(enemy_hp_drop)+' )', 'hp_drop') if enemy_hp_drop else ''}", highlight=False),
            self.print(f"{style_text('You', 'player')}: Health - {style_text(self.player.health, 'health')}{style_text(' ( -'+str(player_hp_drop)+' )', 'hp_drop') if player_hp_drop else ''}\n", highlight=False)
        )
        print_footer = lambda: self.print(f"Press {controls_style('a')} to {style_text('attack', 'action')}.", highlight=False)

        self.print(f"You have met an {style_text(enemy.name, 'enemy')}!", highlight=False)
        time.sleep(1)
        clear_screen()
        print_header();print_health();print_footer()
        while enemy.health > 0:
            if keyboard.is_pressed("a"):
                clear_screen()
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
        prev_inventory = self.player.cell.inventory
        self.map.matrix[self.player.y][self.player.x].inventory = self.map.cell(
            symbol=config.symbols.empty,
            explored=True,
            inventory=prev_inventory
        )

        # print(self.map.matrix[self.player.y][self.player.x])
        self.print(f"The {style_text(enemy.name, 'enemy')} drops {style_text(f'{enemy.coin_drop} coins', 'coin')}.", highlight=False)
        self.player.coins += enemy.coin_drop
        time.sleep(2)

    def gameloop(self):
        self.time = DungeonTimeData(game=self)
        self.log.info(f"started game at {time.time():.2f}")
        self.map.print()
        while True:
            if keyboard.read_key():
                self.time.add()
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
                        func=lambda: self.menu.inventory(
                            menu_context=self.menu.context(
                                function=self.menu.function.equip,
                                header=lambda: self.menu.header.menu(menu_name="Use/Equip")
                            )
                        ),
                        end="use/equip menu closed"
                    )
                    self.map.print()
                elif keyboard.is_pressed("d"):
                    self.log.time_logged(
                        start="drop menu opened",
                        func=lambda: self.menu.inventory(
                            menu_context=self.menu.context(
                                function=self.menu.function.drop,
                                header=lambda: self.menu.header.menu(menu_name="Drop")
                            )
                        ),
                        end="drop menu closed"
                    )
                    self.map.print()
                elif keyboard.is_pressed("i"):
                    if len(self.player.cell.inventory) == 0:
                        self.map.print()
                        self.print(f"There is nothing to {style_text('interact', 'action')} with or {style_text('pick up', 'action')}.")
                        continue
                    _object = self.player.cell.object
                    if isinstance(_object, DungeonItem):
                        self.map.print()
                        if len(self.player.inventory) == self.player.max_inventory:
                            self.print(f"Your {style_text('inventory', 'inventory')} is full!")
                            self.player.cell.print_inventory()
                            continue
                        item = _object
                        self.print(f"You {style_text('picked up', 'action')} a {style_text(item.name, 'item')}.")
                        self.player.cell.item_pickup()
                        self.player.cell.print_inventory()
                    elif isinstance(_object, DungeonTrader):
                        trader = _object
                        self.log.time_logged(
                            start=f"trading with {trader.occupation}",
                            func=lambda: self.menu.inventory(
                                menu_context=self.menu.context(
                                    function=self.menu.function.trader,
                                    header=lambda: self.menu.header.trader(trader=trader),
                                    trader=trader
                                )
                            ),
                            end=f"stopped trading"
                        )
                        self.map.print()
                elif keyboard.is_pressed("p"):
                    self.time.pause_menu()

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
