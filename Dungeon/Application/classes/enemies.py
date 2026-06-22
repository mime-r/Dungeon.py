import random

from ..config import config
from .status import StatusSet

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
    is_summon = False
    despawn_timer = 0

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
        ranged: bool = False,
        attack_distance: int = 1,
        on_hit: dict | None = None,
        speed: int = 10,
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
        self.ranged = ranged
        self.attack_distance = attack_distance
        self.on_hit = on_hit or {}
        self.status = StatusSet()
        self.energy = 0
        self.speed = speed

    @property
    def y(self) -> int:
        return self.location[0]

    @property
    def x(self) -> int:
        return self.location[1]

    def effective_speed(self) -> int:
        s = self.speed
        if self.status.has("haste"):
            s += 5
        if self.status.has("slow"):
            s -= 5
        return max(1, s)

    def attack_player(self, ranged: bool = False) -> None:
        """Resolve one attack against the player, applying damage, status, and messaging."""
        if self.game.godmode:
            return
        player = self.game.player
        hit_chance = max(5, self.accuracy - player.evasion())
        if random.randint(1, 100) < hit_chance:
            damage = (self.attack_base
                      + random.randint(self.attack_range[0], self.attack_range[1])
                      + self.status.potency("might"))
            crit = damage >= self.attack_base + self.attack_range[1]
            damage = max(1, damage - player.armor_class())
            self.game.message(self.texts.critical_hit if crit else self.texts.hit, drop=damage)
            player.health -= damage
            if player.skills:
                player.skills.record("Armour")
                if player.armour.get("shield"):
                    player.skills.record("Shields")
            self._apply_on_hit()
        else:
            self.game.message(self.texts.missed_hit)

    def _apply_on_hit(self) -> None:
        if not self.on_hit:
            return
        if random.randint(1, 100) > self.on_hit.get("chance", 100):
            return
        effect = self.on_hit["effect"]
        self.game.player.status.add(
            effect, self.on_hit.get("duration", 4), self.on_hit.get("potency", 1))
        verb = {"poison": "are poisoned", "slow": "feel sluggish",
                "confusion": "reel in confusion"}.get(effect, f"are afflicted with {effect}")
        self.game.message(f"[{effect}]You {verb}![/{effect}]")

    def _closest_summon(self):
        """Return closest living summon and its Chebyshev distance, or (None, 999)."""
        best = None
        best_d = 999
        for s in self.game.map.summon:
            if s.health <= 0:
                continue
            d = max(abs(s.y - self.y), abs(s.x - self.x))
            if d < best_d:
                best_d = d
                best = s
        return best, best_d

    def _attack_target(self, target) -> None:
        """Resolve one melee attack against a target entity (summon, not player)."""
        hit_chance = max(5, self.accuracy - 5)  # summons have no evasion
        if random.randint(1, 100) < hit_chance:
            dmg = self.attack_base + random.randint(self.attack_range[0], self.attack_range[1])
            dmg = max(1, dmg)
            target.health -= dmg
            self.game.message(f"[enemy]The {self.name} attacks your {target.name}![/enemy]", drop=dmg)
            if target.health <= 0:
                self.game.on_summon_death(target)
        else:
            self.game.message(f"[enemy]The {self.name} misses your {target.name}.[/enemy]")

    def act(self) -> None:
        """Take one turn: wake near the player, then chase, fire, or bump-attack."""
        player = self.game.player
        pdist = max(abs(self.y - player.y), abs(self.x - player.x))
        if not self.awake:
            if pdist <= config.depth.sight_radius + player.stealth_penalty():
                self.awake = True
            else:
                return
        if self.status.has("confusion"):
            self._step_confused()
            return
        if self.status.has("petrify"):
            return
        # Choose closest target (player or summon); player wins ties
        closest_summon, sdist = self._closest_summon()
        if closest_summon and sdist < pdist:
            target = closest_summon
            tdist = sdist
        else:
            target = player
            tdist = pdist
        # Act toward chosen target
        if tdist == 1:
            if target is player:
                self.attack_player()
            else:
                self._attack_target(target)
            return
        if self.ranged and tdist <= self.attack_distance \
                and self.game.map._line_of_sight(self.y, self.x, target.y, target.x):
            if target is player:
                self.attack_player(ranged=True)
            else:
                self._attack_target(target)
            return
        self._step_toward(target.y, target.x)

    def _walkable_neighbors(self):
        for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1),
                        (-1, -1), (-1, 1), (1, -1), (1, 1)):
            ny, nx = self.y + dy, self.x + dx
            if not self.game.map.in_bounds(ny, nx):
                continue
            cell = self.game.map.matrix[ny][nx]
            if cell.terrain not in config.terrain.walkable or cell.occupant is not None:
                continue
            yield ny, nx

    def _step_toward(self, ty: int, tx: int) -> None:
        moves = [(max(abs(ny - ty), abs(nx - tx)), ny, nx) for ny, nx in self._walkable_neighbors()]
        if not moves:
            return
        best = min(m[0] for m in moves)
        _, ny, nx = random.choice([m for m in moves if m[0] == best])
        self.game.map.move_occupant(self, ny, nx)

    def _step_confused(self) -> None:
        options = list(self._walkable_neighbors())
        if options:
            self.game.map.move_occupant(self, *random.choice(options))


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
            ranged=getattr(d, "ranged", False),
            attack_distance=getattr(d, "attack_distance", getattr(d, "range", 1)),
            on_hit=getattr(d, "on_hit", None),
            speed=getattr(d, "speed", 10),
        )
