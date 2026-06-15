import random

from ..config import config

_DEFAULT_TEXTS = {
    "critical_hit": "The {} lands a brutal blow!",
    "hit": "The {} hits you.",
    "missed_hit": "The {} misses you.",
    "death": "The {} dies.",
}

_TIER_STYLE = {
    "weak": "enemy_weak",
    "mid": "enemy_mid",
    "strong": "enemy_strong",
    "boss": "enemy_boss",
}


def _fmt(template: str, enemy_name: str) -> str:
    return template.replace("{}", f"[enemy]{enemy_name}[/enemy]")


class EnemyTexts:
    """Formatted combat text templates for an enemy."""

    def __init__(self, critical_hit: str, hit: str, missed_hit: str, death: str, enemy_name: str) -> None:
        self.critical_hit = _fmt(critical_hit, enemy_name)
        self.hit = _fmt(hit, enemy_name)
        self.missed_hit = _fmt(missed_hit, enemy_name)
        self.death = _fmt(death, enemy_name)


class DungeonEnemy:
    """A living dungeon enemy: combat stats, position, and simple chase AI."""

    is_enemy = True

    def __init__(
        self,
        name: str,
        symbol: str,
        tier: str,
        health: int,
        coin_drop: int,
        xp_drop: int,
        attack_base: int,
        attack_range: list[int],
        accuracy: int,
        texts: EnemyTexts,
        game,
    ) -> None:
        self.name = name
        self.symbol = symbol
        self.tier = tier
        self.style = _TIER_STYLE.get(tier, "enemy")
        self.health = health
        self.max_health = health
        self.xp_drop = xp_drop
        self.attack_base = attack_base
        self.attack_range = attack_range
        self.accuracy = accuracy
        self.coin_drop = coin_drop
        self.texts = texts
        self.game = game
        self.location: tuple[int, int] = (0, 0)
        self.awake = False

    @property
    def y(self) -> int:
        return self.location[0]

    @property
    def x(self) -> int:
        return self.location[1]

    def attack_player(self) -> None:
        """Resolve one attack against the player, applying damage and messaging."""
        if self.game.godmode:
            return
        if random.randint(1, 100) < self.accuracy:
            damage = self.attack_base + random.randint(self.attack_range[0], self.attack_range[1])
            crit = damage == self.attack_base + self.attack_range[1]
            self.game.message(self.texts.critical_hit if crit else self.texts.hit, drop=damage)
            self.game.player.health -= damage
        else:
            self.game.message(self.texts.missed_hit)

    def act(self) -> None:
        """Take one turn: wake near the player, then chase and bump-attack."""
        player = self.game.player
        dist = max(abs(self.y - player.y), abs(self.x - player.x))
        if not self.awake:
            if dist <= config.depth.sight_radius:
                self.awake = True
            else:
                return
        if dist == 1:
            self.attack_player()
            return
        self._step_toward(player.y, player.x)

    def _step_toward(self, ty: int, tx: int) -> None:
        moves = []
        for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1),
                        (-1, -1), (-1, 1), (1, -1), (1, 1)):
            ny, nx = self.y + dy, self.x + dx
            if not self.game.map.in_bounds(ny, nx):
                continue
            cell = self.game.map.matrix[ny][nx]
            if cell.terrain not in config.terrain.walkable or cell.occupant is not None:
                continue
            moves.append((max(abs(ny - ty), abs(nx - tx)), ny, nx))
        if not moves:
            return
        moves.sort(key=lambda m: m[0])
        best = moves[0][0]
        _, ny, nx = random.choice([m for m in moves if m[0] == best])
        self.game.map.move_occupant(self, ny, nx)


class DungeonEnemyLoader:
    """Builds a randomized DungeonEnemy from JSON data."""

    def __init__(self, game, data) -> None:
        self.game = game
        self.data = data

    def load(self) -> DungeonEnemy:
        d = self.data
        min_hp, max_hp = d.health_range
        min_coin, max_coin = d.coin_drop_range
        raw_texts = {**_DEFAULT_TEXTS, **getattr(d, "texts", {})}
        texts = EnemyTexts(
            raw_texts["critical_hit"], raw_texts["hit"], raw_texts["missed_hit"],
            raw_texts["death"], d.name,
        )
        return DungeonEnemy(
            name=d.name,
            symbol=d.symbol,
            tier=getattr(d, "tier", "mid"),
            health=random.randint(min_hp, max_hp),
            coin_drop=random.randint(min_coin, max_coin),
            xp_drop=d.xp_drop,
            attack_base=d.attack_base,
            attack_range=d.attack_range,
            accuracy=d.accuracy,
            texts=texts,
            game=self.game,
        )
