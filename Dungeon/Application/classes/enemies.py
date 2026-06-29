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
        holiness: str = "natural",
        # --- Phase 0+ extensions (all optional, defaults preserve behaviour) ---
        spells: list | None = None,
        spell_chance: float = 0.0,
        ai: str = "chase",
        flies: bool = False,
        swims: bool = False,
        amphibious: bool = False,
        invisible: bool = False,
        regen: int = 0,
        splits_on_death: bool = False,
        explodes_on_death: dict | None = None,
        spore_cloud: dict | None = None,
        breath_weapon: dict | None = None,
        on_death: dict | None = None,
        shriek: bool = False,
        resistances: dict | None = None,
        hates_holiness: list | None = None,
        corpseless: bool = False,
        size: str = "medium",
        reach: int = 1,
        constricts: bool = False,
        flee_below_hp: float = 0.0,
        see_invisible: bool = False,
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
        # "natural" | "undead" | "demonic" | "holy". Affects holy_wrath brand
        # and the Sacred Scourge weapon.
        self.holiness = holiness
        # --- Phase 0+ extensions ---
        self.spells: list[str] = list(spells) if spells else []
        self.spell_chance = spell_chance
        self.ai = ai  # "chase" | "flee" | "guard" | "stationary"
        self.flies = flies
        self.swims = swims
        self.amphibious = amphibious
        self.invisible = invisible
        self.regen = regen
        self.splits_on_death = splits_on_death
        self.explodes_on_death = explodes_on_death
        self.spore_cloud = spore_cloud
        self.breath_weapon = breath_weapon
        self.on_death = on_death or {}
        self.shriek = shriek
        self.resistances: dict[str, int] = dict(resistances) if resistances else {}
        self.hates_holiness: list[str] = list(hates_holiness) if hates_holiness else []
        self.corpseless = corpseless
        self.size = size  # "tiny"|"small"|"medium"|"large"|"huge"
        self.reach = max(1, reach)
        self.constricts = constricts
        self.flee_below_hp = flee_below_hp
        self.see_invisible = see_invisible
        # Active constriction victims: target_obj -> turns_remaining
        self.constricting: dict = {}
        self._breath_cd = 0
        self._shrieked = False
        # Phase 3: per-spell cooldowns (spell_name -> turns_remaining).
        self.cooldowns: dict[str, int] = {}

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
        # Phase 3: tick spell cooldowns so cast selection sees current state.
        self.tick_cooldowns()
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
        if self.status.has("paralysis"):
            return
        # Decay breath cooldown.
        if self._breath_cd > 0:
            self._breath_cd -= 1
        # Mob must be able to perceive the player (invisibility check).
        if not self.can_see_player() and pdist > 1:
            # Wander randomly if the player is invisible to us.
            options = list(self._walkable_neighbors())
            if options and random.random() < 0.3:
                self.game.map.move_occupant(self, *random.choice(options))
            return
        # Maintain active constrictions first.
        if self.constricting:
            self._tick_constriction()
            return
        # Cowardly mobs flee when low.
        if self.flee_below_hp > 0 and self.health / max(1, self.max_health) < self.flee_below_hp:
            self._step_away_from(player.y, player.x)
            return
        # Stationary: only attack at range (no movement).
        if self.ai == "stationary":
            # Casters cast in place; ranged mobs shoot.
            if self.spells and self.spell_chance > 0 and random.random() < self.spell_chance:
                sp = self.pick_spell()
                if sp is not None and self.cast_spell(sp, self.game):
                    return
            if self.ranged and self.game.map._line_of_sight(self.y, self.x, player.y, player.x):
                self.attack_player(ranged=True)
            return
        # Guard: act only if player in line of sight.
        if self.ai == "guard" and not self.game.map._line_of_sight(self.y, self.x, player.y, player.x):
            return
        # Flee: step away from player instead of toward.
        if self.ai == "flee":
            if pdist == 1:
                # Adjacent: take a swing.
                self.attack_player()
                return
            self._step_away_from(player.y, player.x)
            return
        # Phase 4: consider breath weapon before spellcasting/melee.
        if self.breath_weapon and self._breath_cd <= 0 \
                and pdist <= int(self.breath_weapon.get("range", 6)):
            if self.breath_weapon_act(self.game):
                return
        # Phase 3: consider spellcasting. Casters preferentially cast if in range.
        if self.spells and self.spell_chance > 0 and random.random() < self.spell_chance:
            sp = self.pick_spell()
            if sp is not None and self.cast_spell(sp, self.game):
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
        if tdist <= self.reach:
            if target is player:
                self.attack_player()
                self._attempt_constrict_on(target)
            else:
                self._attack_target(target)
                self._attempt_constrict_on(target)
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
            if not self.passable_for(cell) or cell.occupant is not None:
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

    def _step_away_from(self, ty: int, tx: int) -> None:
        """Move one tile that maximises distance from (ty, tx)."""
        moves = [(max(abs(ny - ty), abs(nx - tx)), ny, nx) for ny, nx in self._walkable_neighbors()]
        if not moves:
            return
        worst = max(m[0] for m in moves)
        candidates = [m for m in moves if m[0] == worst]
        if not candidates:
            return
        _, ny, nx = random.choice(candidates)
        self.game.map.move_occupant(self, ny, nx)

    def _attempt_constrict_on(self, target) -> None:
        """If this mob constricts, start/maintain constriction on `target`."""
        if not self.constricts:
            return
        if target is self.game.player and target.status.has("constricted"):
            # Refresh duration.
            self.constricting[target] = 6
            return
        # 35% chance per melee swing to start a constriction.
        if random.random() < 0.35:
            self._start_constriction(target)

    # --- Phase 0+ extension helpers ----------------------------------------

    def can_see_player(self) -> bool:
        """True if this mob can currently perceive the player.

        Respects player invisibility, fog, and the mob's own see_invisible flag.
        """
        p = self.game.player
        if getattr(p.status, "has", lambda _: False)("invisible") and not self.see_invisible:
            return False
        return True

    def is_silenced(self) -> bool:
        """True if the floor's silence aura or own status prevents spellcasting."""
        aura = getattr(self.game.map, "silence_aura", 0)
        if aura and aura > 0:
            return True
        if self.status.has("silence"):
            return True
        return False

    def passable_for(self, cell) -> bool:
        """Whether this mob can occupy `cell` (honours flies / swims / amphibious)."""
        if cell.terrain in config.terrain.walkable:
            return True
        if self.flies and cell.terrain in (
            config.terrain.SHALLOW_WATER, config.terrain.DEEP_WATER,
            config.terrain.LAVA, config.terrain.TREE, config.terrain.CHASM,
        ):
            return True
        if self.swims and cell.terrain in (
            config.terrain.SHALLOW_WATER, config.terrain.DEEP_WATER,
        ):
            return True
        if self.amphibious and cell.terrain == config.terrain.SHALLOW_WATER:
            return True
        return False

    def _die_extra(self) -> None:
        """Death-time side effects. Called from on_enemy_death before removal.

        Handles: shriek, explodes_on_death, spore_cloud, splits_on_death, on_death hook.
        """
        game = self.game
        ey, ex = self.y, self.x
        # Shriek: wake everything on the floor (one-shot).
        if self.shriek and not self._shrieked:
            self._shrieked = True
            for other in game.map.enemies:
                if other is not self:
                    other.awake = True
            game.message(f"[warn]{self.name} shrieks! Every monster on the floor stirs.[/warn]")
        # Explodes on death: AoE damage at the death tile.
        if self.explodes_on_death:
            cfg = self.explodes_on_death
            radius = int(cfg.get("radius", 1))
            damage = int(cfg.get("damage", 0))
            dmg_type = cfg.get("type", "")
            game.message(f"[fail]{self.name} explodes![/fail]")
            self._aoe_damage(ey, ex, radius, damage, dmg_type)
        # Spore cloud: lingering area effect.
        if self.spore_cloud:
            cfg = self.spore_cloud
            radius = int(cfg.get("radius", 2))
            duration = int(cfg.get("duration", 6))
            effect = cfg.get("effect", "poison")
            potency = int(cfg.get("potency", 1))
            chance = int(cfg.get("chance", 100))
            for dy in range(-radius, radius + 1):
                for dx in range(-radius, radius + 1):
                    ny, nx = ey + dy, ex + dx
                    if not game.map.in_bounds(ny, nx):
                        continue
                    if max(abs(dy), abs(dx)) > radius:
                        continue
                    game.map.fog_cells[(ny, nx)] = max(
                        game.map.fog_cells.get((ny, nx), 0), duration)
            # Apply immediate status to anyone in the cloud.
            for actor, actor_name in ((game.player, "player"),):
                if max(abs(actor.y - ey), abs(actor.x - ex)) <= radius:
                    if random.randint(1, 100) <= chance:
                        actor.status.add(effect, duration, potency)
                        game.message(
                            f"[{effect}]The {self.name}'s spores wash over you![/{effect}]")
        # Split on death: spawn smaller copies.
        if self.splits_on_death:
            split = self.on_death.get("split", {}) if isinstance(self.on_death, dict) else {}
            count = int(split.get("count", 2)) if split else 2
            child = split.get("child") if split else None
            loader = None
            if child:
                loader = game.db.enemy_db.search_enemy(name=child)
            for _ in range(count):
                ny, nx = self._free_neighbor()
                if ny is None:
                    break
                if loader is not None:
                    copy = loader.load()
                else:
                    # Fallback: half-HP twin of self.
                    copy = DungeonEnemy(
                        name=self.name + " fragment", symbol=self.symbol, tier=self.tier,
                        health=max(1, self.max_health // 4), coin_drop=0,
                        xp_drop=0, attack_base=self.attack_base,
                        attack_range=self.attack_range, accuracy=self.accuracy,
                        texts=self.texts, game=game,
                    )
                copy.health = min(copy.max_health, max(1, self.max_health // 4))
                game.map.place_occupant(copy, ny, nx)
                game.map.enemies.append(copy)
        # Generic on_death hook (e.g. "summon_ghost", "ally_buff", "demon_spawn").
        if isinstance(self.on_death, dict):
            hook = self.on_death.get("effect")
            if hook == "shriek":
                pass  # already handled by self.shriek
            elif hook == "ally_buff":
                buff = self.on_death.get("buff", "might")
                potency = int(self.on_death.get("potency", 1))
                dur = int(self.on_death.get("duration", 10))
                for other in game.map.enemies:
                    if other is self or other.health <= 0:
                        continue
                    if max(abs(other.y - ey), abs(other.x - ex)) <= int(self.on_death.get("radius", 6)):
                        other.status.add(buff, dur, potency)
                game.message(f"[warn]{self.name}'s death rallies its kin![/warn]")
            elif hook == "demon_spawn":
                # Boss-tier: spawn listed demon mobs on death.
                demon_list = self.on_death.get("spawn", [])
                radius = int(self.on_death.get("radius", 4))
                for demon_name in demon_list:
                    loader = game.db.enemy_db.search_enemy(name=demon_name)
                    if not loader:
                        continue
                    ny, nx = self._free_neighbor()
                    if ny is None:
                        break
                    copy = loader.load()
                    copy.health = copy.max_health
                    game.map.place_occupant(copy, ny, nx)
                    game.map.enemies.append(copy)
                if demon_list:
                    game.message(
                        f"[fail]{self.name}'s death tears a rift, "
                        f"and {demon_list[0]} claws its way through![/fail]")
            # demon_spawn nested inside ally_buff hook (Pandemonium Lord etc.)
            if self.on_death.get("demon_spawn"):
                spec = self.on_death["demon_spawn"]
                demon_list = spec.get("spawn", [])
                radius = int(spec.get("radius", 4))
                for demon_name in demon_list:
                    loader = game.db.enemy_db.search_enemy(name=demon_name)
                    if not loader:
                        continue
                    ny, nx = self._free_neighbor()
                    if ny is None:
                        break
                    copy = loader.load()
                    copy.health = copy.max_health
                    game.map.place_occupant(copy, ny, nx)
                    game.map.enemies.append(copy)
                if demon_list:
                    game.message(
                        f"[fail]{self.name}'s death calls forth {demon_list[0]}![/fail]")
            # minion_spawn (Pikel style): spawn a specific minion type.
            if self.on_death.get("minion_spawn"):
                spec = self.on_death["minion_spawn"]
                minion_name = spec.get("spawn", "")
                count = int(spec.get("count", 1))
                loader = game.db.enemy_db.search_enemy(name=minion_name)
                if loader is not None:
                    spawned = 0
                    for _ in range(count):
                        ny, nx = self._free_neighbor()
                        if ny is None:
                            break
                        copy = loader.load()
                        copy.health = copy.max_health
                        game.map.place_occupant(copy, ny, nx)
                        game.map.enemies.append(copy)
                        spawned += 1
                    if spawned:
                        game.message(
                            f"[warn]A {minion_name} scrambles out from "
                            f"where {self.name} fell![/warn]")
            # DCSS behaviour: caster's summons dissolve when the caster dies.
            for s in list(game.map.summon):
                if getattr(s, "_summoned_by", None) is self and s.health > 0:
                    s.health = 0
                    game.on_summon_death(s)

    def _aoe_damage(self, cy: int, cx: int, radius: int, damage: int, dmg_type: str = "") -> None:
        """Deal `damage` to all valid targets within Chebyshev `radius` of (cy,cx)."""
        game = self.game
        if damage <= 0:
            return
        p = game.player
        if max(abs(p.y - cy), abs(p.x - cx)) <= radius:
            actual = damage
            if dmg_type:
                actual = p.apply_resistance(dmg_type, damage)
            p.health = max(0, p.health - actual)
            game.message(
                f"[fail]You are hit by the blast for {actual} damage![/fail]", drop=actual)
            if p.health <= 0:
                game.game_over("dead")
        for e in list(game.map.enemies):
            if e is self or e.health <= 0:
                continue
            if max(abs(e.y - cy), abs(e.x - cx)) <= radius:
                if dmg_type and e.resistances.get(dmg_type, 0) > 0:
                    continue
                e.health = max(0, e.health - damage)

    def _free_neighbor(self):
        """Return a free walkable (for self) neighbor (y, x) or (None, None)."""
        options = list(self._walkable_neighbors())
        if options:
            return random.choice(options)
        return None, None

    def _start_constriction(self, target) -> None:
        """Begin constricting `target` (player or summon)."""
        if not self.constricts:
            return
        if target in self.constricting:
            return
        self.constricting[target] = 6
        if target is self.game.player:
            target.status.add("constricted", 6, 1)
            self.game.message(
                f"[enemy]{self.name} coils around you![/enemy]")
        else:
            # Summon being constricted; tag the summon object.
            setattr(target, "_constricted_by", self)

    def _tick_constriction(self) -> None:
        """Damage constricted targets and decrement timers."""
        if not self.constricting:
            return
        for t in list(self.constricting.keys()):
            turns = self.constricting[t] - 1
            if turns <= 0 or t.health <= 0 or self.health <= 0:
                self.constricting.pop(t, None)
                if t is self.game.player:
                    t.status.remove("constricted")
                else:
                    if hasattr(t, "_constricted_by") and t._constricted_by is self:
                        delattr(t, "_constricted_by")
                continue
            self.constricting[t] = turns
            dmg = max(1, self.attack_base // 2 + random.randint(0, 2))
            t.health -= dmg
            if t is self.game.player:
                self.game.message(
                    f"[enemy]{self.name} tightens its grip ({dmg} damage).[/enemy]", drop=dmg)
                if t.health <= 0:
                    self.game.game_over("dead")
            else:
                self.game.message(
                    f"[action]{self.name} crushes your {t.name} ({dmg}).[/action]", drop=dmg)
                if t.health <= 0:
                    self.game.on_summon_death(t)

    # --- Phase 3: enemy spellcasting --------------------------------------

    def tick_cooldowns(self) -> None:
        """Decrement per-spell cooldowns at the end of one action tick."""
        if not self.cooldowns:
            return
        for k in list(self.cooldowns.keys()):
            self.cooldowns[k] -= 1
            if self.cooldowns[k] <= 0:
                del self.cooldowns[k]

    def pick_spell(self) -> "DungeonSpell | None":
        """Choose a spell from `self.spells` that is off-cooldown, or None."""
        if not self.spells:
            return None
        db = getattr(getattr(self.game, "db", None), "item_db", None)
        if db is None:
            return None
        # Build list of available spells (off cooldown and defined in DB).
        available = []
        for sname in self.spells:
            if sname in self.cooldowns:
                continue
            sp = db.search_spell(sname)
            if sp is not None:
                available.append(sp)
        if not available:
            return None
        # Weight: prefer damage/control spells; never pick self_teleport at full HP.
        weights = []
        for sp in available:
            w = 1.0
            if sp.effect == "self_teleport":
                w = 0.0 if self.health >= self.max_health // 2 else 4.0
            elif sp.effect in ("projectile", "explosion", "expanding_aoe"):
                w = 2.0
            elif sp.effect == "summon":
                # Prefer summon when below summon cap.
                cap = sp.extra.get("max_active", 99)
                active = sum(
                    1 for s in self.game.map.summon
                    if getattr(s, "_summoned_by", None) is self and s.health > 0
                )
                if active < cap:
                    w = 1.5
                else:
                    w = 0.0
            weights.append(w)
        total = sum(weights)
        if total <= 0:
            return None
        r = random.uniform(0, total)
        acc = 0.0
        for sp, w in zip(available, weights):
            acc += w
            if r <= acc:
                return sp
        return available[-1]

    def cast_spell(self, spell, game) -> bool:
        """Enemy entry point: pick a target and dispatch to the effect handler.

        Returns True if a spell was successfully cast (consumed a turn's worth
        of action). Enemies cast freely: no MP cost, no miscast.
        """
        if self.is_silenced():
            return False
        target = self._pick_spell_target(spell)
        if target is None and spell.effect not in ("self_teleport", "ignite_flora"):
            return False
        # Announce the cast.
        game.message(
            f"[arcane]{self.name} casts [item]{spell.name}[/item]![/arcane]")
        if spell.effect == "projectile":
            self._enemy_projectile(spell, target, game)
        elif spell.effect == "touch":
            self._enemy_touch(spell, target, game)
        elif spell.effect == "status_chain":
            self._enemy_status_chain(spell, target, game)
        elif spell.effect == "expanding_aoe":
            self._enemy_aoe(spell, target, game)
        elif spell.effect == "explosion":
            self._enemy_explosion(spell, target, game)
        elif spell.effect == "ignite_flora":
            self._enemy_ignite_flora(spell, game)
        elif spell.effect == "self_teleport":
            self._enemy_self_teleport(spell, game)
        elif spell.effect == "summon":
            self._enemy_summon(spell, game)
        elif spell.effect == "channel":
            # Sustained beam - handled as a one-shot projectile for AI.
            self._enemy_projectile(spell, target, game)
        else:
            return False
        # Set cooldown proportional to spell level (1-3 turns for low, 4-6 for high).
        cd = 2 + min(5, max(0, spell.level - 1))
        self.cooldowns[spell.name] = cd
        return True

    def _pick_spell_target(self, spell):
        """Return the player, an enemy of the caster, or None."""
        # Most spells target the player.
        p = self.game.player
        if spell.range > 0:
            dist = max(abs(p.y - self.y), abs(p.x - self.x))
            if dist <= spell.range and self.game.map._line_of_sight(self.y, self.x, p.y, p.x):
                return p
            return None
        # Self-range spells (Blink, Ignite Flora) have no target.
        if spell.effect in ("self_teleport", "ignite_flora"):
            return None
        # Touch range: must be adjacent.
        if spell.effect == "touch":
            dist = max(abs(p.y - self.y), abs(p.x - self.x))
            if dist <= 1 and self.game.map._line_of_sight(self.y, self.x, p.y, p.x):
                return p
            return None
        return p

    # --- enemy effect handlers ---------------------------------------------

    def _enemy_projectile(self, spell, target, game):
        from ..utils import style_text
        if target is None:
            return
        en = style_text(target.name, "enemy")
        style_tag = {"fire": "fire", "cold": "ice", "lightning": "lightning",
                     "poison": "poison", "force": "arcane"}.get(
            spell.damage_type, "arcane")
        if spell.damage:
            lo, hi = spell.damage
            dmg = max(1, random.randint(lo, hi))
            if not spell.extra.get("bypass_mr"):
                dmg = max(1, target.apply_resistance(spell.damage_type, dmg))
                if dmg <= 0:
                    game.message(f"[{style_tag}]You resist the {spell.damage_type}![/{style_tag}]")
                    return
            game.message(
                f"[{style_tag}]{en} is struck by {spell.name} for {dmg}![/{style_tag}]",
                drop=dmg,
            )
            target.health -= dmg
            if target.health <= 0:
                game.on_enemy_death(target)
            elif spell.status:
                target.status.add(
                    spell.status["effect"],
                    spell.status.get("duration", 4),
                    spell.status.get("potency", 1))

    def _enemy_touch(self, spell, target, game):
        from ..utils import style_text
        if target is None:
            return
        en = style_text(target.name, "enemy")
        style_tag = {"fire": "fire", "cold": "ice", "lightning": "lightning",
                     "poison": "poison", "force": "arcane"}.get(
            spell.damage_type, "arcane")
        if spell.damage:
            lo, hi = spell.damage
            dmg = max(1, random.randint(lo, hi))
            if not spell.extra.get("bypass_mr"):
                dmg = max(1, target.apply_resistance(spell.damage_type, dmg))
                if dmg <= 0:
                    game.message(f"[{style_tag}]You resist the {spell.damage_type}![/{style_tag}]")
                    return
            game.message(
                f"[{style_tag}]{self.name} reaches out and freezes {en} for {dmg}![/{style_tag}]",
                drop=dmg,
            )
            target.health -= dmg
            if target.health <= 0:
                game.on_enemy_death(target)
        if spell.status:
            target.status.add(
                spell.status["effect"],
                spell.status.get("duration", 4),
                spell.status.get("potency", 1))

    def _enemy_status_chain(self, spell, target, game):
        from ..utils import style_text
        if target is None:
            return
        en = style_text(target.name, "enemy")
        target.status.add("slow", 2, 1)
        if spell.status:
            target.status.add(
                spell.status["effect"],
                spell.status.get("duration", 5),
                spell.status.get("potency", 1))
        game.message(f"[earth]{en} stiffens as stone creeps across their limbs.[/earth]")

    def _enemy_aoe(self, spell, target, game):
        from ..utils import style_text
        cy, cx = (self.y, self.x) if self.ai == "stationary" else (target.y, target.x)
        r = spell.extra.get("radius", 3)
        style_tag = {"fire": "fire", "cold": "ice", "lightning": "lightning",
                     "poison": "poison", "force": "arcane"}.get(
            spell.damage_type, "arcane")
        if not spell.damage:
            return
        lo, hi = spell.damage
        bypass = spell.extra.get("bypass_mr", False)
        for y in range(max(0, cy - r), min(game.map.max_y, cy + r) + 1):
            for x in range(max(0, cx - r), min(game.map.max_x, cx + r) + 1):
                if (y - cy) ** 2 + (x - cx) ** 2 > r * r:
                    continue
                cell = game.map.matrix[y][x]
                if cell.occupant is game.player:
                    dmg = max(1, random.randint(lo, hi))
                    if not bypass:
                        dmg = max(1, cell.occupant.apply_resistance(spell.damage_type, dmg))
                        if dmg <= 0:
                            continue
                    cell.occupant.health -= dmg
                    game.message(
                        f"[{style_tag}]{spell.name} washes over you for {dmg}![/{style_tag}]",
                        drop=dmg,
                    )
                    if cell.occupant.health <= 0:
                        game.game_over("dead")
                        return
        game.message(
            f"[{style_tag}]Power ripples outward from {self.name}.[/{style_tag}]")

    def _enemy_explosion(self, spell, target, game):
        from ..utils import style_text
        if target is None:
            return
        ty, tx = (target.y, target.x) if hasattr(target, "y") else target
        r = spell.extra.get("radius", 1)
        style_tag = {"fire": "fire", "cold": "ice", "lightning": "lightning",
                     "poison": "poison", "force": "arcane"}.get(
            spell.damage_type, "arcane")
        if not spell.damage:
            return
        lo, hi = spell.damage
        bypass = spell.extra.get("bypass_mr", False)
        for y in range(max(0, ty - r), min(game.map.max_y, ty + r) + 1):
            for x in range(max(0, tx - r), min(game.map.max_x, tx + r) + 1):
                if (y - ty) ** 2 + (x - tx) ** 2 > r * r:
                    continue
                cell = game.map.matrix[y][x]
                if cell.occupant is game.player:
                    dmg = max(1, random.randint(lo, hi))
                    if not bypass:
                        dmg = max(1, cell.occupant.apply_resistance(spell.damage_type, dmg))
                        if dmg <= 0:
                            continue
                    cell.occupant.health -= dmg
                    game.message(
                        f"[{style_tag}]{spell.name} detonates on you for {dmg}![/{style_tag}]",
                        drop=dmg,
                    )
                    if cell.occupant.health <= 0:
                        game.game_over("dead")
                        return
                elif cell.occupant and getattr(cell.occupant, "is_summon", False):
                    dmg = max(1, random.randint(lo, hi))
                    if not bypass and getattr(cell.occupant, "_summoned_by", None) is game.player:
                        dmg = max(1, cell.occupant.apply_resistance(spell.damage_type, dmg))
                    cell.occupant.health -= dmg
                    if cell.occupant.health <= 0:
                        game.on_summon_death(cell.occupant)

    def _enemy_ignite_flora(self, spell, game):
        from ..utils import style_text
        burned = 0
        if not spell.damage:
            return
        lo, hi = spell.damage
        for y, x in list(game.map.visible):
            cell = game.map.matrix[y][x]
            if cell.terrain in ("grass", "tree") or cell.feature in ("shrub", "mushroom"):
                if cell.terrain in ("grass", "tree"):
                    cell.feature = "burning"
                game.map.burning_cells[(y, x)] = 5
                burned += 1
                if cell.occupant and getattr(cell.occupant, "is_enemy", False):
                    dmg = max(1, random.randint(lo, hi))
                    cell.occupant.health -= dmg
                    if cell.occupant.health <= 0:
                        game.on_enemy_death(cell.occupant)
        if burned:
            game.message(
                f"[fire]{self.name} ignites the flora around you! {burned} tiles flare.[/fire]")
        else:
            game.message(
                f"[warn]{self.name} gestures, but nothing burns.[/warn]")

    def _enemy_self_teleport(self, spell, game):
        from ..utils import style_text
        candidates = []
        for y, x in game.map.visible:
            cell = game.map.matrix[y][x]
            if cell.walkable and cell.occupant is None and (y, x) != (self.y, self.x):
                candidates.append((y, x))
        if not candidates:
            return
        ny, nx = random.choice(candidates)
        game.map.move_occupant(self, ny, nx)
        game.message(
            f"[arcane]{self.name} folds space and reappears elsewhere.[/arcane]")

    def _enemy_summon(self, spell, game):
        from ..utils import style_text
        from .enemies import DungeonEnemy, EnemyTexts
        # Resolve summon template. Falls back to a small mob.
        summon_type = spell.extra.get("summon_type", "small_mammal")
        mob_map = {
            "small_mammal": ["Rat", "Bat", "Snake"],
            "canine": ["Hound", "Wolf", "Jackal"],
            "wolf": ["Wolf", "Warg", "Hell Hound"],
            "skeletal": ["Skeletal Warrior", "Death Cob"],
            "imp": ["Crimson Imp", "White Imp"],
            "elemental": ["Air Elemental", "Earth Elemental", "Fire Elemental"],
            "spider": ["Wolf Spider", "Jumping Spider", "Tarantella"],
            "snake": ["Adder", "Black Mamba", "Anaconda"],
            "demon": ["Crimson Imp", "Hellwing", "Smoke Demon", "Red Devil"],
        }
        candidates = mob_map.get(summon_type, ["Rat"])
        # Respect summon cap.
        cap = spell.extra.get("max_active", 99)
        active = sum(
            1 for s in game.map.summon
            if getattr(s, "_summoned_by", None) is self and s.health > 0
        )
        if active >= cap:
            return
        # Try each candidate until one loads.
        for mob_name in candidates:
            loader = game.db.enemy_db.search_enemy(name=mob_name)
            if loader is None:
                continue
            d = loader.data
            ny, nx = self._free_neighbor()
            if ny is None:
                return
            # Build texts.
            from .enemies import _DEFAULT_TEXTS
            raw_texts = {**_DEFAULT_TEXTS, **getattr(d, "texts", {})}
            sum_texts = EnemyTexts(
                raw_texts["critical_hit"], raw_texts["hit"],
                raw_texts["missed_hit"], raw_texts["death"], d.name)
            # Stats - slightly buffed.
            base_hp = (d.health_range[0] + d.health_range[1]) // 2
            summon = DungeonEnemy(
                name=d.name, symbol=d.symbol, tier=getattr(d, "tier", "weak"),
                health=base_hp + max(0, self.tier_to_bonus()),
                coin_drop=0, xp_drop=0,
                attack_base=d.attack_base,
                attack_range=d.attack_range,
                accuracy=d.accuracy,
                texts=sum_texts, game=game,
                speed=getattr(d, "speed", 10),
            )
            summon.is_enemy = False
            summon.is_summon = True
            summon.despawn_timer = spell.extra.get("duration", 80)
            summon.awake = True
            summon._summoned_by = self
            game.map.place_occupant(summon, ny, nx)
            game.map.summon.append(summon)
            game.message(
                f"[arcane]{self.name} traces a sigil; a {style_text(d.name, 'enemy')} appears![/arcane]")
            return

    def tier_to_bonus(self) -> int:
        """Small stat boost from caster tier."""
        return {"weak": 0, "mid": 2, "strong": 5, "boss": 10}.get(self.tier, 0)

    # --- Phase 4: breath weapons -------------------------------------------

    def breath_weapon_act(self, game) -> bool:
        """Breathe at the player if in range and off cooldown.

        Cone shape: a 90-degree wedge from the dragon toward the player,
        length = breath.range, width = breath.width (perpendicular to direction).
        """
        cfg = self.breath_weapon
        if not cfg or self._breath_cd > 0:
            return False
        player = game.player
        dist = max(abs(player.y - self.y), abs(player.x - self.x))
        rng = int(cfg.get("range", 6))
        if dist > rng:
            return False
        if not game.map._line_of_sight(self.y, self.x, player.y, player.x):
            return False
        cells = self._cone_cells(self.y, self.x, player.y, player.x,
                                 length=rng, width=int(cfg.get("width", 3)))
        # Apply damage to any target in the cone.
        dmg = cfg.get("damage", [4, 10])
        lo, hi = (dmg[0], dmg[1]) if isinstance(dmg, (list, tuple)) else (dmg, dmg)
        dtype = cfg.get("type", "fire")
        style_tag = {"fire": "fire", "cold": "ice", "lightning": "lightning",
                     "poison": "poison", "steam": "fire",
                     "acid": "poison"}.get(dtype, "fire")
        verb = {"fire": "belches a cone of flame",
                "cold": "exhales a wall of frost",
                "lightning": "crackles with an electrical burst",
                "poison": "spews a cloud of noxious gas",
                "steam": "vents a jet of scalding steam",
                "acid": "hurls a spray of acid"}.get(dtype, "breathes")
        from ..utils import style_text
        game.message(
            f"[{style_tag}]{self.name} {verb}![/{style_tag}]")
        for cy, cx in cells:
            if not game.map.in_bounds(cy, cx):
                continue
            cell = game.map.matrix[cy][cx]
            if cell.occupant is game.player:
                d = random.randint(lo, hi)
                d = max(1, game.player.apply_resistance(dtype, d))
                game.player.health -= d
                game.message(
                    f"[{style_tag}]You are engulfed for {d} damage![/{style_tag}]",
                    drop=d,
                )
                if game.player.health <= 0:
                    game.game_over("dead")
                    return True
            elif cell.occupant and getattr(cell.occupant, "is_summon", False):
                d = random.randint(lo, hi)
                cell.occupant.health -= d
                if cell.occupant.health <= 0:
                    game.on_summon_death(cell.occupant)
        # Optional on-hit status.
        if cfg.get("status"):
            st = cfg["status"]
            if random.randint(1, 100) <= int(st.get("chance", 30)):
                game.player.status.add(
                    st.get("effect", "burn"),
                    st.get("duration", 3),
                    st.get("potency", 1))
        # Set cooldown.
        self._breath_cd = int(cfg.get("cooldown", 6))
        return True

    @staticmethod
    def _cone_cells(cy: int, cx: int, ty: int, tx: int,
                    length: int, width: int) -> list:
        """Return a list of (y, x) cells in a cone from (cy,cx) toward (ty,tx).

        Width controls how wide the cone spreads (in tiles). Cells in the
        cone are those within `width/2` Chebyshev distance of the ray, clipped
        to `length`.
        """
        out = []
        if ty == cy and tx == cx:
            return [(cy, cx)]
        # Normalised direction.
        ddy = ty - cy
        ddx = tx - cx
        dist = max(abs(ddy), abs(ddx))
        if dist == 0:
            return [(cy, cx)]
        ndy = ddy / dist
        ndx = ddx / dist
        # Step along the ray up to `length` tiles, expanding a square
        # perpendicular to the direction by `width/2` tiles.
        half = max(0, width // 2)
        for step in range(length + 1):
            ry = cy + round(ndy * step)
            rx = cx + round(ndx * step)
            for dyy in range(-half, half + 1):
                for dxx in range(-half, half + 1):
                    # Only include if perpendicular: the dot product of the
                    # offset with the direction is < half+1.
                    dot = dyy * ndy + dxx * ndx
                    if abs(dot) > half:
                        continue
                    ny, nx = ry + dyy, rx + dxx
                    if (ny, nx) not in out:
                        out.append((ny, nx))
        return out


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
            holiness=getattr(d, "holiness", "natural"),
            # Phase 0+ forwards - all default-safe.
            spells=getattr(d, "spells", None),
            spell_chance=getattr(d, "spell_chance", 0.0),
            ai=getattr(d, "ai", "chase"),
            flies=getattr(d, "flies", False),
            swims=getattr(d, "swims", False),
            amphibious=getattr(d, "amphibious", False),
            invisible=getattr(d, "invisible", False),
            regen=getattr(d, "regen", 0),
            splits_on_death=getattr(d, "splits_on_death", False),
            explodes_on_death=getattr(d, "explodes_on_death", None),
            spore_cloud=getattr(d, "spore_cloud", None),
            breath_weapon=getattr(d, "breath_weapon", None),
            on_death=getattr(d, "on_death", None),
            shriek=getattr(d, "shriek", False),
            resistances=getattr(d, "resistances", None),
            hates_holiness=getattr(d, "hates_holiness", None),
            corpseless=getattr(d, "corpseless", False),
            size=getattr(d, "size", "medium"),
            reach=getattr(d, "reach", 1),
            constricts=getattr(d, "constricts", False),
            flee_below_hp=getattr(d, "flee_below_hp", 0.0),
            see_invisible=getattr(d, "see_invisible", False),
        )  # type: ignore[call-arg]
