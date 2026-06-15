import datetime
import os
import sys
import time
import operator
import traceback
import random

from tinydb import TinyDB, Query
from rich.panel import Panel

from . import input as keys
from .config import config
from .utils import style_text, clear_screen
from .classes.map import DungeonMap, DungeonPlayer
from .classes.menus import DungeonMenu
from .classes.items import DungeonOrb
from .classes.database import DungeonDatabase
from .classes.misc import DungeonTimeData
from .classes.people import DungeonTrader, DungeonHealer
from .classes.levelgen import generate_level

print("Loading...")

T = config.terrain

# Weapons seeded into vault treasure, by how deep you are.
_VAULT_WEAPONS = ["Short Sword", "Mace", "Spear", "Long Sword", "War Axe"]


class Dungeon:
    """Main game controller: owns the floors, player, database, and game loop."""

    def __init__(self, logger, rich_console) -> None:
        self.log = logger
        self.rich_console = rich_console
        self.print = self.rich_console.print
        self.over = False

        clear_screen()
        self.menu = DungeonMenu(game=self)
        self.moves = 0
        self.depth = 1
        self.levels: dict[int, DungeonMap] = {}
        # Developer god mode: enable from the start with DUNGEON_GODMODE=1, or toggle in-game with `~`.
        self.godmode = os.environ.get("DUNGEON_GODMODE") == "1"

        from .classes.ui import DungeonUI
        self.ui = DungeonUI(game=self)

        self.db = DungeonDatabase(game=self)
        self.leaderboard = TinyDB("leaderboard.json")
        self.leaderboardQuery = Query()

        self.player = DungeonPlayer(
            health=config.player.health,
            max_health=config.player.max_health,
            max_inventory=config.player.max_inventory,
            coins=config.player.coins,
            xp=config.player.xp,
            equipped=self.db.item_db.search_item(name="Fists"),
            game=self,
        )
        for _ in range(2):
            self.player.inventory.append(self.db.item_db.search_item(name="Weak Healing Potion"))

        while True:
            self.session_id = random.getrandbits(64)
            if not self.leaderboard.search(self.leaderboardQuery.session_id == self.session_id):
                break

        self.player.name = input("Hello adventurer, what is your name? (Enter for random)\n> ").strip()
        if not self.player.name:
            from .classes.people import DungeonPeople
            self.player.name = DungeonPeople.generate_name()
            print(f"You are {self.player.name}.")
            time.sleep(1.2)

        self.enter_level(1, mode="down")
        self.message(f"[flavor]You descend into the dungeon. Somewhere far below lies the Orb of Zot.[/flavor]")
        self.log.info("dungeon initialised")

    # --- messaging ------------------------------------------------------
    def message(self, text: str, drop: int | None = None) -> None:
        self.ui.message(text, drop=drop)

    def render(self) -> None:
        self.ui.render()

    # --- level generation & travel -------------------------------------
    def _new_level(self, depth: int) -> DungeonMap:
        is_last = depth >= config.depth.floors
        layout = generate_level(is_last=is_last, depth=depth)
        level = DungeonMap(game=self, layout=layout)
        self._populate(level, depth, is_last)
        return level

    def _populate(self, level: DungeonMap, depth: int, is_last: bool) -> None:
        pool = list(level.floor_cells)
        random.shuffle(pool)
        suy, sux = level.stairs_up

        def far_cell():
            while pool:
                y, x = pool.pop()
                if abs(y - suy) + abs(x - sux) > 3:
                    return (y, x)
            return None

        # Monsters (count scales with depth).
        count = config.spawn.enemies_base + config.spawn.enemies_per_depth * (depth - 1)
        for _ in range(count):
            loader = self.db.enemy_db.random_for_depth(depth)
            spot = far_cell()
            if loader and spot:
                enemy = loader.load()
                level.place_occupant(enemy, *spot)
                level.enemies.append(enemy)

        # NPCs spawn inside open rooms (never in 1-wide corridors, so they can't wall you
        # in), and none appear on the Orb floor.
        if not is_last:
            floor_set = set(level.floor_cells)
            room_pool = [
                (y, x) for room in level.rooms for (y, x) in room.interior()
                if (y, x) in floor_set and abs(y - suy) + abs(x - sux) > 3
            ]
            random.shuffle(room_pool)

            def room_cell():
                while room_pool:
                    y, x = room_pool.pop()
                    if level.matrix[y][x].occupant is None:
                        return (y, x)
                return far_cell()

            for loader in random.sample(self.db.people_db.traders(),
                                        k=min(config.spawn.npcs_per_floor, len(self.db.people_db.traders()))):
                spot = room_cell()
                if not spot:
                    break
                npc = loader.load()
                npc.symbol = loader.data.symbol
                npc.style = npc.occupation.lower()
                level.place_occupant(npc, *spot)
                level.npcs.append(npc)

        # Loose loot on the floor (placed on any open floor tile, never inside a vault).
        for _ in range(config.spawn.floor_potions):
            self._scatter(level, self._depth_potion(depth))
        for _ in range(config.spawn.floor_scrolls):
            self._scatter(level, random.choice(self.db.item_db.scrolls))
        for _ in range(config.spawn.floor_weapons):
            self._scatter(level, random.choice(self.db.item_db.weapons[1:]))
        for _ in range(config.spawn.gold_piles):
            cell = self._floor_cell(level)
            if cell:
                cell.gold += random.randint(2, 6 + depth * 2)

        # Vault treasure (or the Orb chamber on the last floor).
        self._fill_vault(level, depth, is_last)

    def _scatter(self, level, item) -> None:
        cell = self._floor_cell(level)
        if cell and item:
            cell.items.append(item)

    def _floor_cell(self, level):
        if not level.floor_cells:
            return None
        y, x = random.choice(level.floor_cells)
        return level.matrix[y][x]

    def _depth_potion(self, depth: int):
        roll = random.randint(0, 9) + depth
        name = "Strong Healing Potion" if roll > 9 else "Medium Healing Potion" if roll > 4 else "Weak Healing Potion"
        return self.db.item_db.search_item(name=name)

    def _fill_vault(self, level, depth: int, is_last: bool) -> None:
        if not level.vault_cells:
            return
        cells = list(level.vault_cells)
        random.shuffle(cells)
        if is_last:
            oy, ox = cells.pop()
            level.matrix[oy][ox].items.append(DungeonOrb())
            level.matrix[oy][ox].gold += random.randint(40, 80)
            loader = self.db.enemy_db.search_enemy(name="Orb Guardian")
            if loader and cells:
                gy, gx = min(cells, key=lambda c: abs(c[0] - oy) + abs(c[1] - ox))
                boss = loader.load()
                boss.awake = True
                level.place_occupant(boss, gy, gx)
                level.enemies.append(boss)
            if cells:  # the legendary blade rewards reaching the bottom, on its own tile
                sy, sx = cells.pop()
                level.matrix[sy][sx].items.append(self.db.item_db.search_item(name="Sword of Zot"))
        else:
            wy, wx = cells.pop()
            weapon_name = _VAULT_WEAPONS[min(depth - 1, len(_VAULT_WEAPONS) - 1)]
            level.matrix[wy][wx].items.append(self.db.item_db.search_item(name=weapon_name))
            if cells:
                gy, gx = cells.pop()
                level.matrix[gy][gx].gold += random.randint(15, 30 + depth * 5)
            if cells:
                py, px = cells.pop()
                level.matrix[py][px].items.append(self.db.item_db.search_item(name="Strong Healing Potion"))

    def enter_level(self, depth: int, mode: str) -> None:
        if depth not in self.levels:
            self.levels[depth] = self._new_level(depth)
        self.depth = depth
        self.map = self.levels[depth]
        if mode == "up" and self.map.stairs_down:
            self.player.location = self.map.stairs_down
        else:
            self.player.location = self.map.stairs_up
        self.map.update_fov()
        if mode == "down":
            self.message(f"[stairs]You arrive on Depth {depth}.[/stairs]")
        else:
            self.message(f"[stairs]You climb to Depth {depth}.[/stairs]")

    # --- turn engine ----------------------------------------------------
    def take_turn(self) -> None:
        self.moves += 1
        self.time.add()
        self.world_tick()
        if self.player.health <= 0:
            self.game_over("dead")
            return
        if self.map.auto_detect_secret():
            self.message("[warn]You notice a hidden door nearby![/warn]")
        self.map.update_fov()

    def world_tick(self) -> None:
        for enemy in list(self.map.enemies):
            if enemy.health > 0:
                enemy.act()
                if self.player.health <= 0:
                    return

    def on_enemy_death(self, enemy) -> None:
        self.player.xp += enemy.xp_drop
        self.map.remove_occupant(enemy)
        if enemy in self.map.enemies:
            self.map.enemies.remove(enemy)
        ey, ex = enemy.location
        self.map.matrix[ey][ex].gold += enemy.coin_drop
        self.message(enemy.texts.death)
        if enemy.tier == "boss":
            self.message("[success]The guardian shatters! The Orb of Zot lies unguarded.[/success]")

    def awaken_floor(self) -> None:
        for enemy in self.map.enemies:
            enemy.awake = True

    # --- player commands ------------------------------------------------
    def interact_npc(self, npc) -> bool:
        """Open an NPC's menu. Returns True if a turn was spent (the player stepped past)."""
        result = None
        if isinstance(npc, DungeonTrader):
            result = self.menu.trader(npc)
        elif isinstance(npc, DungeonHealer):
            result = self.menu.healer(npc)
        if result == "swap":
            return self.swap_with_npc(npc)
        return False

    def swap_with_npc(self, npc) -> bool:
        """Trade places with a non-hostile NPC so corridors are never permanently blocked."""
        py, px = self.player.location
        ny, nx = npc.location
        self.map.move_occupant(npc, py, px)
        self.player.location = (ny, nx)
        self.player._on_enter(self.player.cell)
        self.message(f"You slip past {style_text(npc.name, 'name')}.")
        return True

    def collect_item(self, item) -> bool:
        """Move one item from the player's tile into the pack (or claim the Orb). True if taken."""
        cell = self.player.cell
        if item not in cell.items:
            return False
        if isinstance(item, DungeonOrb):
            cell.items.remove(item)
            self.player.has_orb = True
            self.message("[orb]You hoist the Orb of Zot! Its light floods the chamber.[/orb]")
            self.message("[warn]The dungeon shudders awake. Flee to the surface![/warn]")
            self.awaken_floor()
            return True
        if len(self.player.inventory) >= self.player.max_inventory:
            self.message("Your pack is full.")
            return False
        cell.items.remove(item)
        self.player.inventory.append(item)
        self.message(f"You pick up the {style_text(item.name, 'item')}.")
        return True

    def pickup(self) -> bool:
        cell = self.player.cell
        if not cell.items:
            self.message("There is nothing here to pick up.")
            return False
        if len(cell.items) == 1:
            return self.collect_item(cell.items[0])
        return self.menu.pickup_menu(cell) > 0

    def descend(self) -> None:
        if self.player.cell.terrain == T.STAIRS_DOWN:
            self.enter_level(self.depth + 1, mode="down")
        else:
            self.message("There are no stairs down here.")

    def ascend(self) -> None:
        if self.player.cell.terrain != T.STAIRS_UP:
            self.message("There are no stairs up here.")
            return
        if self.depth == 1:
            if self.player.has_orb:
                self.game_over("win")
            else:
                self.message("[warn]You cannot abandon the dungeon without the Orb of Zot.[/warn]")
        else:
            self.enter_level(self.depth - 1, mode="up")

    def use_scroll(self, scroll) -> None:
        if scroll.effect == "magic_mapping":
            self.map.reveal_all()
            self.message(f"You read the {style_text(scroll.name, 'item')}. The floor's layout floods into your mind.")
        elif scroll.effect == "teleport":
            self.player.location = self.map.random_walkable()
            self.map.update_fov()
            self.message(f"You read the {style_text(scroll.name, 'item')} and blink across the floor.")

    def search(self) -> None:
        if self.map.search(self.player.y, self.player.x):
            self.message("[warn]You find a hidden door![/warn]")
        else:
            self.message("You search the nearby walls but find nothing.")

    # --- main loop ------------------------------------------------------
    def gameloop(self) -> None:
        self.time = DungeonTimeData(game=self)
        self.log.info(f"started game at {time.time():.2f}")
        self.render()
        while not self.over:
            key = keys.read_key()
            self.handle(key)
            if not self.over:
                self.render()

    def handle(self, key: str) -> None:
        direction = keys.read_direction(key)
        if direction:
            if self.player.move(direction):
                self.take_turn()
            return
        if key == "g":
            if self.pickup():
                self.take_turn()
        elif key in ("d", "i"):
            self.menu.pack()
        elif key == ">":
            self.descend()
        elif key == "<":
            self.ascend()
        elif key == "s":
            self.search()
            self.take_turn()
        elif key in (".", keys.SPACE):
            self.message("You wait.")
            self.take_turn()
        elif key == "p":
            self.time.pause_menu()
        elif key == "~":
            self.godmode = not self.godmode
            if self.godmode:
                self.map.reveal_all()
            self.message(f"[warn]Developer god mode {'ENABLED' if self.godmode else 'disabled'}.[/warn]")
        elif key == "?":
            self.help_screen()
        elif key == keys.ESC:
            self.over = True
            self.log.info("game exited by player")
            clear_screen()
            print("Exiting [Dungeon]...")
            sys.exit()

    def help_screen(self) -> None:
        clear_screen()
        self.print(Panel(
            "[menu_header]Dungeon.py — Controls[/menu_header]\n\n"
            "[controls]arrows[/controls] or [controls]hjkl[/controls]  move / attack (walk into a monster)\n"
            "[controls]yubn[/controls]  diagonal movement (nw / ne / sw / se)\n"
            "[controls]g[/controls]  pick up items on your tile (choose which, or take all)\n"
            "[controls]i[/controls] / [controls]d[/controls]  open pack — use, equip, unequip, drop\n"
            "[controls]>[/controls] / [controls]<[/controls]  descend / ascend stairs\n"
            "[controls]s[/controls]  search adjacent walls for secret doors\n"
            "[controls].[/controls] or [controls]space[/controls]  wait one turn\n"
            "[controls]p[/controls]  pause    [controls]esc[/controls]  quit\n\n"
            "[flavor]At a trader/healer, press [controls]space[/controls] to step past them.[/flavor]\n"
            "[flavor]Developer: [controls]~[/controls] toggles god mode (or set DUNGEON_GODMODE=1).[/flavor]\n\n"
            "[flavor]Descend to the bottom, seize the Orb of Zot, and escape to the surface.[/flavor]\n\n"
            f"Press {style_text('any key', 'controls')} to return.",
            border_style="grey37"))
        keys.read_key()

    # --- endgame --------------------------------------------------------
    def record_leaderboard(self, outcome: str) -> None:
        self.leaderboard.insert({
            "name": self.player.name,
            "outcome": outcome,
            "depth": self.depth,
            "orb": self.player.has_orb,
            "time": round(self.time.elapsed, 3),
            "moves": self.moves,
            "xp": self.player.xp,
            "datetime": str(datetime.datetime.now()),
            "session_id": self.session_id,
        })
        winners = sorted(
            [e for e in self.leaderboard.all() if e.get("outcome") == "win"],
            key=operator.itemgetter("time"))
        self.print(f"\n{style_text('[ Hall of Champions ]', 'menu_header')}\n", highlight=False)
        if not winners:
            self.print("[flavor]No one has escaped with the Orb yet. Be the first.[/flavor]", highlight=False)
        for i, e in enumerate(winners[:10]):
            here = style_text("you", "success") if e["session_id"] == self.session_id else e["name"]
            self.print(f"{i + 1}. {here} — {e['time']}s, {e['moves']} turns", highlight=False)

    def game_over(self, how: str) -> None:
        self.over = True
        clear_screen()
        if how == "win":
            self.print(Panel(
                f"[success]You escape the dungeon clutching the Orb of Zot![/success]\n"
                f"[name]{self.player.name}[/name], you are victorious.\n"
                f"Turns: {self.moves}   Time: {self.time.elapsed:.1f}s   XP: {self.player.xp}",
                title="[success]VICTORY[/success]", border_style="green"))
            self.record_leaderboard("win")
        else:
            self.print(Panel(
                f"[fail]You have fallen on Depth {self.depth}.[/fail]\n"
                f"[name]{self.player.name}[/name] will be remembered... briefly.\n"
                f"Turns: {self.moves}   Time: {self.time.elapsed:.1f}s   XP: {self.player.xp}",
                title="[fail]DEATH[/fail]", border_style="red"))
            self.record_leaderboard("death")
        self.print(f"\nPress {style_text('any key', 'controls')} to exit.", highlight=False)
        keys.read_key()
        sys.exit()

    @staticmethod
    def __start__(logger, rich_console) -> None:
        try:
            d = Dungeon(logger=logger, rich_console=rich_console)
            d.log.info("dungeon set up is done, starting game")
            d.gameloop()
        except SystemExit:
            raise
        except KeyboardInterrupt:
            print("Exiting [Dungeon]...")
            logger.info(f"game exited by KeyboardInterrupt at {time.time():.2f}")
            sys.exit()
        except Exception as e:
            logger.fatal(f"\n{''.join(traceback.format_tb(e.__traceback__))}\n\n{str(e)}")
