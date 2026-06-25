"""Full-screen interaction menus: pack management, tile pickup, trade, healer."""

import time

from rich.live import Live
from rich.table import Table
from rich.text import Text

from .. import input as keys
from ..utils import style_text, clear_screen
from .items import (
    DungeonWeapon, DungeonInventory, DungeonPotion, DungeonScroll, DungeonShard,
    DungeonThrowable, DungeonArmour, DungeonSpellBook,
)
from .skills import SkillState
from .magic import calculate_failure, staff_damage_multiplier, staff_school

_SPINNER = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]


def item_detail(item) -> str:
    """A short stat string for an item, shown in menus."""
    if isinstance(item, DungeonWeapon):
        lo, hi = item.attack_range
        hands = f"{item.hands}-handed"
        ench = getattr(item, "enchant", 0)
        return f"Atk {item.base_attack + ench} (+{lo}-{hi}), {item.accuracy + ench}% acc, {hands}"
    if isinstance(item, DungeonPotion):
        return f"heals +{item.hp_change} HP"
    if isinstance(item, DungeonScroll):
        return item.effect.replace("_", " ").title()
    if isinstance(item, DungeonInventory):
        return f"+{item.inventory} pack slots"
    if isinstance(item, DungeonArmour):
        ench = getattr(item, "enchant", 0)
        stat = f"SH {item.sh + ench}" if item.slot == "shield" else f"AC {item.ac + ench}"
        enc = f", enc {item.encumbrance}" if item.encumbrance else ""
        return f"{stat}{enc} ({item.slot})"
    if isinstance(item, DungeonShard):
        return "sigil fragment (1 of 3)"
    if isinstance(item, DungeonSpellBook):
        return f"teaches {len(item.spells)} spell(s)"
    if isinstance(item, DungeonThrowable):
        lo, hi = item.attack_range
        return f"Atk {item.base_attack} (+{lo}-{hi}), {item.accuracy}% acc, range {item.range}, x{item.count}"
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
    _PAGE_SIZE = 9

    # Item-type rank for the auto-sort. Lower number = shown first.
    _ITEM_SORT_RANK = {
        "DungeonWeapon":     0,
        "DungeonArmour":     1,
        "DungeonThrowable":  2,
        "DungeonSpellBook":  3,
        "DungeonPotion":     4,
        "DungeonScroll":     5,
        "DungeonInventory":  6,
        "DungeonShard":      7,
    }

    def _sort_inventory(self) -> None:
        """Permanently reorder the inventory: equipped first, then by type,
        then by name, then by enchantment (descending). Uses stable sort so
        the existing within-bucket order is preserved."""
        player = self.game.player

        def sort_key(it):
            cls = type(it).__name__
            is_worn = isinstance(it, DungeonArmour) and player.armour.get(it.slot) is it
            equipped = (it is player.equipped) or is_worn
            # Equipped items get a small negative bonus so they bubble to the top.
            eq_rank = 0 if equipped else 1
            type_rank = self._ITEM_SORT_RANK.get(cls, 99)
            name = getattr(it, "name", "")
            ench = getattr(it, "enchant", 0)
            # Negate enchantment so higher enchantment comes first within a name.
            return (eq_rank, type_rank, name.lower(), -ench)

        player.inventory.sort(key=sort_key)

    def pack(self) -> None:
        game, player = self.game, self.game.player
        page = 0
        while True:
            inv = player.inventory
            total = len(inv)
            # Equipped items always shown first, even before any auto-sort.
            # Build a view: equipped items, then the rest in original order.
            eq_set = {id(player.equipped)}
            for slot, piece in player.armour.items():
                if piece is not None:
                    eq_set.add(id(piece))
            eq_idx = [i for i, it in enumerate(inv) if id(it) in eq_set]
            other_idx = [i for i, it in enumerate(inv) if id(it) not in eq_set]
            view_idx = eq_idx + other_idx
            view_total = len(view_idx)
            pages = max(1, (view_total + self._PAGE_SIZE - 1) // self._PAGE_SIZE)
            page = max(0, min(page, pages - 1))
            start = page * self._PAGE_SIZE
            end = min(start + self._PAGE_SIZE, view_total)
            page_view = view_idx[start:end]  # real indices into player.inventory
            page_items = [inv[i] for i in page_view]
            # True if every item on this page is equipped.
            page_all_eq = bool(page_items) and all(
                it is player.equipped
                or (isinstance(it, DungeonArmour) and player.armour.get(it.slot) is it)
                for it in page_items
            )

            clear_screen()
            full_flag = total >= player.max_inventory
            page_info = f"  [flavor]Page {page + 1}/{pages}[/flavor]" if pages > 1 else ""
            header = (
                f"[menu_header]Pack[/menu_header]  [inventory]{total}/{player.max_inventory}[/inventory]"
                + ("   [warn]FULL[/warn]" if full_flag else "")
                + page_info
            )
            game.print(header, highlight=False)
            game.print(f"Equipped: {style_text(self._name(player.equipped), 'weapons')}  "
                       f"[flavor]({item_detail(player.equipped)})[/flavor]", highlight=False)
            worn = [a for a in player.armour.values() if a]
            worn_str = ", ".join(style_text(self._name(a), 'armour') for a in worn) if worn else "none"
            game.print(f"Armour: {worn_str}  "
                       f"[flavor](AC {player.armor_class()}, EV {player.evasion()})[/flavor]\n", highlight=False)
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
            # Sub-header row when the page is entirely equipped items.
            if page_all_eq and page_items:
                table.add_row("", f"[success]-- equipped --[/success]", "", "")
            prev_was_eq = page_all_eq and bool(page_items)
            for i, it in enumerate(page_items, 1):
                is_worn = isinstance(it, DungeonArmour) and player.armour.get(it.slot) is it
                equipped_now = (it is player.equipped or is_worn)
                # Drop the equipped sub-header when the first unequipped item appears.
                if prev_was_eq and not equipped_now:
                    table.add_row("", f"[flavor]-- pack --[/flavor]", "", "")
                    prev_was_eq = False
                equipped = "equipped" if equipped_now else ""
                table.add_row(str(i), self._name(it), self._detail(it), equipped)
            game.print(table)
            nav = ""
            if pages > 1:
                nav = f"  {style_text(',', 'controls')} prev  {style_text('.', 'controls')} next"
            game.print(f"\n{style_text('1-9', 'controls')} select item  "
                       f"{style_text('s', 'controls')} auto-sort"
                       f"{nav}  {style_text('esc', 'controls')} exit.", highlight=False)
            key = keys.read_key()
            if key in (keys.ESC, "q"):
                return
            if key == "," and page > 0:
                page -= 1
                continue
            if key == "." and page < pages - 1:
                page += 1
                continue
            if key in ("s", "S"):
                self._sort_inventory()
                page = 0
                game.message("[success]Pack auto-sorted.[/success]")
                continue
            if key.isdigit():
                n = int(key)
                if 1 <= n <= len(page_items):
                    # Map the page-local position back to the real inventory index.
                    idx = page_view[n - 1]
                    if self._item_actions(idx):
                        return

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
        elif isinstance(item, DungeonArmour):
            verb = "unequip" if player.armour.get(item.slot) is item else "wear"
        elif isinstance(item, DungeonThrowable):
            verb = None  # thrown via the f key in the field, not from the pack
        elif isinstance(item, DungeonSpellBook):
            verb = "read"
        else:
            verb = "use"
        rec = game.ident.get(getattr(item, "name", None))
        unidentified = bool(rec and not rec["identified"])
        desc = "An unidentified item — use it to discover what it does." if unidentified else item.description
        lore = rec.get("lore") if rec else None
        lore_line = f"\n[flavor]{lore}[/flavor]" if lore else ""
        clear_screen()
        game.print(f"{style_text(self._name(item), 'item')}  [flavor]{self._detail(item)}[/flavor]\n"
                   f"{desc}{lore_line}\n", highlight=False)
        action_hint = (f"{style_text('e', 'controls')} {verb}   " if verb else
                       f"[flavor](press {style_text('f', 'controls')} in the dungeon to throw)[/flavor]   ")
        game.print(f"{action_hint}"
                   f"{style_text('d', 'controls')} drop   "
                   f"{style_text('esc', 'controls')} back", highlight=False)
        key = keys.read_key()
        if key == "e" and verb:
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
                if getattr(item, "hands", "One") == "Two" and player.armour.get("shield"):
                    game.message("You can't wield a two-handed weapon while wearing a shield.")
                    return False
                player.equipped = item
                game.message(f"You wield the {style_text(item.name, 'weapons')}.")
            return False
        if isinstance(item, DungeonArmour):
            return self._toggle_armour(item)
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
        if isinstance(item, DungeonSpellBook):
            return self._read_spellbook(item, idx)
        return False

    def _toggle_armour(self, item) -> bool:
        game, player = self.game, self.game.player
        slot = item.slot
        if player.armour.get(slot) is item:
            player.armour[slot] = None
            game.message(f"You remove the {style_text(item.name, 'armour')}.")
            return False
        if slot == "shield" and getattr(player.equipped, "hands", "One") == "Two":
            game.message("You need both hands free for your weapon; you can't wear a shield.")
            return False
        player.armour[slot] = item
        game.message(f"You put on the {style_text(item.name, 'armour')}.")
        return False

    def _read_spellbook(self, book, idx: int) -> bool:
        game, player = self.game, self.game.player
        learned = 0
        for spell_name in book.spells:
            if any(s.name == spell_name for s in player.known_spells):
                continue
            spell = game.db.item_db.search_spell(spell_name)
            if spell:
                max_slots = self._max_spell_slots(player)
                used = sum(s.level for s in player.known_spells)
                if used + spell.level > max_slots:
                    game.message(f"[warn]Not enough spell slots to memorise {spell_name}.[/warn]")
                    continue
                player.known_spells.append(spell)
                game.message(f"[success]You memorise {style_text(spell_name, 'item')}.[/success]")
                learned += 1
        if learned:
            player.inventory.pop(idx)
            game.message(f"[flavor]The {style_text(book.name, 'item')} crumbles to dust.[/flavor]")
        else:
            game.message(f"[warn]You learn nothing new from the {style_text(book.name, 'item')}.[/warn]")
        return True

    def _drop(self, item, idx: int) -> None:
        game, player = self.game, self.game.player
        if item is player.equipped:
            player.equipped = self._fists()
            game.message(f"You unequip and drop the {style_text(item.name, 'weapons')}.")
        elif isinstance(item, DungeonArmour) and player.armour.get(item.slot) is item:
            player.armour[item.slot] = None
            game.message(f"You unequip and drop the {style_text(item.name, 'armour')}.")
        else:
            game.message(f"You drop the {style_text(self._name(item), 'item')}.")
        player.inventory.pop(idx)
        player.cell.items.append(item)

    # --- armour overview ------------------------------------------------
    def armor_ui(self) -> None:
        """Show a dedicated armour overview screen."""
        game, player = self.game, self.game.player
        clear_screen()
        game.print("[menu_header]Armour[/menu_header]\n", highlight=False)
        table = Table(expand=False, border_style="grey37")
        table.add_column("Slot", style="controls")
        table.add_column("Equipped", style="item")
        table.add_column("AC", style="armour", justify="right")
        table.add_column("SH", style="armour", justify="right")
        table.add_column("Enc", style="warn", justify="right")
        slots = [
            ("body", "Body"),
            ("shield", "Shield"),
            ("helmet", "Helmet"),
            ("cloak", "Cloak"),
            ("gloves", "Gloves"),
            ("boots", "Boots"),
        ]
        for slot_key, slot_label in slots:
            piece = player.armour.get(slot_key)
            if piece:
                name = self._name(piece)
                ac = str(piece.ac) if piece.ac else "-"
                sh = str(piece.sh) if piece.sh else "-"
                enc = str(piece.encumbrance) if piece.encumbrance else "-"
            else:
                name = "[flavor]—[/flavor]"
                ac = sh = enc = "-"
            table.add_row(slot_label, name, ac, sh, enc)
        game.print(table)
        total_enc = player.total_encumbrance()
        ev = player.evasion()
        game.print(
            f"\n[armour]Total AC[/armour]: {player.armor_class()}   "
            f"[armour]EV[/armour]: {ev}   "
            f"[warn]Encumbrance[/warn]: {total_enc}",
            highlight=False,
        )
        game.print(f"\nPress {style_text('esc', 'controls')} to return.", highlight=False)
        keys.read_key()

    # --- skill management -----------------------------------------------
    def skills_ui(self) -> None:
        """DCSS-style skill management screen."""
        game, player = self.game, self.game.player
        skills = player.skills
        if not skills:
            return
        letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        while True:
            clear_screen()
            mode_str = "Manual" if skills.manual_mode else "Automatic"
            header = f"[menu_header]Skills[/menu_header]   [flavor]{mode_str} training mode[/flavor]"
            game.print(header, highlight=False)
            game.print("Press letter to toggle state, '/' for mode, '=' for target, esc to exit.", highlight=False)
            table = Table(expand=False, border_style="grey37")
            table.add_column("Key", style="controls", justify="right")
            table.add_column("Skill", style="item")
            table.add_column("Level", style="level", justify="right")
            table.add_column("State", style="success")
            table.add_column("Apt", style="flavor", justify="right")
            table.add_column("Target", style="warn")
            for i, (name, skill) in enumerate(skills.skills.items()):
                if i >= len(letters):
                    break
                key = letters[i]
                level = f"{skill.level:5.1f}"
                if skill.state == SkillState.FOCUSED:
                    state_disp = "****"
                elif skill.state == SkillState.ENABLED:
                    state_disp = "++"
                else:
                    state_disp = ""
                apt = f"{skill.aptitude:+d}"
                target = ""
                if skill.target is not None:
                    target = "(TARGET MET)" if skill.level >= skill.target else f"(Target: {skill.target:.1f})"
                table.add_row(key, name, level, state_disp, f"[Apt: {apt}]", target)
            game.print(table)
            game.print(f"\n{style_text('letter', 'controls')} toggle   {style_text('/', 'controls')} mode   {style_text('=', 'controls')} target   {style_text('esc', 'controls')} exit", highlight=False)
            key = keys.read_key()
            if key in (keys.ESC, "q"):
                return
            if key == "/":
                skills.manual_mode = not skills.manual_mode
                continue
            if key == "=":
                self._set_skill_target(skills)
                continue
            ukey = key.upper()
            if ukey in letters:
                idx = letters.index(ukey)
                if idx < len(skills.skills):
                    s = list(skills.skills.values())[idx]
                    if s.state == SkillState.DISABLED:
                        s.state = SkillState.ENABLED
                    elif s.state == SkillState.ENABLED:
                        s.state = SkillState.FOCUSED
                    else:
                        s.state = SkillState.DISABLED

    def _set_skill_target(self, skills) -> None:
        """Prompt player to pick a skill and set a target level."""
        game = self.game
        letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        clear_screen()
        game.print("[menu_header]Set target for which skill?[/menu_header]\n", highlight=False)
        table = Table(expand=False, border_style="grey37")
        table.add_column("Key", style="controls", justify="right")
        table.add_column("Skill", style="item")
        table.add_column("Current", style="level", justify="right")
        for i, (name, skill) in enumerate(skills.skills.items()):
            if i >= len(letters):
                break
            table.add_row(letters[i], name, f"{skill.level:.1f}")
        game.print(table)
        game.print(f"\n{style_text('letter', 'controls')} select   {style_text('esc', 'controls')} cancel", highlight=False)
        key = keys.read_key()
        if key in (keys.ESC, "q"):
            return
        ukey = key.upper()
        if ukey in letters:
            idx = letters.index(ukey)
            if idx < len(skills.skills):
                skill = list(skills.skills.values())[idx]
                clear_screen()
                game.print(f"[menu_header]Set target for {skill.name}[/menu_header]", highlight=False)
                game.print(f"Current level: {skill.level:.1f}   Current target: {skill.target if skill.target is not None else 'None'}", highlight=False)
                game.print(f"Enter target (0-27, 0 = no target):", highlight=False)
                val = input("> ").strip()
                try:
                    target = float(val)
                    if 0 <= target <= 27:
                        if target == 0:
                            skill.target = None
                        else:
                            skill.target = target
                            if skill.level >= target:
                                skill.state = SkillState.DISABLED
                except ValueError:
                    pass

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

    # --- amnesia (choose a memorised spell to forget) ------------------
    def choose_spell_to_forget(self):
        """Let the player pick one memorised spell to forget. Returns spell or None."""
        game, player = self.game, self.game.player
        spells = player.known_spells
        if not spells:
            return None
        clear_screen()
        game.print("[menu_header]Forget which spell?[/menu_header]\n", highlight=False)
        table = Table(expand=False, border_style="grey37")
        table.add_column("#", style="controls", justify="right")
        table.add_column("Spell", style="item")
        table.add_column("Schools", style="flavor")
        table.add_column("Level", style="level", justify="right")
        for i, sp in enumerate(spells, 1):
            schools = " / ".join(sp.schools)
            table.add_row(str(i), sp.name, schools, str(sp.level))
        game.print(table)
        game.print(f"\n{style_text('number', 'controls')} forget   "
                   f"{style_text('esc', 'controls')} cancel", highlight=False)
        idx = self._read_index(len(spells))
        return None if idx is None else spells[idx]

    # --- enchant weapon / enchant armour -------------------------------
    def choose_enchantable_weapon(self, exclude=None):
        """Pick a weapon in the player's pack. Returns weapon or None."""
        game, player = self.game, self.game.player
        items = [it for it in player.inventory
                 if isinstance(it, DungeonWeapon) and it is not exclude]
        if not items:
            return None
        clear_screen()
        game.print("[menu_header]Enchant which weapon?[/menu_header]\n", highlight=False)
        table = Table(expand=False, border_style="grey37")
        table.add_column("#", style="controls", justify="right")
        table.add_column("Item", style="item")
        table.add_column("Enchant", style="level", justify="right")
        for i, it in enumerate(items, 1):
            ench = getattr(it, "enchant", 0)
            ench_str = f"+{ench}" if ench >= 0 else str(ench)
            table.add_row(str(i), self._name(it), ench_str)
        game.print(table)
        game.print(f"\n{style_text('number', 'controls')} select   "
                   f"{style_text('esc', 'controls')} cancel", highlight=False)
        idx = self._read_index(len(items))
        return None if idx is None else items[idx]

    def choose_enchantable_armour(self, exclude=None):
        """Pick a body armour or shield in the player's pack."""
        game, player = self.game, self.game.player
        items = [it for it in player.inventory
                 if isinstance(it, DungeonArmour)
                 and it.slot in ("body", "shield")
                 and it is not exclude]
        if not items:
            return None
        clear_screen()
        game.print("[menu_header]Enchant which armour?[/menu_header]\n", highlight=False)
        table = Table(expand=False, border_style="grey37")
        table.add_column("#", style="controls", justify="right")
        table.add_column("Item", style="item")
        table.add_column("Slot", style="flavor")
        table.add_column("AC", style="armour", justify="right")
        table.add_column("Enchant", style="level", justify="right")
        for i, it in enumerate(items, 1):
            ench = getattr(it, "enchant", 0)
            ench_str = f"+{ench}" if ench >= 0 else str(ench)
            table.add_row(str(i), self._name(it), it.slot, str(it.ac), ench_str)
        game.print(table)
        game.print(f"\n{style_text('number', 'controls')} select   "
                   f"{style_text('esc', 'controls')} cancel", highlight=False)
        idx = self._read_index(len(items))
        return None if idx is None else items[idx]

    # --- blinking target ------------------------------------------------
    def choose_blink_target(self):
        """Pick a walkable, unoccupied, in-sight tile to blink to."""
        game, player = self.game, self.game.player
        py, px = player.location
        candidates = [
            (y, x) for (y, x) in game.map.visible
            if game.map.matrix[y][x].walkable
            and game.map.matrix[y][x].occupant is None
            and (y, x) != (py, px)
        ]
        if not candidates:
            return None
        cursor = list(player.location)
        game._show_examine(cursor)
        game.render()
        while True:
            key = keys.read_key()
            if key in (keys.ESC, "q"):
                game._clear_examine()
                return None
            if key in (keys.ENTER, "z"):
                target = tuple(cursor)
                game._clear_examine()
                if target in candidates:
                    return target
                return None
            d = keys.read_direction(key)
            if d:
                from .map import DIRS
                dy, dx = DIRS[d]
                ny, nx = cursor[0] + dy, cursor[1] + dx
                if game.map.in_bounds(ny, nx) and game._examine_reachable(ny, nx):
                    cursor = [ny, nx]
                    game._show_examine(cursor)
                    game.render()
                continue

    # --- acquirement: pick one of three offered items -----------------
    def choose_acquirement(self, offerings: list):
        """Let the player pick one of three offered items (or take gold)."""
        game = self.game
        clear_screen()
        game.print("[menu_header]Acquirement[/menu_header]\n", highlight=False)
        game.print("[flavor]Three items appear before you, drawn from the dungeon.[/flavor]\n",
                   highlight=False)
        table = Table(expand=False, border_style="grey37")
        table.add_column("#", style="controls", justify="right")
        table.add_column("Item", style="item")
        table.add_column("Detail", style="flavor")
        for i, (item, detail) in enumerate(offerings, 1):
            table.add_row(str(i), self._name(item), detail)
        table.add_row("g", "[coin]500 gold[/coin]", "[flavor]a pile of treasure[/flavor]")
        game.print(table)
        game.print(f"\n{style_text('number', 'controls')} take   "
                   f"{style_text('g', 'controls')} gold   "
                   f"{style_text('esc', 'controls')} cancel", highlight=False)
        while True:
            key = keys.read_key()
            if key in (keys.ESC, "q"):
                return ("cancel",)
            if key == "g":
                return ("gold", 500)
            if key.isdigit():
                n = int(key)
                if 1 <= n <= len(offerings):
                    return ("item", offerings[n - 1][0])
        # unreachable

    # --- ranged: choose which thrown item to use -----------------------
    def choose_throwable(self, throwables: list):
        """Let the player pick which throwable stack to fire when more than one exists."""
        game = self.game
        clear_screen()
        game.print("[menu_header]Throw what?[/menu_header]\n", highlight=False)
        table = Table(expand=False, border_style="grey37")
        table.add_column("#", style="controls", justify="right")
        table.add_column("Item", style="item")
        table.add_column("Details", style="flavor")
        for i, it in enumerate(throwables, 1):
            table.add_row(str(i), self._name(it), self._detail(it))
        game.print(table)
        game.print(f"\n{style_text('number', 'controls')} select   "
                   f"{style_text('esc', 'controls')} cancel", highlight=False)
        idx = self._read_index(len(throwables))
        return None if idx is None else throwables[idx]

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

    # --- LLM helpers ----------------------------------------------------
    def _npc_greeting(self, npc, role: str) -> str | None:
        """Generate an in-character greeting via LLM, showing a spinner while waiting."""
        game = self.game
        llm = getattr(game, "llm", None)
        if not llm or not llm.enabled:
            return None
        p = game.player
        background = getattr(p, "background", None) or "adventurer"
        personality = getattr(npc, "personality", "")
        if role == "healer":
            task_hint = "Acknowledge their wounds and offer to heal them."
        else:
            items = ", ".join(i.name for i in getattr(npc, "stuff", [])[:3])
            task_hint = f"The following are the items that you sell (e.g. {items or 'various wares'}). Not necessary to include to sound more natural."

        messages = [
            {"role": "system", "content": (
                f"You are {npc.name}, a {npc.occupation} in a dungeon. {personality} "
                f"Reply with ONLY the spoken dialogue — 1-2 sentences, no thinking"
                f"no stage directions, no quotation marks, no internal monologue."
            )},
            {"role": "user", "content": (
                f"Depth {game.depth}. A {background} named {p.name} "
                f"({p.health}/{p.max_health} HP, {p.coins} gold) approaches. "
                f"Greet them. {task_hint}"
            )},
        ]

        future = llm.complete_async(messages)

        # Show NPC header + animated spinner while the LLM generates
        clear_screen()
        game.print(
            f"{style_text(npc.name, 'name')} — {style_text(npc.occupation, 'occupation')}",
            highlight=False,
        )
        with Live(console=game.rich_console, refresh_per_second=10) as live:
            i = 0
            while not future.done():
                live.update(Text.from_markup(
                    f"[flavor]{_SPINNER[i % len(_SPINNER)]} ...[/flavor]"
                ))
                time.sleep(0.1)
                i += 1

        return future.result()

    # --- trader ---------------------------------------------------------
    def trader(self, trader) -> str | None:
        """Returns 'swap' if the player chose to step past the trader."""
        greeting = self._npc_greeting(trader, "trader")
        while True:
            stock = trader.stuff
            clear_screen()
            self.game.print(
                f"{style_text(trader.name, 'name')} — {style_text(trader.occupation, 'occupation')}"
                f"   (your gold: [coin]{self.game.player.coins}[/coin])", highlight=False)
            if greeting:
                self.game.print(f"[flavor]\"{greeting}\"[/flavor]\n", highlight=False)
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
        if isinstance(item, DungeonThrowable):
            stack = next((it for it in player.inventory
                          if isinstance(it, DungeonThrowable) and it.name == item.name), None)
            if stack:
                player.coins -= item.cost
                stack.count += item.count
                trader.stuff.pop(idx)
                game.message(f"You buy {item.count} more {style_text(item.name, 'item')} for "
                             f"[coin]{item.cost}[/coin] gold ([inventory]{stack.count}[/inventory] total).")
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
        greeting = self._npc_greeting(healer, "healer")
        while True:
            clear_screen()
            missing = player.max_health - player.health
            full_cost = missing * rate
            affordable_hp = min(missing, player.coins // rate) if rate else missing
            self.game.print(
                f"{style_text(healer.name, 'name')} — {style_text('Healer', 'occupation')}"
                f"   (your gold: [coin]{player.coins}[/coin])", highlight=False)
            if greeting:
                self.game.print(f"[flavor]\"{greeting}\"[/flavor]\n", highlight=False)
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

    # --- spells ----------------------------------------------------------
    def spell_ui(self) -> bool:
        """DCSS-style spell library screen. Returns True if a turn was spent."""
        game, player = self.game, self.game.player
        spells = player.known_spells
        if not spells:
            clear_screen()
            game.print("[menu_header]Spells[/menu_header]", highlight=False)
            game.print("\nYou have not memorised any spells.", highlight=False)
            game.print(f"\nPress {style_text('esc', 'controls')} to return.", highlight=False)
            keys.read_key()
            return False

        letters = "abcdefghijklmnopqrstuvwxyz"
        while True:
            clear_screen()
            used_slots = sum(s.level for s in spells)
            max_slots = self._max_spell_slots(player)
            game.print(
                f"[menu_header]Your Spells[/menu_header]    "
                f"[flavor]Slots Left: {max_slots - used_slots}/{max_slots}[/flavor]",
                highlight=False,
            )
            game.print("=" * 63, highlight=False)
            table = Table(expand=False, border_style="grey37")
            table.add_column("Key", style="controls", justify="right")
            table.add_column("Spell", style="item")
            table.add_column("Schools", style="flavor")
            table.add_column("Level", style="level", justify="right")
            table.add_column("Failure", style="warn", justify="right")
            for i, spell in enumerate(spells):
                if i >= len(letters):
                    break
                key = letters[i]
                schools = " / ".join(spell.schools)
                failure = calculate_failure(spell, player)
                fail_str = f"{failure:.0f}% Failure"
                boosted = ""
                staff = player.equipped
                if staff:
                    ss = staff_school(staff.name)
                    if ss and (ss in spell.schools or ss == "Spellcasting"):
                        boosted = " *Staff Boosted*"
                table.add_row(key, spell.name, schools, str(spell.level), fail_str + boosted)
            game.print(table)
            game.print(
                f"\n{style_text('letter', 'controls')} cast   "
                f"{style_text('l + letter', 'controls')} describe   "
                f"{style_text('esc', 'controls')} exit",
                highlight=False,
            )
            key = keys.read_key()
            if key in (keys.ESC, "q"):
                return False
            if key == "l":
                sub = keys.read_key()
                if sub in letters:
                    idx = letters.index(sub)
                    if idx < len(spells):
                        self._describe_spell(spells[idx])
                continue
            if key in letters:
                idx = letters.index(key)
                if idx < len(spells):
                    return self._cast_spell(spells[idx])

    def _max_spell_slots(self, player) -> int:
        spellcasting = player.skills.get_level("Spellcasting") if player.skills else 0.0
        return int(3 + spellcasting * 0.5 + player.level * 0.3)

    def _describe_spell(self, spell) -> None:
        """Show full details for a spell: description, damage, status, MP cost."""
        game, player = self.game, self.game.player
        clear_screen()
        game.print(f"[menu_header]{spell.name}[/menu_header]\n", highlight=False)
        if spell.description:
            game.print(f"[flavor]{spell.description}[/flavor]\n", highlight=False)
        failure = calculate_failure(spell, player)
        staff = player.equipped
        boosted = False
        if staff:
            ss = staff_school(staff.name)
            if ss and (ss in spell.schools or ss == "Spellcasting"):
                boosted = True
        table = Table(expand=False, border_style="grey37")
        table.add_column("Stat", style="controls")
        table.add_column("Value", style="item")
        table.add_row("Level", str(spell.level))
        table.add_row("Schools", " / ".join(spell.schools))
        table.add_row("MP Cost", str(spell.mp_cost))
        table.add_row("Range", str(spell.range) if spell.range else "self")
        if spell.damage:
            lo, hi = spell.damage
            table.add_row("Damage", f"{lo}-{hi} {spell.damage_type}")
        if spell.status:
            eff = spell.status.get("effect", "")
            dur = spell.status.get("duration", 0)
            pot = spell.status.get("potency", 1)
            table.add_row("Status", f"{eff} (dur {dur}, power {pot})")
        if spell.effect == "channel":
            total = max(1, int(spell.extra.get("channel_turns", 3)))
            table.add_row("Channel", f"{total} ticks (grows stronger each turn)")
        elif spell.effect == "self_teleport":
            table.add_row("Effect", "Teleport to random visible tile")
        elif spell.effect == "summon":
            st = spell.extra.get("summon_type", "?")
            dur = spell.extra.get("duration", 0)
            table.add_row("Summon", f"{st} for {dur} turns")
        elif spell.effect == "ignite_flora":
            table.add_row("Effect", "Ignites all visible plants")
        elif spell.effect == "expanding_aoe":
            r = spell.extra.get("radius", 0)
            table.add_row("AOE", f"expanding ring (radius {r})")
        elif spell.effect == "explosion":
            r = spell.extra.get("radius", 0)
            table.add_row("AOE", f"radius {r}")
        fail_str = f"{failure:.0f}%"
        if boosted:
            fail_str += " *Staff Boosted*"
        table.add_row("Failure", fail_str)
        game.print(table)
        game.print(f"\nPress {style_text('enter', 'controls')} to return.", highlight=False)
        keys.read_key()

    def _cast_spell(self, spell) -> bool:
        """Cast a spell. Returns True if a turn was spent (caller should spend_turn)."""
        game, player = self.game, self.game.player

        if spell.effect == "channel" and spell.name in player._channeling:
            from .magic import continue_channel
            return continue_channel(spell, player, game)

        # Silence aura / status blocks magic.
        if game.map.silence_aura > 0 or player.status.has("silence"):
            game.message(f"[fail]A heavy silence swallows the {spell.name}. The magic fizzles.[/fail]")
            return False

        if player.mp < spell.mp_cost:
            game.message(f"[warn]You do not have enough MP to cast {spell.name}.[/warn]")
            return False

        # Target selection if needed
        target = None
        if spell.effect in ("projectile", "explosion", "channel", "status_chain"):
            target = self._choose_spell_target(spell)
            if target is None:
                return False
        elif spell.effect == "touch":
            py, px = player.location
            # Check adjacent enemies
            adj = []
            for dy, dx in [(-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (-1, 1), (1, -1), (1, 1)]:
                ny, nx = py + dy, px + dx
                if game.map.in_bounds(ny, nx):
                    occ = game.map.matrix[ny][nx].occupant
                    if occ and getattr(occ, "is_enemy", False):
                        adj.append(occ)
            if adj:
                target = adj[0]
            else:
                game.message("[warn]No adjacent enemy to touch.[/warn]")
                return False

        if spell.effect == "channel":
            from .magic import start_channel
            player.mp -= spell.mp_cost
            if player.skills:
                for school in spell.schools:
                    player.skills.record(school)
                player.skills.record("Spellcasting")
            ok = start_channel(spell, player, game, target)
            if ok and spell.cast_text:
                game.message(f"[flavor]{spell.cast_text}[/flavor]")
            return ok

        from .magic import resolve_cast
        player.mp -= spell.mp_cost
        if player.skills:
            for school in spell.schools:
                player.skills.record(school)
            player.skills.record("Spellcasting")
        success = resolve_cast(spell, player, game, target)
        if success:
            if spell.cast_text:
                game.message(f"[flavor]{spell.cast_text}[/flavor]")
            else:
                game.message(f"[action]You cast {spell.name}.[/action]")
        return bool(success)

    def _choose_spell_target(self, spell):
        game = self.game
        player = game.player
        py, px = player.location
        rng = spell.range

        def reachable(e):
            return (max(abs(e.y - py), abs(e.x - px)) <= rng
                    and game.map._line_of_sight(py, px, e.y, e.x))

        targets = sorted((e for e in game.map.visible_enemies() if reachable(e)),
                         key=lambda e: max(abs(e.y - py), abs(e.x - px)))
        if not targets:
            game.message("There is no target in range.")
            return None
        idx = 0
        cursor = list(targets[idx].location)
        while True:
            game._show_target(cursor)
            game.render()
            key = keys.read_key()
            if key in (keys.ESC, "q"):
                game._clear_target()
                return None
            if key in (keys.ENTER, "z"):
                break
            if key == keys.TAB:
                idx = (idx + 1) % len(targets)
                cursor = list(targets[idx].location)
                continue
            d = keys.read_direction(key)
            if d:
                from .map import DIRS
                dy, dx = DIRS[d]
                ny, nx = cursor[0] + dy, cursor[1] + dx
                if game.map.in_bounds(ny, nx):
                    cursor = [ny, nx]
                    continue
        game._clear_target()
        enemy = game.map.matrix[cursor[0]][cursor[1]].occupant
        if enemy and getattr(enemy, "is_enemy", False):
            return enemy
        # For explosion, return cursor position
        if spell.effect == "explosion":
            return tuple(cursor)
        return None
