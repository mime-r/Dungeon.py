"""Status effects shared by the player and monsters.

A :class:`StatusSet` hangs off each actor as ``.status``. Most effects are passive flags
read elsewhere (might at attack time, haste/slow by the energy scheduler, confusion at
move time); only poison and regeneration do something on each game-tick via :meth:`tick`.
"""

# effect name -> (HUD label, rich style, short tag)
EFFECT_STYLE = {
    "poison": ("Poison", "poison", "Psn"),
    "burn": ("Burning", "burn", "Brn"),
    "regen": ("Regen", "regen", "Reg"),
    "might": ("Might", "might", "Mgt"),
    "haste": ("Haste", "haste", "Hst"),
    "slow": ("Slow", "slow", "Slo"),
    "confusion": ("Confused", "confusion", "Cnf"),
    "petrify": ("Petrified", "petrify", "Ptr"),
    "silence": ("Silenced", "warn", "Sil"),
    "fear": ("Afraid", "warn", "Afr"),
    "inner_flame": ("Inner Flame", "fire", "Flam"),
    "vulnerable": ("Vulnerable", "fail", "Vul"),
    "see_invisible": ("See Invis", "haste", "Eye"),
    "ac_buff": ("Warded", "haste", "Wrd"),
    "paralysis": ("Paralysed", "petrify", "Par"),
    "blind": ("Blinded", "warn", "Bli"),
    "drain_max_hp": ("Draining", "fail", "Drn"),
    "drain_mp": ("Mana Drain", "arcane", "MDr"),
    "bleed": ("Bleeding", "fail", "Bld"),
    "constricted": ("Held", "fail", "Hld"),
    "invisible": ("Invisible", "haste", "Inv"),
    "corrosion": ("Corroded", "fail", "Cor"),
}


class StatusSet:
    """Holds an actor's active effects: name -> {"duration", "potency"}."""

    def __init__(self) -> None:
        self.effects: dict[str, dict] = {}

    def add(self, name: str, duration: int, potency: int = 0) -> None:
        cur = self.effects.get(name)
        if cur:
            cur["duration"] = max(cur["duration"], duration)
            cur["potency"] = max(cur["potency"], potency)
        else:
            self.effects[name] = {"duration": duration, "potency": potency}

    def remove(self, name: str) -> None:
        self.effects.pop(name, None)

    def clear_harmful(self) -> list[str]:
        harmful = [
            n for n in ("poison", "burn", "slow", "confusion", "petrify",
                        "paralysis", "blind", "bleed", "corrosion", "constricted")
            if n in self.effects
        ]
        for n in harmful:
            del self.effects[n]
        return harmful

    def has(self, name: str) -> bool:
        return name in self.effects

    def potency(self, name: str) -> int:
        eff = self.effects.get(name)
        return eff["potency"] if eff else 0

    def any(self) -> bool:
        return bool(self.effects)

    def summary(self) -> list[tuple[str, str]]:
        """List of (label-with-duration, style) for the HUD."""
        out = []
        for name, eff in self.effects.items():
            label, style, _ = EFFECT_STYLE.get(name, (name.title(), "warn", name[:3]))
            out.append((f"{label} {eff['duration']}", style))
        return out

    def tick(self, actor, game) -> None:
        """Advance one game-tick: apply poison/regen, then age out expired effects."""
        is_player = actor is game.player
        for name, eff in list(self.effects.items()):
            if name == "poison":
                dmg = max(1, eff["potency"])
                actor.health -= dmg
                if is_player:
                    game.message(f"[poison]You take {dmg} poison damage.[/poison]")
            elif name == "burn":
                dmg = max(1, eff["potency"])
                actor.health -= dmg
                if is_player:
                    game.message(f"[burn]You are seared for {dmg} fire damage.[/burn]")
            elif name == "inner_flame":
                # Inner Flame: detonates on death (handled in on_enemy_death /
                # on_summon_death / on_player_death), not on the per-tick loop.
                pass
            elif name == "regen":
                healed = min(actor.max_health - actor.health, eff["potency"])
                if healed > 0:
                    actor.health += healed
                    if is_player:
                        game.message(f"[regen]You regenerate {healed} HP.[/regen]")
            elif name == "drain_max_hp":
                # Vampires and similar reduce the actor's max HP.
                if actor.max_health > 1:
                    actor.max_health -= max(1, eff["potency"])
                    if actor.health > actor.max_health:
                        actor.health = actor.max_health
                    if is_player:
                        game.message(
                            f"[fail]Your maximum life is drained! ({actor.max_health})[/fail]")
            elif name == "drain_mp":
                if is_player and getattr(actor, "max_mp", 0) > 0:
                    actor.mp = max(0, actor.mp - max(1, eff["potency"]))
            elif name == "bleed":
                # Bleed damage scales lightly with potency; stationary actors bleed more.
                from random import randint as _r
                dmg = max(1, eff["potency"] + _r(0, 1))
                actor.health -= dmg
                if is_player:
                    game.message(f"[fail]You bleed for {dmg} damage.[/fail]", drop=dmg)
            elif name == "corrosion":
                # Slowly degrades equipped armour (handled by a hook elsewhere);
                # here we just tag the duration.
                pass
            elif name == "paralysis" or name == "constricted" \
                    or name == "blind" or name == "invisible":
                # Pure flag effects; expiry handled below.
                pass
            eff["duration"] -= 1
            if eff["duration"] <= 0:
                del self.effects[name]
                if is_player:
                    label = EFFECT_STYLE.get(name, (name.title(),))[0]
                    game.message(f"[flavor]Your {label} wears off.[/flavor]")
