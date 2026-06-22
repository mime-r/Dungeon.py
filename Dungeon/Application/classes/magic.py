"""Magic engine: spell success formula, staff integration, and spell execution."""

import math
import random

from ..config import config
from ..utils import style_text


# Configurable constants for the success formula
class MagicConfig:
    DIFFICULTY_PER_LEVEL = 10
    SPELLCASTING_WEIGHT = 2
    SCHOOL_WEIGHT = 4
    INT_WEIGHT = 2.0
    BASE_FAILURE = 30
    STAFF_SKILL_BONUS = 4.0
    STAFF_DAMAGE_MULT = 0.05
    SEVERE_MISCAST_THRESHOLD = 30


_MAGIC_SCHOOLS = {
    "Staff of Flame": "Fire Magic",
    "Staff of Frost": "Ice Magic",
    "Staff of Earth": "Earth Magic",
    "Staff of Venom": "Poison Magic",
    "Staff of Lightning": "Conjuration",
    "Magic Staff": "Spellcasting",
}


def staff_school(weapon_name: str) -> str | None:
    return _MAGIC_SCHOOLS.get(weapon_name)


def virtual_skill(actual: float, has_staff: bool) -> float:
    if not has_staff:
        return actual
    return actual + MagicConfig.STAFF_SKILL_BONUS


def calculate_failure(spell, player) -> float:
    """Return failure percentage (0.0–99.0) for casting a spell."""
    difficulty = (spell.level * MagicConfig.DIFFICULTY_PER_LEVEL) + spell.base_difficulty

    skills = player.skills
    avg_skill = 0.0
    staff = player.equipped
    staff_s = staff_school(staff.name) if staff else None

    for school in spell.schools:
        actual = skills.get_level(school) if skills else 0.0
        boosted = virtual_skill(actual, staff_s == school)
        avg_skill += boosted
    avg_skill /= max(1, len(spell.schools))

    spellcasting = skills.get_level("Spellcasting") if skills else 0.0
    if staff_s == "Spellcasting":
        spellcasting += MagicConfig.STAFF_SKILL_BONUS
    skill_power = (
        spellcasting * MagicConfig.SPELLCASTING_WEIGHT
        + avg_skill * MagicConfig.SCHOOL_WEIGHT
        + player.intelligence * MagicConfig.INT_WEIGHT
    )

    raw = MagicConfig.BASE_FAILURE + difficulty - skill_power

    if raw <= 0:
        # Exponential decay: asymptotically approach 0
        failure = 2.0 ** (raw / 10.0)
        return max(0.0, min(5.0, failure))
    if raw >= 100:
        return 99.0

    return max(0.0, min(99.0, raw))


def staff_damage_multiplier(spell, player) -> float:
    """Return damage multiplier from staff synergy."""
    staff = player.equipped
    staff_s = staff_school(staff.name) if staff else None
    if not staff_s:
        return 1.0
    if staff_s == "Spellcasting":
        level = player.skills.get_level("Spellcasting") if player.skills else 0.0
        return 1.0 + (MagicConfig.STAFF_DAMAGE_MULT * level)
    if staff_s not in spell.schools:
        return 1.0
    level = player.skills.get_level(staff_s) if player.skills else 0.0
    return 1.0 + (MagicConfig.STAFF_DAMAGE_MULT * level)


def _roll_failure(failure_pct: float) -> str:
    """Return 'success', 'fizzle', or 'miscast' based on RNG."""
    roll = random.uniform(0, 100)
    if roll >= failure_pct:
        return "success"
    if roll >= failure_pct - MagicConfig.SEVERE_MISCAST_THRESHOLD:
        return "fizzle"
    return "miscast"


def resolve_cast(spell, player, game, target=None) -> bool:
    """Attempt to cast a spell. Returns True if the cast succeeded."""
    failure = calculate_failure(spell, player)
    result = _roll_failure(failure)

    if result == "success":
        _execute(spell, player, game, target)
        return True
    if result == "fizzle":
        game.message(f"[warn]You miscast {style_text(spell.name, 'item')}, wasting the magical energy.[/warn]")
        return False
    # Severe miscast
    dmg = random.randint(1, 3 + spell.level)
    player.health -= dmg
    game.message(
        f"[fail]You severely miscast {style_text(spell.name, 'item')}! "
        f"Magical backlash burns you for {dmg} damage![/fail]",
        drop=dmg,
    )
    return False


def _execute(spell, player, game, target):
    effect = spell.effect
    mult = staff_damage_multiplier(spell, player)

    if effect == "projectile":
        _projectile(spell, player, game, target, mult)
    elif effect == "touch":
        _touch(spell, player, game, target, mult)
    elif effect == "channel":
        _channel(spell, player, game, target, mult)
    elif effect == "self_teleport":
        _self_teleport(spell, player, game)
    elif effect == "summon":
        _summon(spell, player, game)
    elif effect == "ignite_flora":
        _ignite_flora(spell, player, game, mult)
    elif effect == "expanding_aoe":
        _expanding_aoe(spell, player, game, mult)
    elif effect == "explosion":
        _explosion(spell, player, game, target, mult)
    elif effect == "status_chain":
        _status_chain(spell, player, game, target)


def _projectile(spell, player, game, target, mult):
    if target is None:
        game.message("No target.")
        return
    en = style_text(target.name, "enemy")
    if spell.damage:
        lo, hi = spell.damage
        raw = random.randint(lo, hi)
        dmg = max(1, int(raw * mult))
        game.message(f"[action]You cast {style_text(spell.name, 'item')}! The {en} is hit by magical force.[/action]", drop=dmg)
        target.health -= dmg
        if target.health <= 0:
            game.on_enemy_death(target)
        elif spell.status:
            target.status.add(spell.status["effect"], spell.status.get("duration", 4), spell.status.get("potency", 1))
    else:
        game.message(f"[action]You cast {style_text(spell.name, 'item')}! The {en} is struck.[/action]")


def _touch(spell, player, game, target, mult):
    if target is None:
        game.message("No target in range.")
        return
    en = style_text(target.name, "enemy")
    dmg_text = {
        "cold": "is frozen solid",
        "fire": "is seared",
        "lightning": "is electrocuted",
        "poison": "is poisoned",
        "force": "is blasted",
    }
    verb = dmg_text.get(spell.damage_type, "is struck")
    if spell.damage:
        lo, hi = spell.damage
        raw = random.randint(lo, hi)
        dmg = max(1, int(raw * mult))
        game.message(f"[action]You cast {style_text(spell.name, 'item')}! The {en} {verb}.[/action]", drop=dmg)
        target.health -= dmg
        if target.health <= 0:
            game.on_enemy_death(target)
    if spell.status:
        target.status.add(spell.status["effect"], spell.status.get("duration", 4), spell.status.get("potency", 1))
        status_verb = {"slow": "slows to a crawl", "confusion": "reels in confusion", "poison": "is poisoned", "burn": "catches fire", "petrify": "begins to turn to stone"}
        sv = status_verb.get(spell.status["effect"], f"is afflicted by {spell.status['effect']}")
        game.message(f"[action]The {en} {sv}![/action]")


def _channel(spell, player, game, target, mult):
    key = spell.name
    if key not in player._channeling:
        player._channeling[key] = 1
        game.message(f"[action]You begin channelling {style_text(spell.name, 'item')}...[/action]")
        return
    turns = player._channeling[key]
    if turns >= spell.extra.get("channel_turns", 3):
        player._channeling.pop(key, None)
        game.message(f"[action]The {style_text(spell.name, 'item')} fades.[/action]")
        return
    player._channeling[key] = turns + 1
    if target and spell.damage:
        en = style_text(target.name, "enemy")
        lo, hi = spell.damage
        raw = random.randint(lo, hi)
        bonus = turns  # each turn adds +1 damage
        dmg = max(1, int((raw + bonus) * mult))
        game.message(f"[action]The {style_text(spell.name, 'item')} sears the {en}! (turn {turns + 1})[/action]", drop=dmg)
        target.health -= dmg
        if target.health <= 0:
            game.on_enemy_death(target)


def _self_teleport(spell, player, game):
    py, px = player.location
    visible = [(y, x) for y, x in game.map.visible if game.map.matrix[y][x].walkable and (y, x) != (py, px)]
    if visible:
        ny, nx = random.choice(visible)
        player.location = (ny, nx)
        game.map.update_fov()
        game.message(f"[action]You cast {style_text(spell.name, 'item')}! You blink across the floor.[/action]")
    else:
        game.message("[warn]Nowhere to blink to![/warn]")


def _summon(spell, player, game):
    summon_type = spell.extra.get("summon_type", "canine")
    duration = spell.extra.get("duration", 81)
    py, px = player.location
    candidates = []
    for dy, dx in [(-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (-1, 1), (1, -1), (1, 1)]:
        ny, nx = py + dy, px + dx
        if game.map.in_bounds(ny, nx) and game.map.matrix[ny][nx].walkable and game.map.matrix[ny][nx].occupant is None:
            candidates.append((ny, nx))
    if not candidates:
        game.message("[warn]No space to summon![/warn]")
        return
    # Determine mob template
    mob_map = {
        "canine": "Canine",
        "small_mammal": random.choice(["Rat", "Bat", "Snake"]),
        "wolf": "Wolf",
    }
    mob_name = mob_map.get(summon_type, "Canine")
    # Enforce max active summons for this spell
    max_active = spell.extra.get("max_active", 99)
    if max_active < 99:
        active = sum(1 for s in game.map.summon if s.health > 0)
        if active >= max_active:
            game.message(f"[warn]You can't maintain any more {style_text(spell.name, 'item')} summons.[/warn]")
            return
    loader = game.db.enemy_db.search_enemy(name=mob_name)
    if not loader:
        game.message("[warn]The summon fizzles![/warn]")
        return
    d = loader.data
    # Scale stats to player level
    base_hp = (d.health_range[0] + d.health_range[1]) // 2
    scaled_hp = base_hp + player.level * 2
    scaled_attack = d.attack_base + player.level // 2
    ny, nx = random.choice(candidates)
    from .enemies import DungeonEnemy, EnemyTexts
    raw_texts = getattr(d, "texts", {})
    sum_texts = EnemyTexts(
        critical_hit=raw_texts.get("critical_hit", "The {} attacks!"),
        hit=raw_texts.get("hit", "The {} attacks!"),
        missed_hit=raw_texts.get("missed_hit", "The {} misses."),
        death=raw_texts.get("death", "The {} vanishes."),
        enemy_name=d.name,
    )
    summon = DungeonEnemy(
        name=d.name,
        symbol=d.symbol,
        tier=getattr(d, "tier", "weak"),
        health=scaled_hp,
        coin_drop=0,
        xp_drop=0,
        attack_base=scaled_attack,
        attack_range=getattr(d, "attack_range", [0, 2]),
        accuracy=getattr(d, "accuracy", 70),
        texts=sum_texts,
        game=game,
        speed=getattr(d, "speed", 10),
    )
    summon.is_enemy = False
    summon.is_summon = True
    summon.despawn_timer = duration
    summon.awake = True
    game.map.place_occupant(summon, ny, nx)
    game.map.summon.append(summon)
    game.message(f"[action]You cast {style_text(spell.name, 'item')}! A {d.name} appears beside you.[/action]")


def _ignite_flora(spell, player, game, mult):
    burned = 0
    duration = spell.extra.get("duration", 5)
    for y, x in game.map.visible:
        cell = game.map.matrix[y][x]
        if cell.terrain in ("grass", "tree", "shrub") or cell.feature == "altar":
            if cell.terrain in ("grass", "tree") or cell.feature in ("shrub",):
                cell.feature = "burning"
                game.map.burning_cells[(y, x)] = duration
                burned += 1
                if cell.occupant and getattr(cell.occupant, "is_enemy", False) and spell.damage:
                    lo, hi = spell.damage
                    dmg = max(1, int(random.randint(lo, hi) * mult))
                    cell.occupant.health -= dmg
                    game.message(f"[fire]{style_text(cell.occupant.name, 'enemy')} is caught in the blaze![/fire]", drop=dmg)
                    if cell.occupant.health <= 0:
                        game.on_enemy_death(cell.occupant)
    if burned:
        game.message(f"[fire]You cast {style_text(spell.name, 'item')}! {burned} tiles burst into flame.[/fire]")
    else:
        game.message(f"[warn]You cast {style_text(spell.name, 'item')}, but there is nothing to burn.[/warn]")


def _expanding_aoe(spell, player, game, mult):
    py, px = player.location
    r = spell.extra.get("radius", 3)
    dmg = spell.damage
    for y in range(max(0, py - r), min(game.map.max_y, py + r) + 1):
        for x in range(max(0, px - r), min(game.map.max_x, px + r) + 1):
            if (y - py) ** 2 + (x - px) ** 2 > r * r:
                continue
            cell = game.map.matrix[y][x]
            if cell.occupant and getattr(cell.occupant, "is_enemy", False):
                target = cell.occupant
                lo, hi = dmg
                raw = random.randint(lo, hi)
                damage = max(1, int(raw * mult))
                target.health -= damage
                game.message(f"[action]The {style_text(target.name, 'enemy')} is caught in the blast.[/action]", drop=damage)
                if target.health <= 0:
                    game.on_enemy_death(target)
                elif spell.status:
                    target.status.add(spell.status["effect"], spell.status.get("duration", 4), spell.status.get("potency", 1))
    game.message(f"[action]You cast {style_text(spell.name, 'item')}! Power ripples outward.[/action]")


def _explosion(spell, player, game, target, mult):
    if target is None:
        game.message("No target selected.")
        return
    ty, tx = target
    r = spell.extra.get("radius", 1)
    for y in range(max(0, ty - r), min(game.map.max_y, ty + r) + 1):
        for x in range(max(0, tx - r), min(game.map.max_x, tx + r) + 1):
            if (y - ty) ** 2 + (x - tx) ** 2 > r * r:
                continue
            cell = game.map.matrix[y][x]
            if cell.occupant and getattr(cell.occupant, "is_enemy", False):
                enemy = cell.occupant
                lo, hi = spell.damage
                raw = random.randint(lo, hi)
                damage = max(1, int(raw * mult))
                enemy.health -= damage
                game.message(f"[action]The explosion engulfs the {style_text(enemy.name, 'enemy')}.[/action]", drop=damage)
                if enemy.health <= 0:
                    game.on_enemy_death(enemy)
                elif spell.status:
                    enemy.status.add(spell.status["effect"], spell.status.get("duration", 4), spell.status.get("potency", 1))
    game.message(f"[action]You cast {style_text(spell.name, 'item')}! The air cracks with power.[/action]")


def _status_chain(spell, player, game, target):
    if target is None:
        game.message("No target.")
        return
    en = style_text(target.name, "enemy")
    game.message(f"[action]You cast {style_text(spell.name, 'item')}! The {en} begins to stiffen.[/action]")
    target.status.add("slow", 2, 1)
    target.status.add("petrify", spell.status.get("duration", 5), spell.status.get("potency", 1))
    game.message(f"[earth]The {en} is turning to stone![/earth]")
