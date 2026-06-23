import copy
import datetime
import json
import os
import sys
import time
import operator
import traceback
import random
import types
from dataclasses import dataclass, field
from pathlib import Path

from tinydb import TinyDB, Query
from rich.panel import Panel

from . import input as keys
from .config import config
from .utils import style_text, clear_screen
from .classes.map import DungeonMap, DungeonPlayer, DIRS
from .classes.menus import DungeonMenu
from .classes.items import (
    DungeonShard, DungeonPotion, DungeonScroll, DungeonThrowable,
    DungeonArmour, DungeonSpellBook, DungeonWeapon, DungeonInventory,
    DungeonSpell,
)
from .classes.database import DungeonDatabase
from .classes.misc import DungeonTimeData
from .classes.status import StatusSet
from __version__ import __version__
from .classes.people import DungeonTrader, DungeonHealer
from .classes.skills import SkillSet, SkillState
from .classes.enemies import DungeonEnemy, EnemyTexts
from .classes.levelgen import generate_level, LevelLayout, Room, STRUCTURE_CATALOG
from .llm import LLMClient

SAVE_FILE_NAME = "savegame.json"
SAVE_FILE = Path(__file__).resolve().parent.parent.parent / SAVE_FILE_NAME
SAVE_VERSION = 2  # v2: brand/ego/enchant/fog/silence/holiness fields

print("Loading...")


def _read_save_state() -> dict | None:
    if not SAVE_FILE.exists():
        return None
    try:
        with open(SAVE_FILE, "r", encoding="utf-8") as handle:
            data = json.load(handle)
        if int(data.get("version", 0)) != SAVE_VERSION:
            return None
        return data
    except Exception:
        return None


T = config.terrain

TURN = 10  # energy one full-speed action costs / grants per game-tick

# compass direction -> (dy, dx), for cursor movement and pathfinding
DIR_DELTA = {
    "n": (-1, 0), "s": (1, 0), "w": (0, -1), "e": (0, 1),
    "ne": (-1, 1), "nw": (-1, -1), "se": (1, 1), "sw": (1, -1),
}

# Serialization helpers for save/load state.

def _coord_to_list(coord):
    return [coord[0], coord[1]] if coord is not None else None


def _list_to_coord(value):
    return tuple(value) if value is not None else None


def _room_to_dict(room: Room) -> dict:
    return {
        "x": room.x,
        "y": room.y,
        "w": room.w,
        "h": room.h,
        "shape": room.shape,
    }


def _room_from_dict(data: dict) -> Room:
    return Room(data["x"], data["y"], data["w"], data["h"], shape=data.get("shape", "rect"))


def _save_item(item) -> dict | None:
    if item is None:
        return None
    data = {"kind": type(item).__name__, "name": item.name}
    if isinstance(item, DungeonThrowable):
        data["count"] = item.count
    if isinstance(item, DungeonInventory):
        data["inventory"] = item.inventory
    if isinstance(item, DungeonArmour):
        data["slot"] = item.slot
    if isinstance(item, DungeonSpellBook):
        data["spells"] = item.spells
    # Weapon fields added with the brand/ego/enchant systems.
    if isinstance(item, DungeonWeapon):
        if getattr(item, "brand", None):
            data["brand"] = item.brand
        if getattr(item, "enchant", 0):
            data["enchant"] = item.enchant
        if getattr(item, "magical_staff", False):
            data["magical_staff"] = True
        if getattr(item, "dmg_pct_vs_holiness", None):
            data["dmg_pct_vs_holiness"] = dict(item.dmg_pct_vs_holiness)
    # Armour fields added with the ego/enchant system.
    if isinstance(item, DungeonArmour):
        if getattr(item, "ego", None):
            data["ego"] = item.ego
        if getattr(item, "enchant", 0):
            data["enchant"] = item.enchant
        if getattr(item, "resistances", None):
            data["resistances"] = dict(item.resistances)
        if getattr(item, "ev_bonus", 0):
            data["ev_bonus"] = item.ev_bonus
        if getattr(item, "sh_bonus", 0):
            data["sh_bonus"] = item.sh_bonus
        if getattr(item, "ranged_dmg_bonus", 0.0):
            data["ranged_dmg_bonus"] = item.ranged_dmg_bonus
        if getattr(item, "grant_see_invisible", False):
            data["grant_see_invisible"] = True
    return data


def _load_item(data: dict, game):
    if data is None:
        return None
    kind = data["kind"]
    name = data["name"]

    if kind == "DungeonShard":
        return DungeonShard(name)
    if kind == "DungeonThrowable":
        item = game.db.item_db.search_item(name=name, type=DungeonThrowable)
        item = copy.copy(item) if item else None
        if item:
            item.count = int(data.get("count", 1))
        return item
    if kind == "DungeonPotion":
        item = game.db.item_db.search_item(name=name, type=DungeonPotion)
        return copy.copy(item) if item else None
    if kind == "DungeonScroll":
        item = game.db.item_db.search_item(name=name, type=DungeonScroll)
        return copy.copy(item) if item else None
    if kind == "DungeonWeapon":
        item = game.db.item_db.search_item(name=name, type=DungeonWeapon)
        item = copy.copy(item) if item else None
        if item is not None:
            item.brand = data.get("brand")
            item.enchant = int(data.get("enchant", 0))
            if data.get("magical_staff"):
                item.magical_staff = True
            if data.get("dmg_pct_vs_holiness"):
                item.dmg_pct_vs_holiness = dict(data["dmg_pct_vs_holiness"])
        return item
    if kind == "DungeonArmour":
        item = game.db.item_db.search_item(name=name, type=DungeonArmour)
        item = copy.copy(item) if item else None
        if item is not None:
            item.ego = data.get("ego")
            item.enchant = int(data.get("enchant", 0))
            if data.get("resistances"):
                item.resistances = dict(data["resistances"])
            if data.get("ev_bonus"):
                item.ev_bonus = int(data["ev_bonus"])
            if data.get("sh_bonus"):
                item.sh_bonus = int(data["sh_bonus"])
            if data.get("ranged_dmg_bonus"):
                item.ranged_dmg_bonus = float(data["ranged_dmg_bonus"])
            if data.get("grant_see_invisible"):
                item.grant_see_invisible = True
        return item
    if kind == "DungeonInventory":
        item = game.db.item_db.search_item(name=name, type=DungeonInventory)
        return copy.copy(item) if item else None
    if kind == "DungeonSpellBook":
        item = game.db.item_db.search_item(name=name, type=DungeonSpellBook)
        return copy.copy(item) if item else None
    return None


def _save_status(status) -> dict:
    return {name: {"duration": eff["duration"], "potency": eff["potency"]}
            for name, eff in status.effects.items()}


def _load_status(data: dict):
    status = StatusSet()
    for name, eff in data.items():
        status.effects[name] = {"duration": int(eff["duration"]), "potency": int(eff["potency"])}
    return status


def _save_skills(skills) -> dict | None:
    if skills is None:
        return None
    return {
        "manual_mode": bool(skills.manual_mode),
        "recent_actions": list(skills.recent_actions),
        "cross_training": skills.cross_training,
        "skills": {
            name: {
                "level": skill.level,
                "aptitude": skill.aptitude,
                "state": skill.state.value,
                "target": skill.target,
            }
            for name, skill in skills.skills.items()
        },
    }


def _load_skills(data: dict) -> SkillSet | None:
    if data is None:
        return None
    skills = SkillSet(
        skill_names=list(data["skills"].keys()),
        aptitudes={name: int(info.get("aptitude", 0)) for name, info in data["skills"].items()},
        cross_training=data.get("cross_training", {}),
    )
    skills.manual_mode = bool(data.get("manual_mode", False))
    skills.recent_actions = list(data.get("recent_actions", []))
    for name, info in data["skills"].items():
        skill = skills.skills.get(name)
        if not skill:
            continue
        skill.level = float(info.get("level", 0.0))
        skill.aptitude = int(info.get("aptitude", 0))
        skill.state = SkillState(info.get("state", SkillState.DISABLED.value))
        skill.target = info.get("target")
    return skills


def _save_theme(theme) -> dict | None:
    if theme is None:
        return None
    return {
        "name": theme.name,
        "description": theme.description,
        "layout_bias": theme.layout_bias,
        "enemy_bias": list(theme.enemy_bias),
        "trap_type": theme.trap_type,
        "trap_density": theme.trap_density,
        "loot_bias": theme.loot_bias,
        "ambient": theme.ambient,
        "structures": list(theme.structures),
        "terrain_features": list(theme.terrain_features),
    }


def _load_theme(data: dict):
    if data is None:
        return None
    return FloorTheme(
        name=data.get("name", ""),
        description=data.get("description", ""),
        layout_bias=data.get("layout_bias", "any"),
        enemy_bias=list(data.get("enemy_bias", [])),
        trap_type=data.get("trap_type", "any"),
        trap_density=data.get("trap_density", "normal"),
        loot_bias=data.get("loot_bias", "balanced"),
        ambient=data.get("ambient", ""),
        structures=list(data.get("structures", [])),
        terrain_features=list(data.get("terrain_features", [])),
    )


def _save_player(player) -> dict:
    return {
        "name": player.name,
        "background": player.background,
        "health": player.health,
        "max_health": player.max_health,
        "xp": player.xp,
        "xp_next": player.xp_next,
        "coins": player.coins,
        "shards": list(player.shards),
        "inventory": [_save_item(item) for item in player.inventory],
        "max_inventory": player.max_inventory,
        "equipped": _save_item(player.equipped),
        "armour": {slot: _save_item(item) for slot, item in player.armour.items()},
        "location": _coord_to_list(player.location),
        "level": player.level,
        "status": _save_status(player.status),
        "energy": player.energy,
        "speed": player.speed,
        "mp": player.mp,
        "max_mp": player.max_mp,
        "intelligence": player.intelligence,
        "known_spells": [spell.name for spell in player.known_spells],
        "channeling": player._channeling,
        "skills": _save_skills(player.skills),
    }


def _load_player(data: dict, game) -> DungeonPlayer:
    equipped = _load_item(data.get("equipped"), game) or game.db.item_db.search_item(name="Fists")
    player = DungeonPlayer(
        health=int(data.get("health", 1)),
        max_health=int(data.get("max_health", 1)),
        max_inventory=int(data.get("max_inventory", config.player.max_inventory)),
        coins=int(data.get("coins", 0)),
        xp=int(data.get("xp", 0)),
        equipped=equipped,
        game=game,
    )
    player.name = data.get("name")
    player.background = data.get("background")
    player.xp_next = int(data.get("xp_next", config.progression.xp_for(player.level)))
    player.shards = set(data.get("shards", []))
    player.inventory = [_load_item(item_proto, game) for item_proto in data.get("inventory", []) if _load_item(item_proto, game) is not None]
    player.armour = {slot: _load_item(item_proto, game) for slot, item_proto in data.get("armour", {}).items()}
    player.location = tuple(data.get("location", (0, 0)))
    player.level = int(data.get("level", 1))
    player.status = _load_status(data.get("status", {}))
    player.energy = int(data.get("energy", TURN))
    player.speed = int(data.get("speed", 10))
    player.mp = float(data.get("mp", 0))
    player.max_mp = float(data.get("max_mp", 0))
    player.intelligence = int(data.get("intelligence", 8))
    player.known_spells = [game.db.item_db.search_spell(name) for name in data.get("known_spells", [])]
    player.known_spells = [s for s in player.known_spells if s is not None]
    player._channeling = {name: int(turns) for name, turns in data.get("channeling", {}).items()}
    player._channel_targets = {}
    player.skills = _load_skills(data.get("skills"))
    if player.skills:
        player.skills.recent_actions = list(data.get("skills", {}).get("recent_actions", []))
    player.equipped = None
    if equipped is not None:
        # Reuse the matching object from inventory if possible.
        for inv_item in player.inventory:
            if inv_item is not None and inv_item.name == equipped.name and type(inv_item) is type(equipped):
                player.equipped = inv_item
                break
        if player.equipped is None:
            player.equipped = equipped
    return player


def _save_cell(cell) -> dict:
    return {
        "terrain": cell.terrain,
        "explored": cell.explored,
        "trap": cell.trap,
        "trap_hidden": cell.trap_hidden,
        "feature": cell.feature,
        "gold": cell.gold,
        "items": [_save_item(item) for item in cell.items],
    }


def _load_cell(data: dict, cell):
    cell.explored = bool(data.get("explored", False))
    cell.trap = data.get("trap")
    cell.trap_hidden = bool(data.get("trap_hidden", True))
    cell.feature = data.get("feature")
    cell.gold = int(data.get("gold", 0))
    cell.items = [_load_item(item_proto, cell.game) for item_proto in data.get("items", []) if _load_item(item_proto, cell.game) is not None]


def _save_entity(entity) -> dict:
    if isinstance(entity, DungeonTrader):
        return {
            "kind": "trader",
            "name": entity.name,
            "occupation": entity.occupation,
            "personality": entity.personality,
            "symbol": entity.symbol,
            "style": entity.style,
            "location": _coord_to_list(entity.location),
            "stuff": [_save_item(item) for item in entity.stuff],
        }
    if isinstance(entity, DungeonHealer):
        return {
            "kind": "healer",
            "name": entity.name,
            "occupation": entity.occupation,
            "personality": entity.personality,
            "symbol": entity.symbol,
            "style": entity.style,
            "location": _coord_to_list(entity.location),
            "heal_cost_per_hp": entity.heal_cost_per_hp,
        }
    kind = "summon" if getattr(entity, "is_summon", False) else "enemy"
    data = {
        "kind": kind,
        "name": entity.name,
        "tier": entity.tier,
        "health": entity.health,
        "max_health": entity.max_health,
        "coin_drop": getattr(entity, "coin_drop", 0),
        "xp_drop": getattr(entity, "xp_drop", 0),
        "attack_base": entity.attack_base,
        "attack_range": list(entity.attack_range),
        "accuracy": entity.accuracy,
        "ranged": bool(getattr(entity, "ranged", False)),
        "attack_distance": int(getattr(entity, "attack_distance", 1)),
        "speed": int(getattr(entity, "speed", 10)),
        "awake": bool(getattr(entity, "awake", False)),
        "energy": int(getattr(entity, "energy", 0)),
        "status": _save_status(entity.status),
        "location": _coord_to_list(entity.location),
        "despawn_timer": int(getattr(entity, "despawn_timer", 0)),
    }
    # Holiness (added with the Sacred Scourge / holy_wrath system).
    holiness = getattr(entity, "holiness", "natural")
    if holiness != "natural":
        data["holiness"] = holiness
    # Special summon flags used by Spectral / Butterfly brands.
    if getattr(entity, "is_spectral", False):
        data["is_spectral"] = True
    if getattr(entity, "is_butterfly", False):
        data["is_butterfly"] = True
    return data


def _load_entity(data: dict, game):
    kind = data.get("kind")
    if kind == "trader":
        trader = DungeonTrader(
            potential_sales=[],
            occupation=data.get("occupation", "trader"),
            personality=data.get("personality", ""),
        )
        trader.name = data.get("name", trader.name)
        trader.symbol = data.get("symbol", trader.symbol)
        trader.style = data.get("style", trader.style)
        trader.location = _list_to_coord(data.get("location")) or (0, 0)
        trader.stuff = [_load_item(item_proto, game) for item_proto in data.get("stuff", []) if _load_item(item_proto, game) is not None]
        return trader
    if kind == "healer":
        healer = DungeonHealer(
            heal_cost_per_hp=int(data.get("heal_cost_per_hp", 1)),
            occupation=data.get("occupation", "Healer"),
            personality=data.get("personality", ""),
        )
        healer.name = data.get("name", healer.name)
        healer.symbol = data.get("symbol", healer.symbol)
        healer.style = data.get("style", healer.style)
        healer.location = _list_to_coord(data.get("location")) or (0, 0)
        return healer
    name = data.get("name")
    loader = game.db.enemy_db.search_enemy(name=name)
    if loader:
        entity = loader.load()
    else:
        texts = EnemyTexts("The {} attacks!", "The {} hits!", "The {} misses!", "The {} dies.", name)
        entity = DungeonEnemy(
            name=name,
            symbol="?",
            tier=data.get("tier", "mid"),
            health=int(data.get("max_health", 1)),
            coin_drop=int(data.get("coin_drop", 0)),
            xp_drop=int(data.get("xp_drop", 0)),
            attack_base=int(data.get("attack_base", 1)),
            attack_range=list(data.get("attack_range", [0, 1])),
            accuracy=int(data.get("accuracy", 50)),
            texts=texts,
            game=game,
            ranged=bool(data.get("ranged", False)),
            attack_distance=int(data.get("attack_distance", 1)),
            speed=int(data.get("speed", 10)),
        )
    entity.health = int(data.get("health", entity.health))
    entity.max_health = int(data.get("max_health", entity.max_health))
    entity.coin_drop = int(data.get("coin_drop", getattr(entity, "coin_drop", 0)))
    entity.xp_drop = int(data.get("xp_drop", getattr(entity, "xp_drop", 0)))
    entity.attack_base = int(data.get("attack_base", getattr(entity, "attack_base", 0)))
    entity.attack_range = list(data.get("attack_range", getattr(entity, "attack_range", [0, 1])))
    entity.accuracy = int(data.get("accuracy", getattr(entity, "accuracy", 50)))
    entity.ranged = bool(data.get("ranged", getattr(entity, "ranged", False)))
    entity.attack_distance = int(data.get("attack_distance", getattr(entity, "attack_distance", 1)))
    entity.speed = int(data.get("speed", getattr(entity, "speed", 10)))
    entity.awake = bool(data.get("awake", False))
    entity.energy = int(data.get("energy", 0))
    entity.status = _load_status(data.get("status", {}))
    entity.location = _list_to_coord(data.get("location")) or (0, 0)
    if kind == "summon":
        entity.is_enemy = False
        entity.is_summon = True
        entity.despawn_timer = int(data.get("despawn_timer", 0))
    if data.get("is_spectral"):
        entity.is_spectral = True
    if data.get("is_butterfly"):
        entity.is_butterfly = True
    # Restore holiness (added with Sacred Scourge / holy_wrath system).
    if data.get("holiness"):
        entity.holiness = data["holiness"]
    return entity


def _save_level(level: DungeonMap) -> dict:
    return {
        "width": level.width,
        "height": level.height,
        "rooms": [_room_to_dict(room) for room in level.rooms],
        "stairs_up": _coord_to_list(level.stairs_up),
        "stairs_down": _coord_to_list(level.stairs_down),
        "vault_cells": [_coord_to_list(c) for c in level.vault_cells],
        "temple_cells": [_coord_to_list(c) for c in level.temple_cells],
        "altar": _coord_to_list(level.altar),
        "floor_cells": [_coord_to_list(c) for c in level.floor_cells],
        "scenery_features": [[y, x, feat] for (y, x, feat) in getattr(level, "scenery_features", [])],
        "excluded_stairs": [_coord_to_list(c) for c in level.excluded_stairs],
        "terrain": [[cell.terrain for cell in row] for row in level.matrix],
        "cells": [[_save_cell(cell) for cell in row] for row in level.matrix],
        "enemies": [_save_entity(e) for e in level.enemies],
        "summon": [_save_entity(s) for s in level.summon],
        "npcs": [_save_entity(n) for n in level.npcs],
        # Floor effects added with the scroll system.
        "silence_aura": int(getattr(level, "silence_aura", 0)),
        "fog_cells": [[c[0], c[1], int(t)] for c, t in getattr(level, "fog_cells", {}).items()],
    }


def _load_level(data: dict, game) -> DungeonMap:
    layout = LevelLayout(int(data.get("width", 1)), int(data.get("height", 1)))
    layout.rooms = [_room_from_dict(room) for room in data.get("rooms", [])]
    layout.stairs_up = _list_to_coord(data.get("stairs_up"))
    layout.stairs_down = _list_to_coord(data.get("stairs_down"))
    layout.vault_cells = [_list_to_coord(c) for c in data.get("vault_cells", []) if c is not None]
    layout.temple_cells = [_list_to_coord(c) for c in data.get("temple_cells", []) if c is not None]
    layout.altar = _list_to_coord(data.get("altar"))
    layout.floor_cells = [_list_to_coord(c) for c in data.get("floor_cells", []) if c is not None]
    layout.scenery_features = [tuple(feat) for feat in data.get("scenery_features", [])]
    layout.terrain = [list(row) for row in data.get("terrain", [])]
    level = DungeonMap(game=game, layout=layout)
    level.excluded_stairs = {tuple(c) for c in data.get("excluded_stairs", []) if c is not None}
    for y, row in enumerate(data.get("cells", [])):
        for x, cell_data in enumerate(row):
            _load_cell(cell_data, level.matrix[y][x])
    level.enemies = []
    level.summon = []
    level.npcs = []
    for entity_data in data.get("enemies", []):
        enemy = _load_entity(entity_data, game)
        level.enemies.append(enemy)
        level.place_occupant(enemy, *enemy.location)
    for entity_data in data.get("summon", []):
        summon = _load_entity(entity_data, game)
        level.summon.append(summon)
        level.place_occupant(summon, *summon.location)
    for entity_data in data.get("npcs", []):
        npc = _load_entity(entity_data, game)
        level.npcs.append(npc)
        level.place_occupant(npc, *npc.location)
    # Floor effects added with the scroll system.
    level.silence_aura = int(data.get("silence_aura", 0))
    level.fog_cells = {
        (int(c[0]), int(c[1])): int(c[2])
        for c in data.get("fog_cells", []) if len(c) >= 3
    }
    return level


# Weapons seeded into vault treasure, by how deep you are.
_VAULT_WEAPONS = [
    "Short Sword", "Scimitar", "Mace", "Falchion",
    "Demon trident", "Battleaxe", "Eudemon blade", "War Axe",
    "Triple sword", "Bardiche", "Giant spiked club", "Triple crossbow",
]

# Shard floors: depth -> (shard name, guardian name)
_SHARD_FLOORS = {
    6: ("Shard of Flame", "Flame Guardian"),
    7: ("Shard of Stone", "Stone Guardian"),
    8: ("Shard of Shadow", "Shadow Guardian"),
}

# Floor themes: LLM-generated per-floor biome data
@dataclass
class FloorTheme:
    name: str = ""
    description: str = ""
    layout_bias: str = "any"      # cave | rooms | bsp | any
    enemy_bias: list = field(default_factory=list)
    trap_type: str = "any"        # dart | poison | teleport | alarm | any
    trap_density: str = "normal"  # low | normal | high
    loot_bias: str = "balanced"   # potions | scrolls | weapons | gold | balanced
    ambient: str = ""
    structures: list = field(default_factory=list)        # 0-2 names from STRUCTURE_CATALOG
    terrain_features: list = field(default_factory=list)  # 0-2 from _VALID_TERRAIN_FEATURES
    water_density: str = "small"  # small | medium | large — size of ambient ponds

_THEME_SPINNER = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
_VALID_BIAS_ENEMIES = [
    "Giant Rat", "Bat", "Kobold", "Goblin", "Orc", "Skeleton", "Zombie",
    "Giant Spider", "Kobold Slinger", "Ogre", "Wraith", "Troll",
]
_VALID_STRUCTURES = {
    "shrine", "mushroom_grove", "overgrown_room", "ruined_hall",
    "frozen_pond", "campsite", "poison_marsh", "standing_stones",
}
_VALID_TERRAIN_FEATURES = {"lava_pools", "chasms", "water_pools"}

# Pre-defined biomes used when the LLM is disabled. Each tuple:
#   (name, description, water_density, structures, terrain_features)
# Empty list for structures/terrain_features = none placed.
_FALLBACK_BIOMES: list[tuple[str, str, str, list, list]] = [
    ("Flooded Catacombs", "Ancient graves half-drowned in stagnant water.", "large", ["ruined_hall"], ["water_pools"]),
    ("Drowned Crypt", "Black water fills these burial halls to the brim.", "large", ["ruined_hall"], ["water_pools"]),
    ("Sunken Temple", "Flooded ruins of a long-forgotten shrine.", "large", ["shrine", "ruined_hall"], ["water_pools"]),
    ("Sodden Sewers", "Moss-lined tunnels where water pools knee-deep.", "medium", [], ["water_pools"]),
    ("Mossy Caverns", "Verdant grottoes dotted with shallow pools.", "medium", ["overgrown_room"], []),
    ("Mushroom Grotto", "Strange fungi glow in the damp earthen corners.", "medium", ["mushroom_grove"], []),
    ("Twisting Tunnels", "Cramped passages worn smooth by time.", "small", [], []),
    ("Forgotten Vault", "Locked chambers stuffed with dust and cobwebs.", "small", [], []),
    ("Burning Halls", "Charred chambers reeking of old fire.", "small", ["ruined_hall"], ["lava_pools"]),
    ("Whispering Galleries", "Long echoing corridors lined with worn frescoes.", "small", ["standing_stones"], []),
]

# Brands the Scroll of Brand Weapon can apply. Mirrors the BRAND_TABLE keys
# in classes/map.py so the two stay in sync.
BRAND_CHOICES = [
    "flaming", "freezing", "venom", "electrocution", "pain", "holy_wrath", "draining",
    "antimagic", "chaos", "distortion", "heavy", "protection", "spectral", "speed",
    "vampiric",
]

# Randomised appearances for unidentified consumables (shuffled per game).
_POTION_ADJ = [
    "fizzy", "murky", "glowing", "viscous", "azure", "crimson", "smoky", "bubbling",
    "cloudy", "oily", "sparkling", "luminous", "syrupy", "effervescent",
]
_SCROLL_LABELS = [
    "XYZZY", "FOOBIE", "KLATAA", "ZELGO", "NR9", "PRZ", "VELOX", "GNARL",
    "HRUM", "TZADIK", "OByeDA", "WAffLE", "ZIMBO", "QUOATH", "XUANGS",
    "BRYNDL", "PHLEGM", "KSIJ", "VARDE", "ULNOR", "MORPHI", "TENEBR",
]


class Dungeon:
    """Main game controller: owns the floors, player, database, and game loop."""

    def __init__(self, logger, rich_console, load_state: dict | None = None) -> None:
        self.log = logger
        self.rich_console = rich_console
        self.print = self.rich_console.print
        self.over = False

        clear_screen()
        self.menu = DungeonMenu(game=self)
        self.moves = 0
        self.depth = 1
        self.levels: dict[int, DungeonMap] = {}
        self.target_cursor = None   # ranged-targeting overlay state
        self.target_path = None
        self.examine_cursor = None   # examine-mode overlay state (y, x)
        self.camera_override = None  # pans viewport to a staircase when set (y, x)
        self.stair_cursor = None     # highlights a staircase tile in the render
        self.auto_pickup_types: set[str] = {"potion", "scroll", "gold"}
        # Developer god mode: enable from the start with DUNGEON_GODMODE=1, or toggle in-game with `~`.
        self.godmode = os.environ.get("DUNGEON_GODMODE") == "1"

        self.llm = LLMClient()
        self.log.info(f"LLM status: {self.llm.status}")
        if load_state is None:
            self._ai_toggle_prompt()

        # DM hint state
        self._hint_future = None
        self._last_hint_turn: int = -30
        self._hinted_states: set[str] = set()

        # Item lore state (name -> Future); _lore_done tracks items already attempted
        self._lore_futures: dict = {}
        self._lore_done: set[str] = set()

        # Floor theme state
        self._floor_themes: dict[int, FloorTheme] = {}
        self._theme_history: list[str] = []

        from .classes.ui import DungeonUI
        self.ui = DungeonUI(game=self)

        self.db = DungeonDatabase(game=self)
        self._init_identification()
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
        self.player.mp = 0
        self.player.max_mp = 0
        self.player.intelligence = 8

        if load_state is None:
            self._choose_background()

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
            self.message(f"[flavor]You descend into the dungeon. Three shards of a Broken Sigil lie scattered in the depths — find them all.[/flavor]")
            if self.llm.enabled:
                self.message(f"[flavor]The dungeon breathes with strange intelligence. ({self.llm.status})[/flavor]")
            elif self.llm.status != "disabled":
                self.message(f"[warn]LLM unavailable: {self.llm.status}[/warn]")
            self.log.info("dungeon initialised")
        else:
            self._load_state(load_state)

    # --- pre-game setup ------------------------------------------------
    def _ai_toggle_prompt(self) -> None:
        """Show AI toggle prompt before character creation."""
        clear_screen()
        self.print("[menu_header]AI Features[/menu_header]\n", highlight=False)
        if self.llm.enabled:
            self.print(
                f"[flavor]An AI companion is available ({self.llm.status}).[/flavor]\n\n"
                f"AI provides: dynamic floor themes, NPC dialogue, item lore, and hints.\n",
                highlight=False,
            )
            self.print(
                f"{style_text('1', 'controls')} Enable AI  {style_text('2', 'controls')} Disable AI\n",
                highlight=False,
            )
            while True:
                key = keys.read_key()
                if key == "1":
                    self.llm.enabled = True
                    self.log.info("AI enabled by player")
                    break
                elif key == "2":
                    self.llm.enabled = False
                    self.log.info("AI disabled by player")
                    break
        else:
            self.print(
                f"[warn]AI features unavailable ({self.llm.status}).[/warn]\n\n"
                f"To enable AI, configure a local LLM (LM Studio) or set an API key in .env.\n",
                highlight=False,
            )
            self.print(
                f"Press {style_text('enter', 'controls')} to continue with AI disabled.",
                highlight=False,
            )
            keys.read_key()
            self.llm.enabled = False

    # --- character creation --------------------------------------------
    def _serialize_state(self) -> dict:
        return {
            "version": SAVE_VERSION,
            "depth": self.depth,
            "moves": self.moves,
            "time_elapsed": getattr(self.time, "elapsed", 0.0),
            "auto_pickup_types": list(self.auto_pickup_types),
            "godmode": self.godmode,
            "llm_enabled": self.llm.enabled,
            "floor_themes": {str(depth): _save_theme(theme) for depth, theme in self._floor_themes.items() if theme is not None},
            "theme_history": list(self._theme_history),
            "ident": self.ident,
            "lore_done": list(self._lore_done),
            "player": _save_player(self.player),
            "levels": {str(depth): _save_level(level) for depth, level in self.levels.items()},
        }

    def save_game(self) -> None:
        clear_screen()
        shard_count = len(self.player.shards)
        self.print(Panel(
            f"[menu_header]Save Game[/menu_header]\n\n"
            f"Depth: [move_count]{self.depth}[/move_count]   "
            f"HP: {self.player.health}/{self.player.max_health}   "
            f"Shards: {shard_count}/3\n"
            f"XP: {self.player.xp}   "
            f"Gold: {self.player.coins}   "
            f"Turns: {self.moves}\n\n"
            f"Save to [warn]{SAVE_FILE_NAME}[/warn]?\n\n"
            f"{style_text('y', 'controls')} save    "
            f"{style_text('n', 'controls')} / {style_text('esc', 'controls')} cancel",
            border_style="grey37"))
        confirm = keys.read_key()
        if confirm != "y":
            self.render()
            return
        try:
            SAVE_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(SAVE_FILE, "w", encoding="utf-8") as handle:
                json.dump(self._serialize_state(), handle, indent=2)
            self.log.info(f"saved game to {SAVE_FILE}")
            self.message(f"[success]Game saved to {SAVE_FILE_NAME}.[/success]")
        except Exception as exc:
            self.log.info(f"failed to save game: {exc}")
            self.message("[warn]Unable to save the game.[/warn]")
        self.render()

    def _load_state(self, data: dict) -> None:
        self.depth = int(data.get("depth", 1))
        self.moves = int(data.get("moves", 0))
        self.auto_pickup_types = set(data.get("auto_pickup_types", list(self.auto_pickup_types)))
        self.godmode = bool(data.get("godmode", self.godmode))
        self.llm.enabled = bool(data.get("llm_enabled", self.llm.enabled))
        self._theme_history = list(data.get("theme_history", []))
        self._floor_themes = {
            int(depth): _load_theme(theme_data)
            for depth, theme_data in (data.get("floor_themes", {}) or {}).items()
            if theme_data is not None
        }
        self.ident = {
            name: {
                "appearance": rec.get("appearance"),
                "identified": bool(rec.get("identified")),
                "lore": rec.get("lore"),
            }
            for name, rec in (data.get("ident", {}) or {}).items()
        }
        self._lore_done = set(data.get("lore_done", []))
        self._lore_futures = {}
        self.time = DungeonTimeData(game=self)
        self.time.elapsed = float(data.get("time_elapsed", 0.0))

        levels = {}
        for depth, level_data in (data.get("levels", {}) or {}).items():
            level = _load_level(level_data, self)
            levels[int(depth)] = level
        self.levels = levels
        self.map = self.levels.get(self.depth) or next(iter(self.levels.values()), None)

        self.player = _load_player(data.get("player", {}), self)
        if self.map is not None:
            self.map.update_fov()

    def _choose_background(self) -> None:
        from rich.table import Table
        from rich.text import Text
        backgrounds = self.db.backgrounds
        page = 0
        per_page = 9
        total_pages = (len(backgrounds) + per_page - 1) // per_page
        while True:
            clear_screen()
            start = page * per_page
            chunk = backgrounds[start:start + per_page]
            title = f"Choose your Class  [flavor]Page {page + 1}/{total_pages}[/flavor]"
            table = Table(title=title, title_style="menu_header", border_style="grey37")
            table.add_column("#", style="controls", justify="right")
            table.add_column("Class", style="name")
            table.add_column("HP", style="health", justify="right")
            table.add_column("Description", style="flavor", overflow="fold", ratio=3)
            for i, bg in enumerate(chunk, 1):
                hp = bg['hp_bonus']
                table.add_row(str(i), bg["name"], f"+{hp}" if hp >= 0 else str(hp), bg["description"])
            self.print(table)
            nav = f"{style_text('1', 'controls')}-{style_text(str(min(9, len(chunk))), 'controls')} select  "
            if total_pages > 1:
                nav += f"{style_text('<', 'controls')} prev  {style_text('>', 'controls')} next  "
            nav += f"{style_text('i', 'controls')}+number inspect  {style_text('esc', 'controls')} exit"
            self.print(f"\n{nav}", highlight=False)
            key = keys.read_key()
            if key == keys.ESC:
                self.print("\n[flavor]Exit to title?[/flavor]  y/any key ", highlight=False)
                if keys.read_key().lower() == "y":
                    return
                continue
            if key == "<" or key == "[":
                if page > 0:
                    page -= 1
                continue
            if key == ">" or key == "]":
                if page + 1 < total_pages:
                    page += 1
                continue
            if key.isdigit():
                n = int(key)
                if 1 <= n <= len(chunk):
                    idx = start + n - 1
                    self._apply_background(backgrounds[idx])
                    return
            if key.lower() == "i":
                self.print("\nPress number to inspect:", highlight=False)
                k2 = keys.read_key()
                if k2.isdigit():
                    n = int(k2)
                    idx = start + n - 1
                    if 0 <= idx < len(backgrounds) and n <= len(chunk):
                        self._inspect_background(backgrounds[idx])

    def _inspect_background(self, bg: dict) -> None:
        """Show detailed information about a class."""
        from rich.table import Table
        clear_screen()
        self.print(f"[menu_header]{bg['name']}[/menu_header]\n", highlight=False)
        self.print(f"[flavor]{bg['description']}[/flavor]\n", highlight=False)

        table = Table(expand=False, border_style="grey37")
        table.add_column("Stat", style="controls")
        table.add_column("Value", style="item")
        hp = bg['hp_bonus']
        table.add_row("HP Bonus", f"+{hp}" if hp >= 0 else str(hp))
        table.add_row("Intelligence", str(bg.get("intelligence", 8)))
        table.add_row("Max MP", str(bg.get("max_mp", 0)))
        table.add_row("Weapon", bg.get("start_weapon", "Fists"))
        table.add_row("Armour", bg.get("start_armour", "None"))
        items = bg.get("start_items", [])
        table.add_row("Items", ", ".join(items) if items else "None")
        spells = bg.get("start_spells", [])
        table.add_row("Spells", ", ".join(spells) if spells else "None")
        self.print(table)

        # Show skill aptitudes
        aptitudes = bg.get("aptitudes", {})
        if aptitudes:
            self.print("\n[menu_header]Skill Aptitudes[/menu_header]", highlight=False)
            apt_table = Table(expand=False, border_style="grey37")
            apt_table.add_column("Skill", style="item")
            apt_table.add_column("Aptitude", style="level", justify="right")
            for skill, value in sorted(aptitudes.items()):
                color = "success" if value > 0 else "warn" if value < 0 else "flavor"
                apt_table.add_row(skill, f"[{color}]{value:+d}[/{color}]")
            self.print(apt_table)

        self.print(
            f"\nPress {style_text('enter', 'controls')} to return to class selection.",
            highlight=False,
        )
        keys.read_key()

    def _apply_background(self, bg: dict) -> None:
        p = self.player
        p.background = bg["name"]
        p.max_health += bg.get("hp_bonus", 0)
        p.health = p.max_health
        # Magic stats
        p.intelligence = bg.get("intelligence", 8)
        p.max_mp = bg.get("max_mp", 5)
        p.mp = p.max_mp
        from .classes.skills import SkillSet
        skills_data = self.db.skills_data
        aptitudes = bg.get("aptitudes", {})
        cross = skills_data.get("cross_training", {})
        p.skills = SkillSet(
            skill_names=skills_data.get("skills", []),
            aptitudes=aptitudes,
            cross_training=cross,
        )
        p.skills.manual_mode = False
        weapon = self.db.item_db.search_item(name=bg["start_weapon"])
        if weapon:
            p.inventory.append(weapon)
            p.equipped = weapon
            self.identify(weapon, announce=False)
        armour_name = bg.get("start_armour")
        if armour_name:
            armour = self.db.item_db.search_item(name=armour_name, type=DungeonArmour)
            if armour:
                p.inventory.append(armour)
                p.armour[armour.slot] = armour
                self.identify(armour, announce=False)
        for name in bg.get("start_items", []):
            item = self.db.item_db.search_item(name=name)
            if item:
                p.inventory.append(item)
                self.identify(item, announce=False)  # starting kit is known
        # Memorise starting spells
        for spell_name in bg.get("start_spells", []):
            spell = self.db.item_db.search_spell(spell_name)
            if spell:
                p.known_spells.append(spell)
        # Starting skill levels for magic backgrounds
        if p.skills:
            for skill_name, level in bg.get("start_skills", {}).items():
                if skill_name in p.skills.skills:
                    p.skills.skills[skill_name].level = level
        # Enable starting-relevant skills by default
        if p.skills:
            from .classes.skills import SkillState, skill_for_weapon
            # Weapon skill
            wskill = skill_for_weapon(p.equipped.name) if p.equipped else None
            if wskill and wskill in p.skills.skills:
                p.skills.skills[wskill].state = SkillState.ENABLED
            # Armour / Shields based on gear
            if p.armour.get("body"):
                p.skills.skills["Armour"].state = SkillState.ENABLED
            if p.armour.get("shield"):
                p.skills.skills["Shields"].state = SkillState.ENABLED
            # Base skills for everyone
            for base in ("Fighting", "Dodging", "Stealth"):
                if base in p.skills.skills:
                    p.skills.skills[base].state = SkillState.ENABLED
            # Magic skills for classes with positive aptitudes
            for skill_name, apt in aptitudes.items():
                if apt >= 0 and skill_name in p.skills.skills:
                    p.skills.skills[skill_name].state = SkillState.ENABLED

    # --- messaging ------------------------------------------------------
    def message(self, text: str, drop: int | None = None) -> None:
        self.ui.message(text, drop=drop)

    def render(self) -> None:
        self._check_state_triggers()
        self._flush_hint()
        self._flush_lore()
        self.ui.render()

    # --- LLM: DM hints -------------------------------------------------
    def _check_state_triggers(self) -> None:
        p = self.player
        if p.max_health and p.health / p.max_health < 0.3:
            self._queue_hint(f"low_hp_d{self.depth}", {
                "trigger": "player is critically wounded",
                "depth": self.depth, "background": p.background,
                "hp": p.health, "max_hp": p.max_health,
            })
        # Ambient flavour: fires at most once per 30-turn bucket (cooldown still applies)
        bucket = self.moves // 30
        if bucket > 0:
            self._queue_hint(f"ambient_{bucket}", {
                "trigger": "a quiet moment in the dungeon between encounters",
                "depth": self.depth, "background": p.background,
                "hp": p.health, "max_hp": p.max_health,
            })

    def _queue_hint(self, trigger_id: str, ctx: dict) -> None:
        if not self.llm.enabled:
            return
        if trigger_id in self._hinted_states:
            return
        if self.moves - self._last_hint_turn < 8:
            return
        self._hinted_states.add(trigger_id)
        self._hint_future = self.llm.complete_async(self._build_hint_prompt(ctx))

    def _build_hint_prompt(self, ctx: dict) -> list[dict]:
        return [
            {"role": "system", "content": (
                "You are the narrator of a dark fantasy roguelike. "
                "Output ONLY one short atmospheric sentence — no thinking, no explanation, "
                "no quotation marks. Maximum 15 words. Pure flavor, no gameplay advice."
            )},
            {"role": "user", "content": (
                f"Event: {ctx.get('trigger', 'something notable happened')}. "
                f"Depth {ctx.get('depth', '?')}, "
                f"{ctx.get('background', 'adventurer')}, "
                f"HP {ctx.get('hp', '?')}/{ctx.get('max_hp', '?')}."
            )},
        ]

    def _flush_hint(self) -> None:
        if self._hint_future and self._hint_future.done():
            text = self._hint_future.result()
            if text:
                self.message(f"[flavor]{text}[/flavor]")
                self._last_hint_turn = self.moves
            self._hint_future = None

    # --- LLM: item lore ------------------------------------------------
    def _build_lore_prompt(self, item) -> list[dict]:
        kind = type(item).__name__.replace("Dungeon", "").lower()
        return [
            {"role": "system", "content": (
                "You write item lore for a dark fantasy game. "
                "Output ONLY one sentence of grim backstory — no thinking, no explanation, "
                "no quotation marks. Specific and evocative."
            )},
            {"role": "user", "content": (
                f"{item.name} ({kind}): {item.description}"
            )},
        ]

    def _flush_lore(self) -> None:
        done = [name for name, f in self._lore_futures.items() if f.done()]
        for name in done:
            text = self._lore_futures.pop(name).result()
            self._lore_done.add(name)
            if not text:
                continue
            if name in self.ident:
                self.ident[name]["lore"] = text
            self.message(f"[flavor]{text}[/flavor]")

    def _maybe_queue_lore(self, item) -> None:
        """Queue lore generation for any identified item that hasn't had lore generated yet."""
        if not self.llm.enabled:
            return
        name = getattr(item, "name", None)
        if not name or name in self._lore_futures or name in self._lore_done:
            return
        rec = self.ident.get(name)
        if rec and not rec["identified"]:
            return  # unidentified consumable — identify() will handle it when used
        self._lore_futures[name] = self.llm.complete_async(self._build_lore_prompt(item))

    # --- item identification -------------------------------------------
    def _init_identification(self) -> None:
        """Assign each potion/scroll type a random appearance for this game."""
        self.ident: dict[str, dict] = {}
        potions = list(self.db.item_db.potions)
        for pot, adj in zip(potions, random.sample(_POTION_ADJ, len(potions))):
            self.ident[pot.name] = {"appearance": f"{adj} potion", "identified": False}
        scrolls = list(self.db.item_db.scrolls)
        for sc, label in zip(scrolls, random.sample(_SCROLL_LABELS, len(scrolls))):
            self.ident[sc.name] = {"appearance": f"scroll labelled '{label}'", "identified": False}

    def display_name(self, item) -> str:
        rec = self.ident.get(getattr(item, "name", None))
        if rec and not rec["identified"]:
            return rec["appearance"]
        name = getattr(item, "name", "?")
        # Show enchantment as a "+N" suffix so the player can see the rolled
        # upgrade at a glance (e.g. "Long Sword +3", "Plate Armour +5").
        ench = getattr(item, "enchant", 0)
        if ench > 0:
            name = f"{name} +{ench}"
        return name

    def identify(self, item, announce: bool = True) -> None:
        """Mark an item's whole type identified (optionally announcing its true name)."""
        rec = self.ident.get(getattr(item, "name", None))
        if rec and not rec["identified"]:
            rec["identified"] = True
            if announce:
                self.message(f"[success]You identify it as {style_text(item.name, 'item')}![/success]")
                if self.llm.enabled and item.name not in self._lore_futures:
                    self._lore_futures[item.name] = self.llm.complete_async(
                        self._build_lore_prompt(item)
                    )

    # --- level generation & travel -------------------------------------
    def _fallback_theme(self, depth: int) -> "FloorTheme":
        """Biome for current depth when LLM is disabled.

        Picks from a hand-tuned pool. Bias toward wet biomes on deeper
        floors (depth >= 5 has a 40 % chance of forcing a wet biome).
        """
        pool = list(_FALLBACK_BIOMES)
        if depth >= 5 and random.random() < 0.4:
            wet = [b for b in pool if b[2] in ("medium", "large")]
            if wet:
                pool = wet
        name, desc, water, structures, terrain_features = random.choice(pool)
        return FloorTheme(
            name=name, description=desc, water_density=water,
            structures=structures, terrain_features=terrain_features,
        )

    def _new_level(self, depth: int) -> DungeonMap:
        is_last = depth >= config.depth.floors
        theme = self._generate_floor_theme(depth)
        if theme is None:
            theme = self._fallback_theme(depth)
        self._floor_themes[depth] = theme
        layout = generate_level(
            is_last=is_last,
            depth=depth,
            layout_hint=theme.layout_bias,
            structures=theme.structures,
            terrain_features=theme.terrain_features,
            water_density=theme.water_density,
        )
        level = DungeonMap(game=self, layout=layout)
        self._populate(level, depth, is_last, theme=theme)
        return level

    def _enemies_for_depth(self, depth: int) -> list[str]:
        """Return names of non-boss enemies valid for the given depth."""
        return [e.data.name for e in self.db.enemy_db.all_for_depth(depth)]

    def _generate_floor_theme(self, depth: int) -> "FloorTheme | None":
        if not self.llm.enabled:
            return None
        history_ctx = "\n".join(self._theme_history[-3:]) or "none yet"
        valid_at_depth = self._enemies_for_depth(depth)
        messages = [
            {"role": "system", "content": (
                "You are a dungeon theme generator for a dark fantasy roguelike. "
                "Output ONLY a single valid JSON object with exactly these keys: "
                "name (string), description (string), "
                "layout_bias (exactly one of: cave rooms bsp any), "
                f"enemy_bias (JSON array of 0-3 names chosen ONLY from: {', '.join(_VALID_BIAS_ENEMIES)}), "
                "trap_type (exactly one of: dart poison teleport alarm any), "
                "trap_density (exactly one of: low normal high), "
                "loot_bias (exactly one of: potions scrolls weapons gold balanced), "
                "ambient (one atmospheric sentence, max 15 words), "
                "structures (JSON array of 0-2 names chosen ONLY from: "
                "shrine mushroom_grove overgrown_room ruined_hall frozen_pond campsite poison_marsh standing_stones), "
                "terrain_features (JSON array of 0-2 names chosen ONLY from: lava_pools chasms water_pools), "
                "water_density (exactly one of: small medium large — size of ambient water pools; use large for flooded/sunken/drowned themes, small for dry/normal themes). "
                "Choose structures, terrain_features, and water_density that match the theme's name and description. "
                "No markdown fences, no explanation, no thinking — pure JSON only."
            )},
            {"role": "user", "content": (
                f"Depth {depth} of {config.depth.floors}. "
                f"Previous floor themes for narrative continuity:\n{history_ctx}\n"
                f"Enemies available at depth {depth}: {', '.join(valid_at_depth)}. "
                "Generate the theme for this floor."
            )},
        ]
        future = self.llm.complete_json_async(messages, max_tokens=2500, timeout=90.0)
        clear_screen()
        self.print(f"[stairs]Descending to Depth {depth}...[/stairs]", highlight=False)
        from rich.live import Live
        from rich.text import Text
        with Live(console=self.rich_console, refresh_per_second=10) as live:
            i = 0
            while not future.done():
                live.update(Text.from_markup(
                    f"[flavor]{_THEME_SPINNER[i % len(_THEME_SPINNER)]} The dungeon stirs...[/flavor]"
                ))
                time.sleep(0.1)
                i += 1
        data = future.result()
        if not isinstance(data, dict):
            return None
        _valid_layout = {"cave", "rooms", "bsp", "any"}
        _valid_trap = {"dart", "poison", "teleport", "alarm", "any"}
        _valid_density = {"low", "normal", "high"}
        _valid_loot = {"potions", "scrolls", "weapons", "gold", "balanced"}
        _valid_water = {"small", "medium", "large"}
        validated_structures = [
            s for s in (data.get("structures") or [])
            if isinstance(s, str) and s in _VALID_STRUCTURES
        ][:2]
        validated_terrain_features = [
            t for t in (data.get("terrain_features") or [])
            if isinstance(t, str) and t in _VALID_TERRAIN_FEATURES
        ][:2]
        theme = FloorTheme(
            name=str(data.get("name", "")),
            description=str(data.get("description", "")),
            layout_bias=data.get("layout_bias", "any") if data.get("layout_bias") in _valid_layout else "any",
            enemy_bias=[e for e in (data.get("enemy_bias") or []) if e in _VALID_BIAS_ENEMIES],
            trap_type=data.get("trap_type", "any") if data.get("trap_type") in _valid_trap else "any",
            trap_density=data.get("trap_density", "normal") if data.get("trap_density") in _valid_density else "normal",
            loot_bias=data.get("loot_bias", "balanced") if data.get("loot_bias") in _valid_loot else "balanced",
            ambient=str(data.get("ambient", "")),
            structures=validated_structures,
            terrain_features=validated_terrain_features,
            water_density=data.get("water_density", "small") if data.get("water_density") in _valid_water else "small",
        )
        if theme.name:
            self._theme_history.append(f"{theme.name}: {theme.description}")
        return theme

    def _populate(self, level: DungeonMap, depth: int, is_last: bool, theme=None) -> None:
        pool = list(level.floor_cells)
        random.shuffle(pool)
        suy, sux = level.stairs_up

        def far_cell():
            while pool:
                y, x = pool.pop()
                if abs(y - suy) + abs(x - sux) > 3:
                    return (y, x)
            return None

        # Monsters (count scales with depth); biased towards theme enemies when theme present.
        count = config.spawn.enemies_base + config.spawn.enemies_per_depth * (depth - 1)
        for _ in range(count):
            if theme and theme.enemy_bias and random.random() < 0.6:
                loader = self.db.enemy_db.random_biased(depth, theme.enemy_bias)
            else:
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

        # Loose loot (counts biased by floor theme when present).
        loot = theme.loot_bias if theme else "balanced"
        if loot == "potions":    pot_n, scr_n, wpn_n, gold_mult = 5, 1, 1, 1.0
        elif loot == "scrolls":  pot_n, scr_n, wpn_n, gold_mult = 1, 4, 1, 1.0
        elif loot == "weapons":  pot_n, scr_n, wpn_n, gold_mult = 1, 1, 4, 1.0
        elif loot == "gold":     pot_n, scr_n, wpn_n, gold_mult = 1, 1, 1, 2.5
        else:                    pot_n, scr_n, wpn_n, gold_mult = config.spawn.floor_potions, config.spawn.floor_scrolls, config.spawn.floor_weapons, 1.0
        for _ in range(pot_n):
            self._scatter(level, self._depth_potion(depth))
        for _ in range(scr_n):
            scrolls = self.db.item_db.scrolls
            weights = [s.weight for s in scrolls]
            self._scatter(level, random.choices(scrolls, weights=weights, k=1)[0])
        for _ in range(wpn_n):
            weapon = copy.copy(random.choice(self.db.item_db.weapons[1:]))
            from .classes.item_egos import maybe_brand_weapon
            maybe_brand_weapon(weapon, depth, vault_bonus=0)
            self._scatter(level, weapon)
        for _ in range(config.spawn.floor_armour):
            armour = copy.copy(random.choice(self.db.item_db.armour))
            from .classes.item_egos import maybe_ego_armour
            maybe_ego_armour(armour, depth, vault_bonus=0)
            self._scatter(level, armour)
        for _ in range(config.spawn.floor_throwables):
            self._scatter(level, copy.copy(random.choice(self.db.item_db.throwables)))
        for _ in range(config.spawn.floor_spellbooks):
            self._scatter(level, random.choice(self.db.item_db.spellbooks))
        for _ in range(config.spawn.gold_piles):
            cell = self._floor_cell(level)
            if cell:
                cell.gold += int(random.randint(2, 6 + depth * 2) * gold_mult)

        # Hidden traps (depth-scaled, density and type biased by theme).
        _density_mult = {"low": 0.5, "normal": 1.0, "high": 1.8}
        density = _density_mult.get(theme.trap_density if theme else "normal", 1.0)
        trap_count = max(1, int((config.spawn.traps_base + depth // 2) * density))
        trap_pool = ["dart", "poison", "teleport", "alarm"]
        if theme and theme.trap_type != "any":
            trap_pool = [theme.trap_type] * 3 + trap_pool
        for _ in range(trap_count):
            y, x = random.choice(level.floor_cells)
            cell = level.matrix[y][x]
            if cell.trap is None and not cell.items and cell.gold == 0 \
                    and abs(y - suy) + abs(x - sux) > 4:
                cell.trap = random.choice(trap_pool)

        # Vault treasure (or the Orb chamber on the last floor), then any temple.
        self._fill_vault(level, depth, is_last)
        self._fill_temple(level, depth)

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
        # Vaults get a +3 floor bonus on ego generation (per DCSS notes).
        VAULT_BONUS = 3
        from .classes.item_egos import maybe_brand_weapon
        if depth in _SHARD_FLOORS:
            shard_name, guardian_name = _SHARD_FLOORS[depth]
            sy, sx = cells.pop()
            level.matrix[sy][sx].items.append(DungeonShard(shard_name))
            level.matrix[sy][sx].gold += random.randint(30, 60)
            loader = self.db.enemy_db.search_enemy(name=guardian_name)
            if loader and cells:
                gy, gx = min(cells, key=lambda c: abs(c[0] - sy) + abs(c[1] - sx))
                boss = loader.load()
                boss.awake = True
                level.place_occupant(boss, gy, gx)
                level.enemies.append(boss)
            if is_last and cells:  # legendary blade still rewards reaching the deepest floor
                bsy, bsx = cells.pop()
                level.matrix[bsy][bsx].items.append(self.db.item_db.search_item(name="Sword of Zot"))
        else:
            wy, wx = cells.pop()
            weapon_name = _VAULT_WEAPONS[min(depth - 1, len(_VAULT_WEAPONS) - 1)]
            weapon = self.db.item_db.search_item(name=weapon_name)
            if weapon is not None:
                weapon = copy.copy(weapon)
                maybe_brand_weapon(weapon, depth, vault_bonus=VAULT_BONUS)
            level.matrix[wy][wx].items.append(weapon)
            if cells:
                gy, gx = cells.pop()
                level.matrix[gy][gx].gold += random.randint(15, 30 + depth * 5)
            if cells:
                py, px = cells.pop()
                level.matrix[py][px].items.append(self.db.item_db.search_item(name="Strong Healing Potion"))

    def _fill_temple(self, level, depth: int) -> None:
        if not level.temple_cells:
            return
        cells = list(level.temple_cells)
        random.shuffle(cells)
        for _ in range(min(3, len(cells))):  # guardians, a notch tougher than the floor
            loader = self.db.enemy_db.random_for_depth(min(config.depth.floors, depth + 1))
            if not loader or not cells:
                continue
            sy, sx = cells.pop()
            if level.matrix[sy][sx].occupant is None:
                enemy = loader.load()
                level.place_occupant(enemy, sy, sx)
                level.enemies.append(enemy)
        if cells:  # a strong weapon as the prize
            wy, wx = cells.pop()
            weapon_name = _VAULT_WEAPONS[min(depth, len(_VAULT_WEAPONS) - 1)]
            level.matrix[wy][wx].items.append(self.db.item_db.search_item(name=weapon_name))
        if cells:
            gy, gx = cells.pop()
            level.matrix[gy][gx].gold += random.randint(20, 40 + depth * 5)
        pool = self.db.item_db.potions + self.db.item_db.scrolls
        for _ in range(2):
            if cells:
                cy, cx = cells.pop()
                level.matrix[cy][cx].items.append(random.choice(pool))

    def enter_level(self, depth: int, mode: str) -> None:
        # Clear summons from the current map before leaving
        if hasattr(self, "map") and self.map:
            for s in list(self.map.summon):
                self.on_summon_death(s)
        self.player._channeling.clear()
        self.player._channel_targets.clear()
        if depth not in self.levels:
            self.levels[depth] = self._new_level(depth)
        self.depth = depth
        self.map = self.levels[depth]
        if mode == "up" and self.map.stairs_down:
            self.player.location = self.map.stairs_down
        else:
            self.player.location = self.map.stairs_up
        self.player.energy = TURN  # ready to act immediately on arrival
        self.map.update_fov()
        if mode == "down":
            self.message(f"[stairs]You arrive on Depth {depth}.[/stairs]")
        else:
            self.message(f"[stairs]You climb to Depth {depth}.[/stairs]")
        theme = self._floor_themes.get(depth)
        if theme and theme.name:
            self.message(f"[flavor]{theme.name}[/flavor]")
        if theme and theme.ambient:
            self.message(f"[flavor]{theme.ambient}[/flavor]")
        if depth >= 6:
            self._queue_hint(f"deep_floor_{depth}", {
                "trigger": f"player descends to depth {depth}, one of the deepest and most dangerous floors",
                "depth": depth, "background": self.player.background,
                "hp": self.player.health, "max_hp": self.player.max_health,
            })
        else:
            self._queue_hint(f"floor_{depth}", {
                "trigger": f"player descends to depth {depth} of the dungeon",
                "depth": depth, "background": self.player.background,
                "hp": self.player.health, "max_hp": self.player.max_health,
            })

    # --- turn engine (energy scheduler) --------------------------------
    def spend_turn(self, cost: int = TURN) -> None:
        """Subtract `cost` energy from the player (default one full turn)."""
        self.player.energy -= cost
        self.moves += 1
        self.time.add()
        # MP regeneration
        if self.player.mp < self.player.max_mp:
            spellcasting = self.player.skills.get_level("Spellcasting") if self.player.skills else 0.0
            regen = 0.2 + spellcasting * 0.05
            self.player.mp = min(self.player.max_mp, self.player.mp + regen)

    def _tick_burning_terrain(self) -> None:
        expired = []
        for (y, x), remaining in self.map.burning_cells.items():
            cell = self.map.matrix[y][x]
            if cell.occupant:
                dmg = max(1, random.randint(1, 3))
                if cell.occupant is self.player:
                    dmg = self.player.apply_resistance("fire", dmg)
                cell.occupant.health -= dmg
                if cell.occupant is self.player:
                    self.message(f"[burn]You are scorched by burning terrain! ({dmg} damage)[/burn]")
                else:
                    self.message(f"[burn]{style_text(cell.occupant.name, 'enemy')} is scorched by flames![/burn]", drop=dmg)
                    if cell.occupant.health <= 0:
                        self.on_enemy_death(cell.occupant)
            self.map.burning_cells[(y, x)] = remaining - 1
            if remaining - 1 <= 0:
                expired.append((y, x))
        for y, x in expired:
            del self.map.burning_cells[(y, x)]
            if self.map.matrix[y][x].feature == "burning":
                self.map.matrix[y][x].feature = None

    def _detonate_inner_flame(self, enemy) -> None:
        """Area fire explosion on death from a Scroll of Immolation victim."""
        ey, ex = enemy.location
        radius = 1
        self.message(
            f"[fire]{style_text(enemy.name, 'enemy')} erupts in a column of flame![/fire]"
        )
        for dy in range(-radius, radius + 1):
            for dx in range(-radius, radius + 1):
                if dy * dy + dx * dx > radius * radius:
                    continue
                ny, nx = ey + dy, ex + dx
                if not self.map.in_bounds(ny, nx):
                    continue
                cell = self.map.matrix[ny][nx]
                if cell.occupant is self.player:
                    dmg = max(1, random.randint(3, 6) + self.depth)
                    dmg = self.player.apply_resistance("fire", dmg)
                    self.player.health -= dmg
                    self.message(
                        f"[fire]You are caught in the blast! ({dmg} fire damage)[/fire]", drop=dmg
                    )
                    if self.player.health <= 0:
                        self.game_over("dead")
                        return
                elif getattr(cell.occupant, "is_enemy", False) and cell.occupant is not enemy:
                    other = cell.occupant
                    dmg = max(1, random.randint(2, 5))
                    other.health -= dmg
                    self.message(
                        f"[fire]{style_text(other.name, 'enemy')} is caught in the blast.[/fire]",
                        drop=dmg,
                    )
                    if other.health <= 0:
                        self.on_enemy_death(other)
        # Mark the source cell as briefly burning
        self.map.burning_cells[(ey, ex)] = 2

    def game_tick(self) -> None:
        """One unit of world time: grant energy, tick statuses, run monster and summon actions."""
        self._tick_burning_terrain()
        self.map.tick_floor_effects()
        p = self.player
        p.energy += p.effective_speed()
        p.status.tick(p, self)
        if p.health <= 0:
            self.game_over("dead")
            return
        for e in self.map.enemies:
            e.energy += e.effective_speed()
        for e in list(self.map.enemies):
            if e.health > 0:
                e.status.tick(e, self)
                if e.health <= 0:
                    self.on_enemy_death(e)
        for e in list(self.map.enemies):
            while e.health > 0 and e.energy >= TURN:
                e.act()
                e.energy -= TURN
                if self.player.health <= 0:
                    self.game_over("dead")
                    return
        # Summon ticks: energy, AI, despawn
        for s in list(self.map.summon):
            if s.health <= 0:
                self.on_summon_death(s)
                continue
            s.despawn_timer -= 1
            if s.despawn_timer <= 0:
                self.message(f"[flavor]Your {s.name} dissolves into nothingness.[/flavor]")
                self.on_summon_death(s)
                continue
            s.energy += s.effective_speed()
            s.status.tick(s, self)
            if s.health <= 0:
                self.on_summon_death(s)
                continue
        for s in list(self.map.summon):
            while s.health > 0 and s.energy >= TURN:
                self._summon_act(s)
                s.energy -= TURN

    def advance_world(self) -> None:
        """Advance time until the player can act again, then settle fog and detection."""
        while self.player.energy < TURN and not self.over:
            self.game_tick()
        if self.over:
            return
        if self.player.health <= 0:
            self.game_over("dead")
            return
        found = self.map.auto_detect_secret()
        if found == "door":
            self.message("[warn]You notice a hidden door nearby![/warn]")
        elif found == "trap":
            self.message("[warn]You spot a hidden trap nearby![/warn]")
        self.map.update_fov()

    def on_enemy_death(self, enemy) -> None:
        # Scroll of Immolation: a dying enemy with inner_flame detonates for fire damage.
        if enemy.status.has("inner_flame"):
            self._detonate_inner_flame(enemy)
        self.player.gain_xp(enemy.xp_drop)
        if self.player.skills:
            leveled = self.player.skills.distribute(enemy.xp_drop)
            for name in leveled:
                level = self.player.skills.get(name).level
                self.message(f"[level]Your {name} skill is now {level:.1f}![/level]")
        self.map.remove_occupant(enemy)
        if enemy in self.map.enemies:
            self.map.enemies.remove(enemy)
        ey, ex = enemy.location
        self.map.matrix[ey][ex].gold += enemy.coin_drop
        self.message(enemy.texts.death)
        if enemy.tier != "boss":
            self._queue_hint("first_kill", {
                "trigger": f"player slew their first enemy, a {enemy.name}",
                "depth": self.depth, "background": self.player.background,
                "hp": self.player.health, "max_hp": self.player.max_health,
            })
        if enemy.tier == "boss":
            self.message("[success]The guardian falls! The shard lies unguarded — take it.[/success]")
            self._queue_hint(f"boss_{enemy.name}", {
                "trigger": f"player just slew the {enemy.name}, a powerful boss guardian",
                "depth": self.depth, "background": self.player.background,
                "hp": self.player.health, "max_hp": self.player.max_health,
            })

    def _summon_act(self, s) -> None:
        """One AI tick for a friendly summon: follow player, attack nearest visible enemy."""
        targets = [e for e in self.map.enemies if getattr(e, "is_enemy", False) and e.health > 0
                   and (e.y, e.x) in self.map.visible]
        if targets:
            # Pick closest visible enemy
            target = min(targets, key=lambda t: max(abs(t.y - s.y), abs(t.x - s.x)))
            dist = max(abs(s.y - target.y), abs(s.x - target.x))
            if dist == 1:
                # Attack
                hit = random.randint(1, 100) < s.accuracy
                if hit:
                    dmg = s.attack_base + random.randint(s.attack_range[0], s.attack_range[1])
                    dmg = max(1, dmg)
                    target.health -= dmg
                    self.message(
                        f"[action]Your {s.name} attacks the {style_text(target.name, 'enemy')}![/action]",
                        drop=dmg,
                    )
                    if target.health <= 0:
                        self.on_enemy_death(target)
                else:
                    self.message(f"[action]Your {s.name} misses the {style_text(target.name, 'enemy')}.[/action]")
            else:
                # Move toward target
                self._summon_step(s, target.y, target.x)
        else:
            # No enemies — roam near player (~2 tiles avg)
            pdist = max(abs(s.y - self.player.y), abs(s.x - self.player.x))
            if pdist > 3:
                self._summon_step(s, self.player.y, self.player.x)  # keep up
            elif random.random() < 0.35:
                self._summon_random_step(s)

    def _summon_step(self, s, ty, tx) -> None:
        best = None
        best_d = 999
        for dy, dx in [(-1,0),(1,0),(0,-1),(0,1),(-1,-1),(-1,1),(1,-1),(1,1)]:
            ny, nx = s.y + dy, s.x + dx
            if not self.map.in_bounds(ny, nx):
                continue
            cell = self.map.matrix[ny][nx]
            if cell.terrain not in config.terrain.walkable:
                continue
            occ = cell.occupant
            if occ and occ is not s:
                if occ is self.player:
                    self.message(f"[action]Swapped places with {style_text(s.name, 'item')}.[/action]")
                    self.map.move_occupant(self.player, s.y, s.x)
                    self.map.move_occupant(s, ny, nx)
                    return
                continue
            nd = max(abs(ny - ty), abs(nx - tx))
            if nd < best_d:
                best_d = nd
                best = (ny, nx)
        if best:
            self.map.move_occupant(s, best[0], best[1])

    def _summon_random_step(self, s) -> None:
        dirs = list(DIRS.values())
        random.shuffle(dirs)
        for dy, dx in dirs:
            ny, nx = s.y + dy, s.x + dx
            if not self.map.in_bounds(ny, nx):
                continue
            cell = self.map.matrix[ny][nx]
            if cell.terrain not in config.terrain.walkable:
                continue
            occ = cell.occupant
            if occ and occ is not s:
                if occ is self.player:
                    self.message(f"[action]Swapped places with {style_text(s.name, 'item')}.[/action]")
                    self.map.move_occupant(self.player, s.y, s.x)
                    self.map.move_occupant(s, ny, nx)
                    return
                continue
            self.map.move_occupant(s, ny, nx)
            return

    def on_summon_death(self, summon) -> None:
        if summon in self.map.summon:
            self.map.summon.remove(summon)
        self.map.remove_occupant(summon)

    def awaken_floor(self) -> None:
        for enemy in self.map.enemies:
            enemy.awake = True

    # --- player commands ------------------------------------------------
    def interact_npc(self, npc) -> bool:
        """Open an NPC's menu. Returns True if a turn was spent (the player stepped past)."""
        result = None
        if isinstance(npc, DungeonTrader):
            for item in npc.stuff:  # merchants' wares are displayed identified
                self.identify(item, announce=False)
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
        if isinstance(item, DungeonShard):
            cell.items.remove(item)
            self.player.shards.add(item.name)
            count = len(self.player.shards)
            self.message(f"[shard]You seize the {item.name}! ({count}/3 sigil shards)[/shard]")
            if count == 3:
                self.message("[warn]The Broken Sigil is whole. The dungeon shudders — flee to the surface![/warn]")
                self.awaken_floor()
                self._queue_hint("all_shards", {
                    "trigger": "player assembled the complete Broken Sigil and must now flee to the surface",
                    "depth": self.depth, "background": self.player.background,
                    "hp": self.player.health, "max_hp": self.player.max_health,
                })
            else:
                remaining = 3 - count
                self.message(f"[flavor]{remaining} shard{'s' if remaining > 1 else ''} remain hidden in the depths.[/flavor]")
                if count == 1:
                    self._queue_hint("first_shard", {
                        "trigger": "player collected the first shard of a broken sigil",
                        "depth": self.depth, "background": self.player.background,
                        "hp": self.player.health, "max_hp": self.player.max_health,
                    })
            return True
        if isinstance(item, DungeonThrowable):
            stack = next((it for it in self.player.inventory
                          if isinstance(it, DungeonThrowable) and it.name == item.name), None)
            if stack:
                cell.items.remove(item)
                stack.count += item.count
                self.message(f"You pick up {item.count} more {style_text(item.name, 'item')} "
                             f"([inventory]{stack.count}[/inventory] total).")
                return True
        if len(self.player.inventory) >= self.player.max_inventory:
            self.message("Your pack is full.")
            return False
        cell.items.remove(item)
        self.player.inventory.append(item)
        self.message(f"You pick up the {style_text(self.display_name(item), 'item')}.")
        self._maybe_queue_lore(item)
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
            if len(self.player.shards) == 3:
                self.game_over("win")
            else:
                missing = 3 - len(self.player.shards)
                self.message(
                    f"[warn]You cannot leave — {missing} shard{'s' if missing > 1 else ''} "
                    f"of the Broken Sigil still lie in the depths.[/warn]"
                )
        else:
            self.enter_level(self.depth - 1, mode="up")

    def apply_potion(self, pot) -> None:
        p = self.player
        appearance = self.display_name(pot)
        was_unknown = appearance != pot.name
        self.identify(pot, announce=False)  # learned by drinking; named in the message below
        parts = []
        if pot.effect == "curing":
            cured = p.status.clear_harmful()
            parts.append("the poison drains away" if "poison" in cured else "you feel cleansed")
        elif pot.effect == "might":
            p.status.add("might", pot.duration, pot.potency)
            parts.append("[might]power surges through you[/might]")
        elif pot.effect == "haste":
            p.status.add("haste", pot.duration, pot.potency)
            parts.append("[haste]the world slows around you[/haste]")
        elif pot.effect == "regen":
            p.status.add("regen", pot.duration, pot.potency)
            parts.append("[regen]your wounds begin to knit[/regen]")
        if pot.hp_change > 0:
            if p.health < p.max_health:
                healed = min(p.max_health - p.health, pot.hp_change)
                p.health += healed
                parts.append("you feel rejuvenated")
            elif not pot.effect:
                parts.append("nothing seems to happen")
        effect_text = f" {', '.join(parts)}." if parts else ""
        real = style_text(pot.name, "item")
        if was_unknown:
            self.message(f"You quaff the {style_text(appearance, 'item')} — "
                         f"it is [success]{real}[/success]!{effect_text}")
        else:
            self.message(f"You quaff the {real}.{effect_text}")

    def use_scroll(self, scroll) -> bool:
        appearance = self.display_name(scroll)
        was_unknown = appearance != scroll.name
        self.identify(scroll, announce=False)  # learned by reading; named in the message below
        real = style_text(scroll.name, "item")
        read = (f"You read the {style_text(appearance, 'item')} — it is [success]{real}[/success]!"
                if was_unknown else f"You read the {real}.")
        # Silence blocks both spells and scrolls. Check the aura + per-actor status.
        if self.map.silence_aura > 0 or self.player.status.has("silence"):
            self.message(f"[fail]A heavy silence swallows the {real}. The magic fizzles.[/fail]")
            return True

        effect = scroll.effect
        if effect == "identify":
            self.message(read)
            target = self.menu.choose_unidentified(exclude=scroll)
            if target is None:
                self.message("[warn]You stop before the incantation — nothing to identify.[/warn]")
                return False  # don't waste the scroll
            self.identify(target)
            return True
        if effect == "teleport":
            self.message(read)
            self.player.location = self.map.random_walkable()
            self.map.update_fov()
            self.message("[action]You blink across the floor.[/action]")
            return True
        if effect == "amnesia":
            self.message(read)
            target = self.menu.choose_spell_to_forget()
            if target is None:
                self.message("[warn]You have no spells to forget.[/warn]")
                return False
            self.player.known_spells.remove(target)
            if target.name in self.player._channeling:
                self.player._channeling.pop(target.name, None)
                self.player._channel_targets.pop(target.name, None)
            freed = target.level
            self.message(
                f"[flavor]The {style_text(target.name, 'item')} fades from your mind. "
                f"([success]+{freed} spell slot{'s' if freed != 1 else ''}[/success])[/flavor]"
            )
            return True
        if effect == "blinking":
            self.message(read)
            target = self.menu.choose_blink_target()
            if target is None:
                self.message("[warn]You find nowhere to blink to.[/warn]")
                return False
            self.player.location = target
            self.map.update_fov()
            self.message("[action]Space folds around you — you reappear in a chosen spot.[/action]")
            return True
        if effect == "butterflies":
            self.message(read)
            self._summon_butterflies()
            return True
        if effect == "enchant_weapon":
            self.message(read)
            weapon = self.menu.choose_enchantable_weapon(exclude=scroll)
            if weapon is None:
                self.message("[warn]You have no weapon to enchant.[/warn]")
                return False
            # Magical staves (and artefacts) cannot be enchanted (DCSS rule).
            if getattr(weapon, "magical_staff", False):
                self.message(
                    f"[fail]The {style_text(weapon.name, 'weapons')} resists the enchantment "
                    f"— magical staves cannot be enchanted.[/fail]"
                )
                return False
            # Cap at +9 (DCSS max). Preserve the scroll on refusal.
            if getattr(weapon, "enchant", 0) >= 9:
                self.message(
                    f"[warn]The {style_text(weapon.name, 'weapons')} cannot be enchanted further "
                    f"— it has reached the maximum of +9.[/warn]"
                )
                return False
            weapon.enchant = getattr(weapon, "enchant", 0) + 1
            self.identify(weapon, announce=False)
            self.message(
                f"[success]The {style_text(weapon.name, 'weapons')} gleams "
                f"([level]+1 enchant, now +{weapon.enchant}[/level]).[/success]"
            )
            return True
        if effect == "enchant_armour":
            self.message(read)
            armour = self.menu.choose_enchantable_armour(exclude=scroll)
            if armour is None:
                self.message("[warn]You have no armour to enchant.[/warn]")
                return False
            # Cap at +9.
            if getattr(armour, "enchant", 0) >= 9:
                self.message(
                    f"[warn]The {style_text(armour.name, 'armour')} cannot be enchanted further "
                    f"— it has reached the maximum of +9.[/warn]"
                )
                return False
            armour.enchant = getattr(armour, "enchant", 0) + 1
            self.identify(armour, announce=False)
            self.message(
                f"[success]The {style_text(armour.name, 'armour')} hardens "
                f"([level]+1 enchant, now +{armour.enchant}[/level]).[/success]"
            )
            return True
        if effect == "fear":
            self.message(read)
            self._aoe_affect_enemies("fear", "flees in terror", duration=8, potency=1)
            return True
        if effect == "fog":
            self.message(read)
            self._spawn_fog()
            self.message("[flavor]A thick mist rolls out from the parchment.[/flavor]")
            self.map.update_fov()
            return True
        if effect == "immolation":
            self.message(read)
            count = self._aoe_affect_enemies("inner_flame", "catches inner flame", duration=999, potency=1)
            if not count:
                self.message("[warn]No creatures caught in sight.[/warn]")
            else:
                self.message(f"[fire]The inner flame ignites in {count} creature{'s' if count != 1 else ''}.[/fire]")
            return True
        if effect == "noise":
            self.message(read)
            self.awaken_floor()
            self.message("[warn]A thunderous crack rolls through the dungeon![/warn]")
            return True
        if effect == "poison_cloud":
            self.message(read)
            placed = self._spawn_poison_clouds()
            self.message(f"[poison]Noxious green clouds bloom in {placed} tile{'s' if placed != 1 else ''}.[/poison]")
            return True
        if effect == "revelation":
            self.message(read)
            self.map.reveal_all()
            self.player.status.add("see_invisible", 6, 1)
            self.message("[success]The floor's layout floods into your mind.[/success]")
            return True
        if effect == "silence":
            self.message(read)
            self.map.silence_aura = 10
            self.message("[fail]A heavy silence settles over the floor.[/fail]")
            return True
        if effect == "summoning":
            self.message(read)
            count = self._summon_random_enemies(2 + self.depth // 3)
            self.message(f"[action]{count} creature{'s' if count != 1 else ''} claw their way into being.[/action]")
            return True
        if effect == "torment":
            self.message(read)
            self._torment_all()
            return True
        if effect == "vulnerability":
            self.message(read)
            self._aoe_affect_enemies("vulnerable", "grows vulnerable", duration=10, potency=1)
            self.player.status.add("vulnerable", 5, 1)
            self.message("[fail]You too feel the will of magic weakening around you.[/fail]")
            return True
        if effect == "brand_weapon":
            self.message(read)
            weapon = self.menu.choose_enchantable_weapon(exclude=scroll)
            if weapon is None:
                self.message("[warn]You have no weapon to brand.[/warn]")
                return False
            # Magical staves cannot be branded (DCSS rule).
            if getattr(weapon, "magical_staff", False):
                self.message(
                    f"[fail]The {style_text(weapon.name, 'weapons')} rejects the brand — "
                    f"magical staves cannot be branded.[/fail]"
                )
                return False
            brand = random.choice(list(BRAND_CHOICES))
            weapon.brand = brand
            self.identify(weapon, announce=False)
            self.message(
                f"[success]The {style_text(weapon.name, 'weapons')} is imbued with "
                f"{style_text(brand, 'item')}[/success]"
            )
            return True
        if effect == "acquirement":
            self.message(read)
            self._do_acquirement()
            return True
        # Fallback: no handler.
        self.message(f"{read} (no effect implemented for {effect!r})")
        return True

    # --- scroll effect helpers -----------------------------------------
    def _aoe_affect_enemies(self, status_name: str, verb: str,
                             duration: int, potency: int) -> int:
        """Apply a status effect to every visible enemy. Returns count affected."""
        count = 0
        for e in self.map.enemies:
            if e.health <= 0:
                continue
            if (e.y, e.x) not in self.map.visible:
                continue
            if getattr(e, "is_summon", False):
                continue
            e.status.add(status_name, duration, potency)
            count += 1
        if count:
            self.message(
                f"[warn]Every visible enemy {verb}.[/warn]"
            )
        return count

    def _spawn_fog(self) -> None:
        """Spread a fog cloud outwards from the player's location."""
        py, px = self.player.location
        radius = 6
        for r in range(radius + 1):
            for dy in range(-r, r + 1):
                for dx in range(-r, r + 1):
                    if dy * dy + dx * dx > r * r:
                        continue
                    ny, nx = py + dy, px + dx
                    if not self.map.in_bounds(ny, nx):
                        continue
                    self.map.fog_cells[(ny, nx)] = max(self.map.fog_cells.get((ny, nx), 0), 12 - r)

    def _spawn_poison_clouds(self) -> int:
        """Mark every walkable, visible, unoccupied tile as a poison cloud for a few turns."""
        placed = 0
        for y, x in self.map.visible:
            cell = self.map.matrix[y][x]
            if not cell.walkable:
                continue
            if cell.occupant is not None:
                continue
            if cell.terrain in (T.DEEP_WATER, T.LAVA, T.CHASM):
                continue
            self.map.burning_cells[(y, x)] = 3  # poison "ticks" via burning mechanism
            placed += 1
        return placed

    def _summon_butterflies(self) -> None:
        """Summon 3 friendly summons that shove enemies away from the player."""
        from .classes.enemies import DungeonEnemy, EnemyTexts
        for _ in range(3):
            loader = self.db.enemy_db.search_enemy(name="Bat")  # reuse bat as proxy
            if not loader:
                continue
            d = loader.data
            texts = EnemyTexts(
                critical_hit=f"The {{}} flutters around.",
                hit=f"The {{}} buffets you.",
                missed_hit=f"The {{}} flits past.",
                death=f"The {{}} dissolves into motes of light.",
                enemy_name=d.name,
            )
            b = DungeonEnemy(
                name="Butterfly",
                symbol="*",
                tier="weak",
                health=1, coin_drop=0, xp_drop=0,
                attack_base=0, attack_range=[0, 0], accuracy=0,
                texts=texts, game=self,
                ranged=False, attack_distance=0, speed=14,
            )
            b.is_enemy = False
            b.is_summon = True
            b.is_butterfly = True
            b.despawn_timer = 18
            b.awake = True
            # Place adjacent to player
            py, px = self.player.location
            candidates = []
            for dy, dx in [(-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (-1, 1), (1, -1), (1, 1)]:
                ny, nx = py + dy, px + dx
                if self.map.in_bounds(ny, nx) and self.map.matrix[ny][nx].walkable \
                        and self.map.matrix[ny][nx].occupant is None:
                    candidates.append((ny, nx))
            if not candidates:
                continue
            ny, nx = random.choice(candidates)
            self.map.place_occupant(b, ny, nx)
            self.map.summon.append(b)
        # Push enemies in adjacent cells away by one tile
        py, px = self.player.location
        for dy, dx in [(-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (-1, 1), (1, -1), (1, 1)]:
            ny, nx = py + dy, px + dx
            if not self.map.in_bounds(ny, nx):
                continue
            occ = self.map.matrix[ny][nx].occupant
            if not getattr(occ, "is_enemy", False):
                continue
            # Try to shove one step further away
            fy, fx = ny + dy, nx + dx
            if self.map.in_bounds(fy, fx) and self.map.matrix[fy][fx].walkable \
                    and self.map.matrix[fy][fx].occupant is None:
                self.map.move_occupant(occ, fy, fx)

    def _summon_random_enemies(self, n: int) -> int:
        """Spawn n random native enemies adjacent to or near the player."""
        from .classes.enemies import DungeonEnemy
        spawned = 0
        depth = self.depth
        py, px = self.player.location
        # Build candidate tiles in spiral from player
        candidates = []
        for r in range(1, 8):
            for dy in range(-r, r + 1):
                for dx in range(-r, r + 1):
                    if abs(dy) != r and abs(dx) != r:
                        continue
                    ny, nx = py + dy, px + dx
                    if not self.map.in_bounds(ny, nx):
                        continue
                    cell = self.map.matrix[ny][nx]
                    if not cell.walkable or cell.occupant is not None:
                        continue
                    candidates.append((ny, nx))
        random.shuffle(candidates)
        for _ in range(n):
            if not candidates:
                break
            loader = self.db.enemy_db.random_for_depth(depth)
            if not loader:
                break
            enemy = loader.load()
            ny, nx = candidates.pop()
            self.map.place_occupant(enemy, ny, nx)
            self.map.enemies.append(enemy)
            spawned += 1
        return spawned

    def _torment_all(self) -> None:
        """Damage all visible creatures (including the player) for torment damage."""
        dmg_player = max(1, random.randint(2, 4) + self.depth)
        self.player.health -= dmg_player
        self.message(f"[fail]Torment tears at your soul! ({dmg_player} damage)[/fail]", drop=dmg_player)
        if self.player.health <= 0:
            self.game_over("dead")
            return
        for e in list(self.map.enemies):
            if e.health <= 0:
                continue
            if (e.y, e.x) not in self.map.visible:
                continue
            if getattr(e, "is_summon", False):
                continue
            d = max(1, random.randint(1, 3) + self.depth // 2)
            e.health -= d
            self.message(f"[fail]{style_text(e.name, 'enemy')} writhes in torment ({d}).[/fail]", drop=d)
            if e.health <= 0:
                self.on_enemy_death(e)

    def _do_acquirement(self) -> None:
        """Offer the player a choice of 3 items tailored to their skills (or 500 gold)."""
        player = self.player
        # Build a pool biased toward the player's high skills.
        pool = []
        if player.skills:
            for skill, info in player.skills.skills.items():
                lvl = info.level if hasattr(info, "level") else 0
                if lvl >= 2.0 and skill in ("Spellcasting", "Conjuration", "Fire Magic",
                                              "Ice Magic", "Earth Magic", "Air Magic",
                                              "Poison Magic", "Transmutation",
                                              "Translocation", "Summoning"):
                    # Add a relevant spellbook
                    pool.extend(self.db.item_db.spellbooks)
                if lvl >= 2.0 and skill in ("Long Blades", "Short Blades", "Maces & Flails",
                                              "Axes", "Polearms", "Staves", "Ranged", "Throwing"):
                    pool.extend(self.db.item_db.weapons)
                if lvl >= 1.5 and skill == "Armour":
                    pool.extend(self.db.item_db.armour)
        # Always offer some potions / scrolls
        pool.extend(self.db.item_db.potions)
        pool.extend(self.db.item_db.scrolls)
        if not pool:
            pool = list(self.db.item_db.items)
        offerings = []
        chosen = random.sample(pool, min(3, len(pool)))
        for item in chosen:
            if isinstance(item, DungeonWeapon):
                lo, hi = item.attack_range
                detail = f"Atk {item.base_attack} (+{lo}-{hi}), {item.accuracy}% acc"
            elif isinstance(item, DungeonArmour):
                detail = f"AC {item.ac}, {item.slot}"
            elif isinstance(item, DungeonPotion):
                detail = f"heals +{item.hp_change} HP"
            elif isinstance(item, DungeonScroll):
                detail = f"{item.effect.replace('_', ' ')}"
            elif isinstance(item, DungeonSpellBook):
                detail = f"teaches {', '.join(item.spells)}"
            else:
                detail = item.description
            offerings.append((item, detail))
        if len(offerings) < 3:
            # Pad with random items if not enough
            extras = random.sample(list(self.db.item_db.items),
                                   min(3 - len(offerings), len(self.db.item_db.items)))
            for item in extras:
                if any(it is item for it, _ in offerings):
                    continue
                offerings.append((item, item.description))
        choice = self.menu.choose_acquirement(offerings)
        if choice[0] == "cancel":
            return
        if choice[0] == "gold":
            _, amount = choice
            player.coins += amount
            self.message(f"[success]{amount} gold coins materialise at your feet.[/success]")
            return
        item = choice[1]
        # Place in inventory if room, otherwise at feet
        if len(player.inventory) < player.max_inventory:
            player.inventory.append(item)
            self.identify(item, announce=False)
            self.message(f"[success]You acquire a {style_text(item.name, 'item')}.[/success]")
        else:
            cell = self.map.matrix[player.y][player.x]
            import copy
            cell.items.append(copy.copy(item))
            self.message(f"[success]A {style_text(item.name, 'item')} appears at your feet.[/success]")

    def search(self) -> None:
        if self.map.search(self.player.y, self.player.x):
            self.message("[warn]You uncover something hidden nearby![/warn]")
        else:
            self.message("You search the area but find nothing.")

    # --- traps ----------------------------------------------------------
    def trigger_trap(self, cell) -> None:
        kind = cell.trap
        cell.trap_hidden = False
        p = self.player
        if kind == "dart":
            dmg = random.randint(2, 4 + self.depth)
            p.health -= dmg
            self.message(f"[trap]A dart trap fires![/trap] You take {dmg} damage.")
        elif kind == "poison":
            dmg = random.randint(1, 3)
            p.health -= dmg
            p.status.add("poison", random.randint(4, 7), 1 + self.depth // 4)
            self.message(f"[trap]A needle springs out![/trap] [poison]You are poisoned![/poison]")
        elif kind == "teleport":
            p.location = self.map.random_walkable()
            self.map.update_fov()
            self.message("[trap]A teleport trap whisks you across the floor![/trap]")
        elif kind == "alarm":
            self.awaken_floor()
            self.message("[trap]An alarm trap blares! The floor's monsters stir.[/trap]")

    # --- temple altar ---------------------------------------------------
    def bless_at_altar(self, cell) -> None:
        cell.feature = None  # a single blessing per altar
        p = self.player
        p.health = p.max_health
        p.status.add("regen", 15, 2)
        self.message("[success]You kneel at the ancient altar. Warmth floods you — "
                     "fully healed and blessed with [regen]Regeneration[/regen].[/success]")

    # --- ranged combat --------------------------------------------------
    def _ranged_source(self):
        """Pick what `fire()` should use: an equipped ranged weapon, or a thrown
        item from the pack (chosen by the player if more than one stack exists)."""
        weapon = self.player.equipped
        if getattr(weapon, "ranged", False):
            return weapon
        throwables = [it for it in self.player.inventory
                      if isinstance(it, DungeonThrowable) and it.count > 0]
        if not throwables:
            return None
        if len(throwables) == 1:
            return throwables[0]
        return self.menu.choose_throwable(throwables)

    def fire(self) -> int:
        """Fire a ranged weapon or throw. Returns the energy cost of the action
        (0 if no shot was fired, otherwise the weapon's ranged delay)."""
        weapon = self._ranged_source()
        if weapon is None:
            self.message("You have no ranged weapon equipped and nothing to throw.")
            return 0
        rng = weapon.range
        py, px = self.player.location

        def reachable(e):
            return (max(abs(e.y - py), abs(e.x - px)) <= rng
                    and self.map._line_of_sight(py, px, e.y, e.x))

        targets = sorted((e for e in self.map.visible_enemies() if reachable(e)),
                         key=lambda e: max(abs(e.y - py), abs(e.x - px)))
        if not targets:
            self.message("There is no target in range.")
            return 0
        idx = 0
        cursor = list(targets[idx].location)
        while True:
            self._show_target(cursor)
            self.render()
            key = keys.read_key()
            if key in (keys.ESC, "q"):
                self._clear_target()
                return 0
            if key in (keys.ENTER, "f"):
                break
            if key == keys.TAB:
                idx = (idx + 1) % len(targets)
                cursor = list(targets[idx].location)
                continue
            d = keys.read_direction(key)
            if d:
                dy, dx = DIR_DELTA[d]
                ny, nx = cursor[0] + dy, cursor[1] + dx
                if self.map.in_bounds(ny, nx):
                    cursor = [ny, nx]
        ty, tx = cursor
        self._clear_target()
        enemy = self.map.matrix[ty][tx].occupant
        if (enemy and getattr(enemy, "is_enemy", False)
                and max(abs(ty - py), abs(tx - px)) <= rng
                and self.map._line_of_sight(py, px, ty, tx)):
            self.ranged_attack(enemy, weapon)
        else:
            self.message("Your shot flies wide and strikes nothing.")
            self._consume_throwable(weapon)
        # Ranged cost = weapon's delay (bows/crossbows slow, throwables default 10).
        return max(1, getattr(weapon, "delay", TURN))

    def _show_target(self, cursor) -> None:
        self.target_cursor = (cursor[0], cursor[1])
        self.target_path = self.map.line_points(
            self.player.y, self.player.x, cursor[0], cursor[1])[1:-1]

    def _clear_target(self) -> None:
        self.target_cursor = None
        self.target_path = None

    # --- examine mode (DCSS-style) --------------------------------------
    def _examine_description(self, y: int, x: int) -> str:
        """Build a Rich-markup description string for the tile at (y, x)."""
        cell = self.map.matrix[y][x]

        parts = []

        # Coordinates
        parts.append(f"[flavor]({x},{y})[/flavor]")

        # Unexplored + out of sight: hide everything except the marker.
        if not cell.explored and (y, x) not in self.map.visible:
            parts.append("[warn](unexplored)[/warn]")
            return " ".join(parts)

        # Terrain
        terrain_labels = {
            T.FLOOR: "Floor",
            T.WALL: "Wall",
            T.DOOR_CLOSED: "Closed door",
            T.DOOR_OPEN: "Open door",
            T.SECRET_DOOR: "Wall",
            T.STAIRS_DOWN: "Staircase down",
            T.STAIRS_UP: "Staircase up",
            T.DEEP_WATER: "Deep water",
            T.SHALLOW_WATER: "Shallow water",
            T.LAVA: "Lava",
            T.TREE: "Tree",
            T.CHASM: "Chasm",
            T.GRASS: "Grass",
            T.MUD: "Mud",
        }
        label = terrain_labels.get(cell.terrain, cell.terrain.replace("_", " ").title())
        parts.append(f"[terrain]{label}[/terrain]")

        # Features
        if cell.feature:
            parts.append(f"[warn]{cell.feature.title()}[/warn]")
        if cell.trap and not cell.trap_hidden:
            parts.append(f"[trap]Trap ({cell.trap.replace('_', ' ')})[/trap]")

        # Occupant
        if cell.occupant is not None:
            occ = cell.occupant
            if getattr(occ, "is_enemy", False):
                status_tags = ""
                if occ.status.any():
                    short_map = {"poison": "Psn", "burn": "Brn", "regen": "Reg",
                                 "might": "Mgt", "haste": "Hst", "slow": "Slo",
                                 "confusion": "Cnf"}
                    tags = [short_map.get(n, n[:3].upper()) for n in occ.status.effects]
                    status_tags = f" [flavor]({'/'.join(tags)})[/flavor]"
                parts.append(f"[enemy]{occ.symbol} {occ.name}[/enemy] {occ.health}/{occ.max_health}HP{status_tags}")
                # Tag the enemy's holiness so the player knows when Sacred Scourge
                # or the holy_wrath brand get a damage bonus.
                holiness = getattr(occ, "holiness", "natural")
                if holiness != "natural":
                    parts.append(f"  [flavor]({holiness})[/flavor]")
            elif getattr(occ, "occupation", None):
                parts.append(f"[occupation]{occ.symbol} {occ.name}[/occupation] [flavor]({occ.occupation})[/flavor]")
            else:
                parts.append(f"[occupation]{occ.symbol} {occ.name}[/occupation]")

        # Items on ground
        if cell.items:
            from .classes.items import DungeonWeapon, DungeonThrowable, DungeonPotion, DungeonScroll, DungeonArmour
            for item in reversed(cell.items):
                detail = ""
                if isinstance(item, DungeonWeapon):
                    lo, hi = item.attack_range
                    enchant = getattr(item, "enchant", 0)
                    detail = f" — Atk {item.base_attack + enchant} (+{lo}-{hi}), {item.accuracy + enchant}% acc, {item.hands}-handed"
                    if enchant:
                        detail += f" [level]+{enchant}[/level]"
                    brand = getattr(item, "brand", None)
                    if brand:
                        detail += f" [arcane]({brand})[/arcane]"
                    holiness_bonuses = getattr(item, "dmg_pct_vs_holiness", {}) or {}
                    if holiness_bonuses:
                        bonuses = ", ".join(
                            f"+{int(v*100)}% vs {h}" for h, v in holiness_bonuses.items()
                        )
                        detail += f" [arcane]({bonuses})[/arcane]"
                elif isinstance(item, DungeonThrowable):
                    lo, hi = item.attack_range
                    detail = f" — Atk {item.base_attack} (+{lo}-{hi}), {item.accuracy}% acc, range {item.range}, x{item.count}"
                elif isinstance(item, DungeonPotion):
                    detail = f" — heals +{item.hp_change} HP"
                elif isinstance(item, DungeonArmour):
                    from .classes.item_egos import ARMOUR_EGO_TABLE
                    ego = getattr(item, "ego", None)
                    ego_label = ARMOUR_EGO_TABLE[ego]["label"] if ego in ARMOUR_EGO_TABLE else ""
                    extras = []
                    if getattr(item, "resistances", {}):
                        for r in item.resistances:
                            extras.append(f"r{r[:2].title()}+")
                    if getattr(item, "ev_bonus", 0):
                        extras.append(f"+{item.ev_bonus} EV")
                    if getattr(item, "sh_bonus", 0):
                        extras.append(f"+{item.sh_bonus} SH")
                    if getattr(item, "ranged_dmg_bonus", 0.0):
                        extras.append(f"+{int(item.ranged_dmg_bonus*100)}% ranged")
                    if getattr(item, "grant_see_invisible", False):
                        extras.append("SInv")
                    suffix = f" ({ego_label})" if ego_label else ""
                    extra = f" [{', '.join(extras)}]" if extras else ""
                    detail = f" — {item.slot.title()} AC {item.ac + getattr(item, 'enchant', 0)}{suffix}{extra}"
                elif isinstance(item, DungeonScroll):
                    detail = f" — {item.effect.replace('_', ' ').title()}"
                parts.append(f"[item]{item.symbol} {self.display_name(item)}[/item]{detail}")

        # Gold
        if cell.gold > 0:
            parts.append(f"[gold]{cell.gold} gold[/gold]")

        return "  ".join(parts)

    def examine_mode(self) -> None:
        """DCSS-style examine mode: move cursor, read tile descriptions."""
        cursor = list(self.player.location)
        self.examine_cursor = tuple(cursor)
        self._show_examine(cursor)
        self.render()

        while True:
            key = keys.read_key()

            if key in (keys.ESC, "x", "q"):
                self._clear_examine()
                return

            if key == "v":
                cursor = list(self.player.location)
                self._show_examine(cursor)
                self.render()
                continue

            if key == ".":
                # Cycle through interesting features in line of sight.
                visible_items = []
                for cy in range(self.map.height):
                    for cx in range(self.map.width):
                        if (cy, cx) in self.map.visible:
                            cell = self.map.matrix[cy][cx]
                            if cell.items or cell.occupant or cell.feature or cell.gold > 0:
                                visible_items.append((cy, cx))
                if visible_items:
                    try:
                        idx = (visible_items.index(tuple(cursor)) + 1) % len(visible_items)
                    except ValueError:
                        idx = 0
                    cursor = list(visible_items[idx])
                    self._show_examine(cursor)
                    self.render()
                continue

            d = keys.read_direction(key)
            if d:
                dy, dx = DIR_DELTA[d]
                ny, nx = cursor[0] + dy, cursor[1] + dx
                if self.map.in_bounds(ny, nx) and self._examine_reachable(ny, nx):
                    cursor = [ny, nx]
                    self._show_examine(cursor)
                    self.render()
                continue

    def _show_examine(self, cursor) -> None:
        self.examine_cursor = tuple(cursor)
        self.camera_override = tuple(cursor)
        desc = self._examine_description(cursor[0], cursor[1])
        self.message(f"[menu_header]Examine:[/menu_header] {desc}")

    def _examine_reachable(self, y: int, x: int) -> bool:
        """Cursor can only land on tiles the player can currently see or has seen."""
        if (y, x) in self.map.visible:
            return True
        return self.map.matrix[y][x].explored

    def _clear_examine(self) -> None:
        self.examine_cursor = None
        self.camera_override = None

    def ranged_attack(self, enemy, weapon=None) -> None:
        weapon = weapon or self.player.equipped
        thrown = isinstance(weapon, DungeonThrowable)
        if self.player.skills:
            if thrown:
                self.player.skills.record("Throwing")
            else:
                self.player.skills.record("Ranged")
            self.player.skills.record("Fighting")
        en = style_text(enemy.name, "enemy")
        wn = style_text(weapon.name, "weapons" if not thrown else "throwables")
        verb = "throw your" if thrown else "shoot the"
        if self.godmode:
            self.message(f"[warn][GOD][/warn] Your shot vaporises the {en}.")
            enemy.health = 0
            self.on_enemy_death(enemy)
            self._consume_throwable(weapon)
            return
        dmg_bonus, acc_bonus = self.player.combat_bonus()
        if random.randint(1, 100) <= weapon.accuracy + acc_bonus:
            raw = random.randint(weapon.attack_range[0], weapon.attack_range[1])
            damage = max(1, weapon.base_attack + raw + dmg_bonus)
            self.message(f"You {verb} {wn} at the {en}." if thrown
                         else f"You shoot the {en} with your {wn}.", drop=damage)
            enemy.health -= damage
            if enemy.health <= 0:
                self.on_enemy_death(enemy)
            else:
                self.player.apply_weapon_on_hit(weapon, enemy)
        else:
            self.message(f"Your {'throw' if thrown else 'shot'} whistles past the {en}.")
        self._consume_throwable(weapon)
        if not thrown:
            delay = self.player.ranged_encumbrance_delay()
            if delay:
                self.player.energy -= delay

    def _consume_throwable(self, weapon) -> None:
        """Deplete one unit of a thrown item's stack, dropping it from the pack at zero."""
        if not isinstance(weapon, DungeonThrowable):
            return
        weapon.count -= 1
        if weapon.count <= 0 and weapon in self.player.inventory:
            self.player.inventory.remove(weapon)

    # --- autoexplore ----------------------------------------------------
    def autoexplore(self) -> None:
        def passable(y, x):
            c = self.map.matrix[y][x]
            if c.occupant is not None:
                return False
            if c.terrain in (T.WALL, T.SECRET_DOOR, T.DEEP_WATER, T.LAVA, T.TREE, T.CHASM):
                return False
            if c.trap and not c.trap_hidden:
                return False
            if (y, x) in self.map.excluded_stairs:
                return False
            return True

        def is_goal(cur):
            y, x = cur
            if not self.map.matrix[y][x].explored:
                return False
            for dy, dx in DIR_DELTA.values():
                ny, nx = y + dy, x + dx
                if self.map.in_bounds(ny, nx) and not self.map.matrix[ny][nx].explored:
                    return True
            return False

        for _ in range(1000):
            # Check AFTER advance_world updates the FOV. visible_enemies already
            # filters out dead enemies and summons.
            if self.over:
                break
            visible = self.map.visible_enemies()
            if visible:
                name = visible[0].name
                self.message(f"[warn]Auto-explore halted: a {style_text(name, 'enemy')} is in view.[/warn]")
                break

            visible_before = frozenset(self.map.visible)
            path = self.map.bfs_path(self.player.location, is_goal, passable)
            if not path:
                self.message("[flavor]There is nothing left to explore here.[/flavor]")
                break
            ny, nx = path[0]
            direction = self._dir_to(ny, nx)
            move_cost = self.player.move(direction) if direction else 0
            if not direction or move_cost <= 0:
                break
            self.spend_turn(cost=move_cost)
            self.advance_world()
            self.render()
            time.sleep(0.03)

            # Pause if a staircase just entered view for the first time.
            for cy, cx in self.map.visible - visible_before:
                terrain = self.map.matrix[cy][cx].terrain
                if terrain == T.STAIRS_DOWN:
                    self.message("[stairs]Auto-explore paused: staircase down spotted.[/stairs]")
                    return
                if terrain == T.STAIRS_UP:
                    self.message("[stairs]Auto-explore paused: staircase up spotted.[/stairs]")
                    return

    def _dir_to(self, ny: int, nx: int) -> str | None:
        return {(-1, 0): "n", (1, 0): "s", (0, -1): "w", (0, 1): "e",
                (-1, -1): "nw", (-1, 1): "ne", (1, -1): "sw", (1, 1): "se"}.get(
            (ny - self.player.y, nx - self.player.x))

    # --- staircase navigation -------------------------------------------
    def goto_stairs_menu(self) -> None:
        """G key: prompt the player to navigate to nearest up or down stairs."""
        self.message("[stairs]Go to: [controls]<[/controls] up-stairs  "
                     "[controls]>[/controls] down-stairs  [controls]esc[/controls] cancel[/stairs]")
        self.render()
        key = keys.read_key()
        if key == "<":
            self.goto_stairs("up")
        elif key == ">":
            self.goto_stairs("down")

    def goto_stairs(self, direction: str) -> None:
        """Walk to the nearest known staircase of the given type ('up' or 'down')."""
        coord = self.map.stairs_up if direction == "up" else self.map.stairs_down
        name = "up-stairs" if direction == "up" else "down-stairs"
        if coord is None:
            self.message(f"There are no {name} on this floor.")
            return
        sy, sx = coord
        if not self.map.matrix[sy][sx].explored:
            self.message(f"You haven't found the {name} yet.")
            return
        if self.player.location == coord:
            self.message(f"You are already at the {name}.")
            return

        def passable(y, x):
            c = self.map.matrix[y][x]
            return (c.occupant is None
                    and c.terrain not in (T.WALL, T.SECRET_DOOR, T.DEEP_WATER, T.LAVA, T.TREE, T.CHASM)
                    and not (c.trap and not c.trap_hidden))

        is_goal = lambda cur: cur == coord

        path = self.map.bfs_path(self.player.location, is_goal, passable)
        if not path:
            self.message(f"No clear path to the {name}.")
            return

        self.message(f"[stairs]Travelling to {name}...[/stairs]")
        for _ in range(1000):
            if self.over:
                break
            visible = self.map.visible_enemies()
            if visible:
                name = visible[0].name
                self.message(f"[warn]Travel halted: a {style_text(name, 'enemy')} is in view.[/warn]")
                break
            if self.player.location == coord:
                break
            path = self.map.bfs_path(self.player.location, is_goal, passable)
            if not path:
                self.message(f"Path to {name} is blocked.")
                break
            ny, nx = path[0]
            d = self._dir_to(ny, nx)
            move_cost = self.player.move(d) if d else 0
            if d is None or move_cost <= 0:
                break
            self.spend_turn(cost=move_cost)
            self.advance_world()
            self.render()
            time.sleep(0.03)

    def view_stair(self, direction: str) -> None:
        """[ / ] keys: pan the camera to a known staircase and highlight it."""
        coord = self.map.stairs_up if direction == "up" else self.map.stairs_down
        name = "up-stairs" if direction == "up" else "down-stairs"
        if coord is None:
            self.message(f"There are no {name} on this floor.")
            return
        sy, sx = coord
        if not self.map.matrix[sy][sx].explored:
            self.message(f"You haven't found the {name} yet.")
            return
        py, px = self.player.location
        dist = abs(sy - py) + abs(sx - px)
        excl = " [warn](excluded)[/warn]" if coord in self.map.excluded_stairs else ""
        self.camera_override = coord
        self.stair_cursor = coord
        self.message(
            f"[stairs]{name.capitalize()} is ~{dist} steps away{excl}. "
            f"[controls]G[/controls]+[controls]{'<' if direction == 'up' else '>'}[/controls] "
            f"to travel · any key to return view[/stairs]"
        )

    def exclude_stair(self) -> None:
        """X key: toggle the staircase under the player in/out of the auto-explore exclusion set."""
        terrain = self.player.cell.terrain
        if terrain not in (T.STAIRS_UP, T.STAIRS_DOWN):
            self.message("Stand on a staircase to exclude it from auto-explore.")
            return
        coord = self.player.location
        kind = "Up-stairs" if terrain == T.STAIRS_UP else "Down-stairs"
        if coord in self.map.excluded_stairs:
            self.map.excluded_stairs.discard(coord)
            self.message(f"[stairs]{kind} exclusion removed.[/stairs]")
        else:
            self.map.excluded_stairs.add(coord)
            self.message(f"[warn]{kind} excluded from auto-explore.[/warn]")

    def auto_pickup_menu(self) -> None:
        """Backslash key: toggle which item types are automatically picked up on contact."""
        OPTIONS = [
            ("potion",    "Potions",    "potions",    "!"),
            ("scroll",    "Scrolls",    "scroll",     "?"),
            ("weapon",    "Weapons",    "weapons",    ")"),
            ("armour",    "Armour",     "armour",     "["),
            ("throwable", "Throwables", "throwables", "/"),
            ("spellbook", "Spellbooks", "scroll",     "?"),
            ("gold",      "Gold",       "gold",       "$"),
        ]
        while True:
            clear_screen()
            self.print(
                "[menu_header]Auto-pickup settings[/menu_header] "
                "(number to toggle, [controls]esc[/controls] to close)\n"
            )
            for i, (key, label, style, sym) in enumerate(OPTIONS, 1):
                state = "[success]ON [/success]" if key in self.auto_pickup_types else "[warn]OFF[/warn]"
                self.print(
                    f"  [controls]{i}[/controls]  [{style}]{sym} {label}[/{style}]  {state}",
                    highlight=False,
                )
            k = keys.read_key()
            if k == keys.ESC:
                break
            if k.isdigit() and 1 <= int(k) <= len(OPTIONS):
                typ = OPTIONS[int(k) - 1][0]
                if typ in self.auto_pickup_types:
                    self.auto_pickup_types.discard(typ)
                else:
                    self.auto_pickup_types.add(typ)
        self.render()

    # --- main loop ------------------------------------------------------
    def gameloop(self) -> None:
        self.time = DungeonTimeData(game=self)
        self.log.info(f"started game at {time.time():.2f}")
        self.player.energy = TURN
        while not self.over:
            self.advance_world()
            if self.over:
                break
            self.render()
            key = keys.read_key()
            cost = self.handle(key)
            if cost > 0:
                self.spend_turn(cost=cost)

    def handle(self, key: str) -> int:
        """Dispatch one keypress. Returns the energy cost of the action (0 if no
        turn was spent, TURN for a standard action, attack_cost for melee attacks)."""
        # Clear stair-view overlay on any key that isn't cycling stair views.
        if key not in ("[", "]") and self.camera_override is not None:
            self.camera_override = None
            self.stair_cursor = None

        direction = keys.read_direction(key)
        if direction:
            if self.player.status.has("confusion") and random.random() < 0.5:
                direction = random.choice(list(keys.MOVE_KEYS.values()))
            return self.player.move(direction)
        if key == "g":
            return TURN if self.pickup() else 0
        if key == "A":
            self.menu.armor_ui()
            return 0
        if key in ("d", "i"):
            self.menu.pack()
            return 0
        if key == "f":
            return self.fire()  # fire() returns cost directly
        if key == "o":
            self.autoexplore()
            return 0
        if key == ">":
            return TURN if self.descend() else 0
        if key == "<":
            return TURN if self.ascend() else 0
        if key == "G":
            self.goto_stairs_menu()
            return 0
        if key == "[":
            self.view_stair("up")
            return 0
        if key == "]":
            self.view_stair("down")
            return 0
        if key == "X":
            self.exclude_stair()
            return 0
        if key == "\\":
            self.auto_pickup_menu()
            return 0
        if key == "s":
            self.search()
            return TURN
        if key == "x":
            self.examine_mode()
            return 0
        if key == "S":
            self.save_game()
            return 0
        if key in (".", keys.SPACE):
            self.message("You wait.")
            return TURN
        if key == "m":
            self.menu.skills_ui()
            return 0
        if key == "z":
            return TURN if self.menu.spell_ui() else 0
        if key == "p":
            self.time.pause_menu()
            return 0
        if key == "~":
            self.godmode = not self.godmode
            if self.godmode:
                self.map.reveal_all()
            self.message(f"[warn]Developer god mode {'ENABLED' if self.godmode else 'disabled'}.[/warn]")
            return 0
        if key == "?":
            self.manual_screen()
            self.render()
            return 0
        if key == keys.ESC:
            clear_screen()
            self.print(Panel(
                "[menu_header]Quit[/menu_header]\n\n"
                f"{style_text('S', 'controls')} save & quit    "
                f"{style_text('y', 'controls')} quit (no save)    "
                f"{style_text('n', 'controls')} / {style_text('esc', 'controls')} cancel",
                border_style="grey37"))
            confirm = keys.read_key()
            if confirm == "S":
                self.save_game()
                self.over = True
                self.log.info("game exited by player (saved)")
                clear_screen()
                print("Exiting [Dungeon]...")
                sys.exit()
            if confirm == "y":
                self.over = True
                self.log.info("game exited by player")
                clear_screen()
                print("Exiting [Dungeon]...")
                sys.exit()
            self.render()
            return 0
        return 0

    def manual_screen(self) -> None:
        pages = {
            "0": ("Controls", self._manual_controls),
            "1": ("Game Objective", self._manual_objective),
            "2": ("Combat", self._manual_combat),
            "3": ("Items & Equipment", self._manual_items),
            "4": ("Identification", self._manual_ident),
            "5": ("Skills & Spells", self._manual_skills),
            "6": ("Status Effects", self._manual_status),
            "7": ("NPCs & Services", self._manual_npcs),
            "8": ("Terrain & Map", self._manual_terrain),
            "9": ("Tips", self._manual_tips),
        }
        while True:
            clear_screen()
            lines = [
                "[menu_header]Dungeon.py — Manual[/menu_header]\n",
                f"  {style_text('0', 'controls')}  Controls (keybindings)",
                f"  {style_text('1', 'controls')}  Game Objective",
                f"  {style_text('2', 'controls')}  Combat",
                f"  {style_text('3', 'controls')}  Items & Equipment",
                f"  {style_text('4', 'controls')}  Identification System",
                f"  {style_text('5', 'controls')}  Skills & Spells",
                f"  {style_text('6', 'controls')}  Status Effects",
                f"  {style_text('7', 'controls')}  NPCs & Services",
                f"  {style_text('8', 'controls')}  Terrain & Map Symbols",
                f"  {style_text('9', 'controls')}  Tips\n",
                f"Press a {style_text('number', 'controls')} to view a page, "
                f"{style_text('?', 'controls')} or {style_text('esc', 'controls')} to return.",
            ]
            self.print(Panel("\n".join(lines), border_style="grey37"))
            key = keys.read_key()
            if key in pages:
                clear_screen()
                pages[key][1]()
            if key in ("?", keys.ESC):
                break

    def _manual_controls(self) -> None:
        self.print(Panel(
            "[menu_header]Controls[/menu_header]\n\n"
            "[controls]arrows[/controls] or [controls]hjkl[/controls]  move / attack (walk into a monster)\n"
            "[controls]yubn[/controls]  diagonal movement (nw / ne / sw / se)\n"
            "[controls]f[/controls]  fire a ranged weapon or throw (aim, [controls]f[/controls]/[controls]enter[/controls]; [controls]tab[/controls] cycle targets)\n"
            "[controls]o[/controls]  autoexplore (pauses on enemy or new staircase)\n"
            "[controls]g[/controls]  pick up items (choose which, or take all)\n"
            "[controls]i[/controls] / [controls]d[/controls]  open pack — use, equip, unequip, drop\n"
            "[controls]A[/controls]  armour management\n"
            "[controls]m[/controls]  skills overview\n"
            "[controls]z[/controls]  spellcasting\n"
            "[controls]>[/controls] / [controls]<[/controls]  descend / ascend stairs\n"
            "[controls]G[/controls]  goto stairs — [controls]<[/controls] or [controls]>[/controls] walks to nearest staircase\n"
            "[controls][[/controls] / [controls]][/controls]  pan view to known up/down-stairs\n"
            "[controls]X[/controls]  exclude stair under you from auto-explore\n"
            "[controls]\\\\[/controls]  auto-pickup settings\n"
            "[controls]x[/controls]  examine mode ([controls]v[/controls] to self, [controls].[/controls] cycle features)\n"
            "[controls]s[/controls]  search for secret doors and traps\n"
            "[controls]S[/controls]  save game to disk\n"
            "[controls].[/controls] or [controls]space[/controls]  wait one turn\n"
            "[controls]?[/controls]  this manual    [controls]p[/controls]  pause    [controls]esc[/controls] quit\n"
            "[controls]~[/controls]  toggle god mode (dev)\n\n"
            f"Press {style_text('any key', 'controls')} to return.",
            border_style="grey37"))
        keys.read_key()

    def _manual_objective(self) -> None:
        self.print(Panel(
            "[menu_header]Game Objective[/menu_header]\n\n"
            "Win condition: collect all [success]three shards[/success] of the Broken Sigil\n"
            "and escape to the surface.\n\n"
            "Shards are found on depths [move_count]6, 7, 8[/move_count], each guarded by a boss:\n"
            "  [fail]Flame Guardian[/fail] (deep 6), [fail]Stone Guardian[/fail] (deep 7),\n"
            "  [fail]Shadow Guardian[/fail] (deep 8).\n\n"
            "Once you hold all three shards, the exit unlocks. Return to\n"
            "depth 1, find the up-stairs, and climb out.\n\n"
            "Monsters get tougher on deeper floors. Stock up, level up, and\n"
            "prepare before challenging the guardians.\n\n"
            f"Press {style_text('any key', 'controls')} to return.",
            border_style="grey37"))
        keys.read_key()

    def _manual_combat(self) -> None:
        self.print(Panel(
            "[menu_header]Combat[/menu_header]\n\n"
            "Walk [controls]into[/controls] a monster to attack it (\"bump attack\").\n"
            "Melee damage depends on your weapon, strength, and skills.\n"
            "Accuracy is checked against the target's evasion.\n\n"
            "[controls]f[/controls] enters ranged aiming mode. Move cursor with arrows,\n"
            "[controls]tab[/controls] cycles targets. Press [controls]f[/controls]/[controls]enter[/controls] to fire.\n"
            "Ranged attacks use ammo (arrows, bolts, stones) from your pack.\n\n"
            "Damage shown in message log. Watch your [fail]HP bar[/fail] in HUD.\n"
            "Monsters chase you if they detect you (line-of-sight).\n"
            "You can kite around corners or through doors to lose pursuers.\n\n"
            "Two-handed weapons hit harder but reduce accuracy.\n"
            "Fighting from [warn]shallow water[/warn] or [warn]deep water[/warn] may slow you.\n\n"
            f"Press {style_text('any key', 'controls')} to return.",
            border_style="grey37"))
        keys.read_key()

    def _manual_items(self) -> None:
        self.print(Panel(
            "[menu_header]Items & Equipment[/menu_header]\n\n"
            "[controls]i[/controls] opens your pack. Select an item to use, equip, or drop.\n"
            "[controls]A[/controls] opens armour management (body, shield, helmet, cloak, gloves, boots).\n"
            "Weapons are one-handed or two-handed. Two-handed = more damage,\n"
            "  less accuracy. Can't use a shield with a two-handed weapon.\n\n"
            "Item types: potions ([warn]![/warn]), scrolls ([warn]?[/warn]), weapons ([warn])[/warn]),\n"
            "  armour ([warn][[/warn]), spellbooks ([warn]+[/warn]), shards ([warn]o[/warn]).\n\n"
            "Gold ([warn]$[/warn]) is used at NPC traders. Carry weight limit:\n"
            "  max_inventory items. Stash unneeded gear or sell it.\n\n"
            "Throwing weapons (darts, javelins, tomahawks) stack in pack.\n"
            "Press [controls]f[/controls] to fire them without equipping.\n\n"
            f"Press {style_text('any key', 'controls')} to return.",
            border_style="grey37"))
        keys.read_key()

    def _manual_ident(self) -> None:
        self.print(Panel(
            "[menu_header]Identification System[/menu_header]\n\n"
            "Potions and scrolls start [warn]unidentified[/warn]. You see only an\n"
            "appearance (e.g. \"potion of yellow liquid\", \"scroll of Ytorb\").\n\n"
            "[controls]Use[/controls] (quaff/read) an item to discover its true name.\n"
            "Identified items show their real name in future drops.\n\n"
            "Effects can be helpful or harmful. Quaffing a random potion\n"
            "might heal you — or poison you. Reading an unknown scroll\n"
            "might reveal the map — or summon monsters.\n\n"
            "Risk vs reward: use items when you need them, or wait until\n"
            "you can identify safely (e.g. in a cleared room).\n\n"
            "Some NPCs may sell identified items at a premium.\n\n"
            f"Press {style_text('any key', 'controls')} to return.",
            border_style="grey37"))
        keys.read_key()

    def _manual_skills(self) -> None:
        self.print(Panel(
            "[menu_header]Skills & Spells[/menu_header]\n\n"
            "[controls]m[/controls] opens the skills screen. Skills improve as you use them\n"
            "(e.g. swinging a mace trains Maces & Flails).\n\n"
            "Skill levels boost: damage, accuracy, spell success rate.\n"
            "Aptitudes vary by class — some learn faster in certain skills.\n\n"
            "[controls]z[/controls] opens the spellcasting screen. Select a known spell\n"
            "to cast it. Spells cost [controls]MP[/controls] (magic points).\n\n"
            "MP recovers over time. Intelligence boosts max MP.\n"
            "Equipping a [controls]staff[/controls] matching your spell's school\n"
            "boosts spell power.\n\n"
            "Spell schools: Conjuration, Fire, Ice, Earth, Poison,\n"
            "  Summoning, Translocation, Transmutation.\n\n"
            f"Press {style_text('any key', 'controls')} to return.",
            border_style="grey37"))
        keys.read_key()

    def _manual_status(self) -> None:
        self.print(Panel(
            "[menu_header]Status Effects[/menu_header]\n\n"
            "Status effects appear in the HUD status line.\n\n"
            "[success]Beneficial:[/success]\n"
            "  [controls]Might[/controls]  +damage, lasts several turns\n"
            "  [controls]Haste[/controls]  act more frequently (double speed)\n"
            "  [controls]Regen[/controls]  heal HP over time\n"
            "  [controls]Curing[/controls]  cures poison, restores a bit of HP\n\n"
            "[fail]Harmful:[/fail]\n"
            "  [fail]Poison[/fail]  take damage each turn until cured\n"
            "  [fail]Slow[/fail]  act less frequently (half speed)\n"
            "  [fail]Confusion[/fail]  movement becomes uncontrollable\n\n"
            "Potions grant buffs. Monster attacks (e.g. poison needles,\n"
            "slow bolts) inflict debuffs. Check the message log.\n\n"
            f"Press {style_text('any key', 'controls')} to return.",
            border_style="grey37"))
        keys.read_key()

    def _manual_npcs(self) -> None:
        self.print(Panel(
            "[menu_header]NPCs & Services[/menu_header]\n\n"
            "Friendly NPCs appear on dungeon floors. Walk into them to\n"
            "interact. Press [controls]space[/controls] to step past without trading.\n\n"
            "[controls]Chemist[/controls]  sells potions (healing, buffs, curing)\n"
            "[controls]Blacksmith[/controls]  buys/sells weapons and armour\n"
            "[controls]Merchant[/controls]  general goods: scrolls, food, supplies\n"
            "[controls]Fletcher[/controls]  ranged weapons and ammunition\n"
            "[controls]Healer[/controls]  restores HP for gold (cost scales with missing HP)\n\n"
            "NPCs have base stock plus random extra items each game.\n"
            "Prices are fixed per item. Sell unwanted gear for gold.\n\n"
            "If you have the LLM feature enabled, NPCs greet you with\n"
            "unique dialogue based on their personality.\n\n"
            f"Press {style_text('any key', 'controls')} to return.",
            border_style="grey37"))
        keys.read_key()

    def _manual_terrain(self) -> None:
        self.print(Panel(
            "[menu_header]Terrain & Map Symbols[/menu_header]\n\n"
            "[controls]@[/controls]  you (the player)\n"
            "[controls]#[/controls]  wall    [controls].[/controls]  floor    [controls]+[/controls]  door\n"
            "[controls]>[/controls]  down-stairs    [controls]<[/controls]  up-stairs\n"
            "[controls]~[/controls]  shallow water  [controls]≈[/controls]  deep water\n"
            "[controls]%[/controls]  shrub    [controls]♂[/controls]  mushroom    [controls]%[/controls]  rubble\n"
            "[controls]^[/controls]  hidden trap (revealed by searching)\n\n"
            "Monster symbols: various letters and glyphs (see examine mode).\n"
            "[controls]$[/controls]  gold    [controls]![/controls]  potion    [controls]?[/controls]  scroll\n"
            "[controls])[/controls]  weapon    [controls][[/controls]  armour    [controls]=[/controls]  staff\n"
            "[controls]+[/controls]  spellbook    [controls]o[/controls]  shard\n\n"
            "Use [controls]x[/controls] (examine mode) to inspect any tile in detail.\n"
            "Secret doors look like walls until you [controls]s[/controls]earch nearby.\n\n"
            f"Press {style_text('any key', 'controls')} to return.",
            border_style="grey37"))
        keys.read_key()

    def _manual_tips(self) -> None:
        self.print(Panel(
            "[menu_header]Tips[/menu_header]\n\n"
            "[controls]•[/controls] Search ([controls]s[/controls]) frequently near walls to find secrets.\n"
            "[controls]•[/controls] Use autoexplore ([controls]o[/controls]) to map floors quickly.\n"
            "[controls]•[/controls] Identify potions/scrolls early — knowledge is power.\n"
            "[controls]•[/controls] Save gold for Healers and Blacksmiths.\n"
            "[controls]•[/controls] Stairs are one-way until you find the up-stairs.\n"
            "[controls]•[/controls] Kite tough enemies through doors or around corners.\n"
            "[controls]•[/controls] Don't fight multiple enemies at once — use doorways.\n"
            "[controls]•[/controls] Check every floor for hidden vault rooms.\n"
            "[controls]•[/controls] Two-handed weapons trade accuracy for damage.\n"
            "[controls]•[/controls] Save the game ([controls]S[/controls]) before risky fights.\n"
            "[controls]•[/controls] Adjust auto-pickup ([controls]\\\\[/controls]) to filter junk.\n\n"
            f"Press {style_text('any key', 'controls')} to return.",
            border_style="grey37"))
        keys.read_key()

    # --- endgame --------------------------------------------------------
    def record_leaderboard(self, outcome: str) -> None:
        self.leaderboard.insert({
            "name": self.player.name,
            "outcome": outcome,
            "depth": self.depth,
            "shards": len(self.player.shards),
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
                f"[success]You escape the dungeon with the Broken Sigil made whole![/success]\n"
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
    def __start__(logger, rich_console, load_state: dict | None = None) -> None:
        try:
            d = Dungeon(logger=logger, rich_console=rich_console, load_state=load_state)
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
