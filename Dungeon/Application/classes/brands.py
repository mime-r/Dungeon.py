"""Brand-on-hit callbacks for complex DCSS-style weapon brands.

Each callback signature: ``(player, enemy, game) -> None``.
They are referenced by name from BRAND_TABLE via the ``on_hit`` field
and looked up via :func:`brand_on_hit`.
"""
import random

from ..utils import style_text


# --- helpers ---------------------------------------------------------------

def _enemy_name(e) -> str:
    return style_text(getattr(e, "name", "?"), "enemy")


def _mp_drain(player, amount: int) -> None:
    """Antimagic penalty: drain wielder's MP per hit."""
    if amount <= 0:
        return
    actual = min(player.mp, amount)
    if actual > 0:
        player.mp -= actual
        player.game.message(
            f"[arcane]{style_text(player.name or 'You', 'name')} feel{'s' if not player.name else ''} "
            f"a stab of lost mana ({actual}).[/arcane]"
        )


# --- brand callbacks -------------------------------------------------------

def _antimagic(player, enemy, game):
    """DCSS antimagic: silences the enemy and drains 1 MP from the wielder per hit."""
    enemy.status.add("silence", 5, 1)
    game.message(
        f"[arcane]{_enemy_name(enemy)} is struck dumb by your {style_text(player.equipped.name, 'weapons')}![/arcane]"
    )
    _mp_drain(player, 1)


def _chaos(player, enemy, game):
    """DCSS chaos: random effect on each hit (damage / teleport / confuse / burn)."""
    roll = random.random()
    if roll < 0.40:
        # Bonus damage
        extra = random.randint(4, 8)
        enemy.health -= extra
        game.message(
            f"[arcane]Chaotic energy rips through {_enemy_name(enemy)} for {extra}![/arcane]",
            drop=extra,
        )
    elif roll < 0.65:
        # Teleport enemy randomly
        ny, nx = game.map.random_walkable()
        if ny is not None and game.map.in_bounds(ny, nx) and game.map.matrix[ny][nx].walkable \
                and game.map.matrix[ny][nx].occupant is None:
            game.map.move_occupant(enemy, ny, nx)
            game.message(f"[arcane]Chaos warps {_enemy_name(enemy)} away![/arcane]")
    elif roll < 0.85:
        # Confuse
        enemy.status.add("confusion", 5, 1)
        game.message(f"[arcane]{_enemy_name(enemy)} reels in chaotic confusion![/arcane]")
    else:
        # Burn
        enemy.status.add("burn", 4, 2)
        game.message(f"[arcane]Chaotic fire licks at {_enemy_name(enemy)}![/arcane]")


def _distortion(player, enemy, game):
    """DCSS distortion: random translocation effect (blink / banish)."""
    roll = random.random()
    if roll < 0.30:
        # Banish: enemy removed from the floor entirely (rare)
        if enemy in game.map.enemies:
            game.map.enemies.remove(enemy)
        game.map.remove_occupant(enemy)
        game.message(f"[arcane]{_enemy_name(enemy)} is banished by distortion![/arcane]")
    elif roll < 0.75:
        # Teleport enemy to random walkable tile
        ny, nx = game.map.random_walkable()
        if ny is not None and game.map.in_bounds(ny, nx) and game.map.matrix[ny][nx].walkable \
                and game.map.matrix[ny][nx].occupant is None:
            game.map.move_occupant(enemy, ny, nx)
            game.message(f"[arcane]{_enemy_name(enemy)} is shifted elsewhere.[/arcane]")
    else:
        # Blink them next to the player (hostile repositioning)
        py, px = player.location
        for dy, dx in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            ny, nx = py + dy, px + dx
            if game.map.in_bounds(ny, nx) and game.map.matrix[ny][nx].walkable \
                    and game.map.matrix[ny][nx].occupant is None:
                game.map.move_occupant(enemy, ny, nx)
                game.message(
                    f"[arcane]Distortion warps {_enemy_name(enemy)} next to you![/arcane]"
                )
                return


def _protection(player, enemy, game):
    """DCSS protection: grants +5 AC for 5 turns after a hit."""
    player.status.add("ac_buff", 5, 5)
    game.message(
        f"[arcane]Warded by your {style_text(player.equipped.name, 'weapons')}, "
        f"a shimmering shield briefly surrounds you.[/arcane]"
    )


def _spectral(player, enemy, game):
    """DCSS spectral: spawns a spectral weapon that fights alongside the player."""
    from .enemies import DungeonEnemy, EnemyTexts
    if sum(1 for s in game.map.summon if getattr(s, "is_spectral", False)) >= 1:
        return  # already have one
    texts = EnemyTexts(
        critical_hit="The spectral weapon lands a phantom blow!",
        hit="The spectral weapon strikes.",
        missed_hit="The spectral weapon passes through harmlessly.",
        death="The spectral weapon fades into nothingness.",
        enemy_name="Spectral Weapon",
    )
    spectral = DungeonEnemy(
        name="Spectral Weapon",
        symbol="|",
        tier="weak",
        health=10, coin_drop=0, xp_drop=0,
        attack_base=4, attack_range=[1, 3], accuracy=80,
        texts=texts, game=game,
        ranged=False, attack_distance=1, speed=12,
    )
    spectral.is_enemy = False
    spectral.is_summon = True
    spectral.is_spectral = True
    spectral.despawn_timer = 50
    spectral.awake = True
    # Place adjacent to player
    py, px = player.location
    for dy, dx in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
        ny, nx = py + dy, px + dx
        if game.map.in_bounds(ny, nx) and game.map.matrix[ny][nx].walkable \
                and game.map.matrix[ny][nx].occupant is None:
            game.map.place_occupant(spectral, ny, nx)
            game.map.summon.append(spectral)
            game.message("[arcane]A spectral weapon rises to fight alongside you![/arcane]")
            return


def _vampiric(player, enemy, game):
    """DCSS vampiric: heal the player for a portion of damage dealt."""
    heal = random.randint(1, 3)
    before = player.health
    player.health = min(player.max_health, player.health + heal)
    actual = player.health - before
    if actual > 0:
        game.message(
            f"[heal]Your {style_text(player.equipped.name, 'weapons')} drinks the {_enemy_name(enemy)}'s life. "
            f"([heal]+{actual} HP[/heal])[/heal]"
        )
    else:
        game.message(
            f"[arcane]Your {style_text(player.equipped.name, 'weapons')} tries to drain life but you are full.[/arcane]"
        )


# --- dispatch --------------------------------------------------------------

_CALLBACKS = {
    "_brand_antimagic": _antimagic,
    "_brand_chaos": _chaos,
    "_brand_distortion": _distortion,
    "_brand_protection": _protection,
    "_brand_spectral": _spectral,
    "_brand_vampiric": _vampiric,
}


def brand_on_hit(brand_name: str, player, enemy, game):
    """Invoke the on-hit callback registered for a brand, if any."""
    spec = BRAND_TABLE_REF.get(brand_name)
    if not spec:
        return
    name = spec.get("on_hit")
    if not name:
        return
    fn = _CALLBACKS.get(name)
    if fn:
        fn(player, enemy, game)


# Imported lazily to avoid circular import; set by map.py at module load.
BRAND_TABLE_REF: dict = {}
