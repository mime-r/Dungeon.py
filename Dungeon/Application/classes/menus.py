"""Full-screen interaction menus: pack management, tile pickup, trade, healer."""

from rich.table import Table

from .. import input as keys
from ..utils import style_text, clear_screen
from .items import DungeonWeapon, DungeonInventory, DungeonPotion, DungeonScroll, DungeonOrb


def item_detail(item) -> str:
    """A short stat string for an item, shown in menus."""
    if isinstance(item, DungeonWeapon):
        lo, hi = item.attack_range
        return f"Atk {item.base_attack} (+{lo}-{hi}), {item.accuracy}% acc"
    if isinstance(item, DungeonPotion):
        return f"heals +{item.hp_change} HP"
    if isinstance(item, DungeonScroll):
        return item.effect.replace("_", " ").title()
    if isinstance(item, DungeonInventory):
        return f"+{item.inventory} pack slots"
    if isinstance(item, DungeonOrb):
        return "the win objective"
    return ""


class DungeonMenu:
    """Renders interaction menus and applies the chosen action."""

    def __init__(self, game) -> None:
        self.game = game

    # --- shared helpers -------------------------------------------------
    def _read_index(self, count: int) -> int | None:
        while True:
            key = keys.read_key()
            if key in (keys.ESC, "q"):
                return None
            if key.isdigit():
                n = int(key)
                if 1 <= n <= count:
                    return n - 1

    def _fists(self):
        return self.game.db.item_db.search_item(name="Fists")

    def _name(self, item) -> str:
        return self.game.display_name(item)

    def _detail(self, item) -> str:
        rec = self.game.ident.get(getattr(item, "name", None))
        if rec and not rec["identified"]:
            return "[flavor]unidentified[/flavor]"
        return item_detail(item)

    # --- pack (use / equip / unequip / drop) ---------------------------
    def pack(self) -> None:
        game, player = self.game, self.game.player
        while True:
            inv = player.inventory
            clear_screen()
            full = len(inv) >= player.max_inventory
            header = (
                f"[menu_header]Pack[/menu_header]  [inventory]{len(inv)}/{player.max_inventory}[/inventory]"
                + ("   [warn]FULL[/warn]" if full else "")
            )
            game.print(header, highlight=False)
            game.print(f"Equipped: {style_text(self._name(player.equipped), 'weapons')}  "
                       f"[flavor]({item_detail(player.equipped)})[/flavor]\n", highlight=False)
            if not inv:
                game.print("Your pack is empty.", highlight=False)
                game.print(f"\nPress {style_text('esc', 'controls')} to return.", highlight=False)
                keys.read_key()
                return
            table = Table(expand=False, border_style="grey37")
            table.add_column("#", style="controls", justify="right")
            table.add_column("Item", style="item")
            table.add_column("Details", style="flavor")
            table.add_column("", style="success")
            for i, it in enumerate(inv, 1):
                equipped = "equipped" if it is player.equipped else ""
                table.add_row(str(i), self._name(it), self._detail(it), equipped)
            game.print(table)
            game.print(f"\n{style_text('number', 'controls')} to select an item, "
                       f"{style_text('esc', 'controls')} to exit.", highlight=False)
            idx = self._read_index(len(inv))
            if idx is None:
                return
            if self._item_actions(idx):
                return  # quaffing/reading closes the pack so the effect is visible at once

    def _item_actions(self, idx: int) -> bool:
        game, player = self.game, self.game.player
        item = player.inventory[idx]
        if isinstance(item, DungeonWeapon):
            verb = "unequip" if item is player.equipped else "wield"
        elif isinstance(item, DungeonPotion):
            verb = "quaff"
        elif isinstance(item, DungeonScroll):
            verb = "read"
        elif isinstance(item, DungeonInventory):
            verb = "wear"
        else:
            verb = "use"
        rec = game.ident.get(getattr(item, "name", None))
        unidentified = bool(rec and not rec["identified"])
        desc = "An unidentified item — use it to discover what it does." if unidentified else item.description
        clear_screen()
        game.print(f"{style_text(self._name(item), 'item')}  [flavor]{self._detail(item)}[/flavor]\n"
                   f"{desc}\n", highlight=False)
        game.print(f"{style_text('e', 'controls')} {verb}   "
                   f"{style_text('d', 'controls')} drop   "
                   f"{style_text('esc', 'controls')} back", highlight=False)
        key = keys.read_key()
        if key == "e":
            return self._primary(item, idx, verb)
        if key == "d":
            self._drop(item, idx)
        return False

    def _primary(self, item, idx: int, verb: str) -> bool:
        """Apply the item's primary action. Returns True if the pack should close
        (i.e. a consumable was used, so the player can see the effect at once)."""
        game, player = self.game, self.game.player
        if isinstance(item, DungeonWeapon):
            if item is player.equipped:
                player.equipped = self._fists()
                game.message(f"You put away the {style_text(item.name, 'weapons')}.")
            else:
                player.equipped = item
                game.message(f"You wield the {style_text(item.name, 'weapons')}.")
            return False
        if isinstance(item, DungeonInventory):
            player.max_inventory += item.inventory
            player.inventory.pop(idx)
            game.message(f"You sling the {style_text(item.name, 'item')} over your shoulders. "
                         f"[inventory](+{item.inventory} slots)[/inventory]")
            return False
        if isinstance(item, DungeonPotion):
            player.inventory.pop(idx)
            game.apply_potion(item)
            return True
        if isinstance(item, DungeonScroll):
            if game.use_scroll(item):
                player.inventory.remove(item)
            return True
        return False

    def _drop(self, item, idx: int) -> None:
        game, player = self.game, self.game.player
        if item is player.equipped:
            player.equipped = self._fists()
            game.message(f"You unequip and drop the {style_text(item.name, 'weapons')}.")
        else:
            game.message(f"You drop the {style_text(self._name(item), 'item')}.")
        player.inventory.pop(idx)
        player.cell.items.append(item)

    # --- identify (choose an unidentified pack item) -------------------
    def choose_unidentified(self, exclude=None):
        """Let the player pick one unidentified pack item to identify. Returns it or None."""
        game, player = self.game, self.game.player
        items = [
            it for it in player.inventory
            if it is not exclude
            and (rec := game.ident.get(getattr(it, "name", None))) and not rec["identified"]
        ]
        if not items:
            return None
        clear_screen()
        game.print("[menu_header]Identify which item?[/menu_header]\n", highlight=False)
        table = Table(expand=False, border_style="grey37")
        table.add_column("#", style="controls", justify="right")
        table.add_column("Item", style="item")
        for i, it in enumerate(items, 1):
            table.add_row(str(i), self._name(it))
        game.print(table)
        game.print(f"\n{style_text('number', 'controls')} identify   "
                   f"{style_text('esc', 'controls')} cancel", highlight=False)
        idx = self._read_index(len(items))
        return None if idx is None else items[idx]

    # --- pick up from the tile you stand on ----------------------------
    def pickup_menu(self, cell) -> int:
        """Let the player choose which of several stacked items to take. Returns count."""
        game, player = self.game, self.game.player
        picked = 0
        while cell.items:
            clear_screen()
            full = len(player.inventory) >= player.max_inventory
            game.print(f"[menu_header]Items here[/menu_header]  "
                       f"[inventory]Pack {len(player.inventory)}/{player.max_inventory}[/inventory]"
                       + ("   [warn]FULL[/warn]" if full else ""), highlight=False)
            table = Table(expand=False, border_style="grey37")
            table.add_column("#", style="controls", justify="right")
            table.add_column("Item", style="item")
            table.add_column("Details", style="flavor")
            for i, it in enumerate(cell.items, 1):
                table.add_row(str(i), self._name(it), self._detail(it))
            game.print(table)
            game.print(f"\n{style_text('number', 'controls')} take one   "
                       f"{style_text('a', 'controls')} take all   "
                       f"{style_text('esc', 'controls')} done", highlight=False)
            key = keys.read_key()
            if key in (keys.ESC, "q"):
                break
            if key == "a":
                for it in list(cell.items):
                    if game.collect_item(it):
                        picked += 1
                    else:
                        break
                continue
            if key.isdigit():
                n = int(key)
                if 1 <= n <= len(cell.items):
                    if game.collect_item(cell.items[n - 1]):
                        picked += 1
        return picked

    # --- trader ---------------------------------------------------------
    def trader(self, trader) -> str | None:
        """Returns 'swap' if the player chose to step past the trader."""
        while True:
            stock = trader.stuff
            clear_screen()
            self.game.print(
                f"{style_text(trader.name, 'name')} — {style_text(trader.occupation, 'occupation')}"
                f"   (your gold: [coin]{self.game.player.coins}[/coin])", highlight=False)
            if stock:
                table = Table(title="For sale", title_style="menu_header", expand=False, border_style="grey37")
                table.add_column("#", style="controls", justify="right")
                table.add_column("Item", style="item")
                table.add_column("Cost", style="coin", justify="right")
                table.add_column("Details", style="flavor")
                for i, it in enumerate(stock, 1):
                    table.add_row(str(i), self._name(it), str(it.cost), self._detail(it))
                self.game.print(table)
            else:
                self.game.print("\nThe stall is bare.", highlight=False)
            self.game.print(f"\n{style_text('number', 'controls')} buy   "
                            f"{style_text('space', 'controls')} step past   "
                            f"{style_text('esc', 'controls')} leave", highlight=False)
            key = keys.read_key()
            if key in (keys.ESC, "q"):
                return None
            if key == keys.SPACE:
                return "swap"
            if key.isdigit() and stock:
                n = int(key)
                if 1 <= n <= len(stock):
                    self._buy(trader, n - 1)

    def _buy(self, trader, idx: int) -> None:
        game, player = self.game, self.game.player
        item = trader.stuff[idx]
        if player.coins < item.cost:
            game.message(f"You can't afford the {style_text(item.name, 'item')}.")
            return
        if len(player.inventory) >= player.max_inventory:
            game.message("Your pack is full.")
            return
        player.coins -= item.cost
        player.inventory.append(item)
        trader.stuff.pop(idx)
        game.message(f"You buy the {style_text(self._name(item), 'item')} for [coin]{item.cost}[/coin] gold.")

    # --- healer ---------------------------------------------------------
    def healer(self, healer) -> str | None:
        """Returns 'swap' if the player chose to step past the healer."""
        game, player = self.game, self.game.player
        rate = healer.heal_cost_per_hp
        while True:
            clear_screen()
            missing = player.max_health - player.health
            full_cost = missing * rate
            affordable_hp = min(missing, player.coins // rate) if rate else missing
            self.game.print(
                f"{style_text(healer.name, 'name')} — {style_text('Healer', 'occupation')}"
                f"   (your gold: [coin]{player.coins}[/coin])", highlight=False)
            if missing <= 0:
                self.game.print("\n\"You are hale and whole, friend.\"", highlight=False)
            else:
                self.game.print(
                    f"\n\"I mend wounds for [coin]{rate}[/coin] gold per point.\"\n"
                    f"Full heal ({missing} HP) costs [coin]{full_cost}[/coin] gold.", highlight=False)
            self.game.print(
                f"\n{style_text('enter', 'controls')} heal {affordable_hp} HP "
                f"([coin]{affordable_hp * rate}[/coin] gold)   "
                f"{style_text('space', 'controls')} step past   "
                f"{style_text('esc', 'controls')} leave", highlight=False)
            key = keys.read_key()
            if key in (keys.ESC, "q"):
                return None
            if key == keys.SPACE:
                return "swap"
            if key == keys.ENTER and affordable_hp > 0:
                player.coins -= affordable_hp * rate
                player.health += affordable_hp
                game.message(f"The healer tends your wounds. [heal](+{affordable_hp} HP)[/heal]")
