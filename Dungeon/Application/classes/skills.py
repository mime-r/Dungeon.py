from enum import Enum


class SkillState(str, Enum):
    DISABLED = "-"
    ENABLED = "+"
    FOCUSED = "*"


# Weapon name -> skill category mapping
_WEAPON_SKILL_MAP = {
    # Maces & Flails
    "Club": "Maces & Flails",
    "Whip": "Maces & Flails",
    "Mace": "Maces & Flails",
    "Flail": "Maces & Flails",
    "Morningstar": "Maces & Flails",
    "Dire Flail": "Maces & Flails",
    "Eveningstar": "Maces & Flails",
    "Sacred Scourge": "Maces & Flails",
    "Demon Whip": "Maces & Flails",
    "Great Mace": "Maces & Flails",
    "Giant Club": "Maces & Flails",
    "Giant Spiked Club": "Maces & Flails",
    # Axes
    "Hand Axe": "Axes",
    "Broad Axe": "Axes",
    "Battleaxe": "Axes",
    "War Axe": "Axes",
    "Executioner's Axe": "Axes",
    # Long Blades
    "Short Sword": "Long Blades",
    "Scimitar": "Long Blades",
    "Falchion": "Long Blades",
    "Long Sword": "Long Blades",
    "Demon Blade": "Long Blades",
    "Eudemon Blade": "Long Blades",
    "Double Sword": "Long Blades",
    "Triple Sword": "Long Blades",
    "Great Sword": "Long Blades",
    # Short Blades
    "Dagger": "Short Blades",
    "Quick Blade": "Short Blades",
    "Rapier": "Short Blades",
    # Polearms
    "Spear": "Polearms",
    "Trident": "Polearms",
    "Demon Trident": "Polearms",
    "Halberd": "Polearms",
    "Partisan": "Polearms",
    "Glaive": "Polearms",
    "Bardiche": "Polearms",
    "Trishula": "Polearms",
    # Staves
    "Quarterstaff": "Staves",
    "Training Staff": "Staves",
    "Lajatang": "Staves",
    "Magic Staff": "Staves",
    "Staff of Earth": "Staves",
    "Staff of Flame": "Staves",
    "Staff of Frost": "Staves",
    "Staff of Venom": "Staves",
    "Staff of Lightning": "Staves",
    "Staff of Air": "Staves",
    # Ranged
    "Sling": "Ranged",
    "Hand Crossbow": "Ranged",
    "Short Bow": "Ranged",
    "Orcbow": "Ranged",
    "Long Bow": "Ranged",
    "Crossbow": "Ranged",
    "Arbalest": "Ranged",
    "Hand Cannon": "Ranged",
    "Triple Crossbow": "Ranged",
    # Fists have no weapon skill
    "Fists": None,
}


def skill_for_weapon(name: str) -> str | None:
    return _WEAPON_SKILL_MAP.get(name)


# Default attack delay per weapon skill category (DCSS: higher = slower swing).
# These are sensible midpoints that match DCSS feel without per-weapon JSON churn.
_SKILL_DEFAULT_DELAY: dict[str | None, int] = {
    None: 5,              # Fists — fast
    "Short Blades": 8,    # Dagger, Quick Blade, Rapier
    "Staves": 11,         # Quarterstaff, Lajatang
    "Maces & Flails": 13, # Mace, Flail, Morningstar
    "Long Blades": 14,    # Short Sword through Great Sword
    "Axes": 15,           # Hand Axe through Battleaxe
    "Polearms": 16,       # Spear, Trident, Halberd
    "Ranged": 12,         # Bows + crossbows (varies by specific weapon)
}


def default_delay_for_weapon(name: str) -> int:
    """Return a sensible default attack delay (in energy units) for a weapon by name.

    Falls back to the skill category default, then 10 (TURN) as a last resort.
    Special-case overrides apply for known outliers (Quick Blade, Rapier, etc.)
    so the JSON doesn't have to be touched for every weapon.
    """
    # Per-weapon overrides (DCSS timing tuned for outliers).
    overrides = {
        "Fists": 5,
        "Dagger": 8,
        "Quick Blade": 7,
        "Rapier": 10,
        "Whip": 8,
        "Demon Whip": 8,
        "Short Sword": 11,
        "Scimitar": 13,
        "Long Sword": 14,
        "Great Sword": 17,
        "Double Sword": 16,
        "Triple Sword": 19,
        "Hand Axe": 13,
        "Broad Axe": 15,
        "Battleaxe": 17,
        "War Axe": 16,
        "Executioner's Axe": 19,
        "Spear": 12,
        "Trident": 13,
        "Halberd": 15,
        "Glaive": 17,
        "Bardiche": 18,
        "Partisan": 13,
        "Trishula": 14,
        "Sling": 10,
        "Short Bow": 11,
        "Long Bow": 13,
        "Orcbow": 14,
        "Crossbow": 15,
        "Hand Crossbow": 13,
        "Arbalest": 19,
        "Hand Cannon": 23,
        "Triple Crossbow": 25,
        "Quarterstaff": 11,
        "Lajatang": 13,
        "Club": 13,
        "Mace": 13,
        "Flail": 14,
        "Morningstar": 14,
        "Dire Flail": 15,
        "Eveningstar": 15,
        "Great Mace": 16,
        "Giant Club": 17,
        "Giant Spiked Club": 19,
        "Sacred Scourge": 12,
        # Magical staves: slower than ordinary staves (DCSS ~12).
        "Magic Staff": 12,
        "Staff of Earth": 12,
        "Staff of Flame": 12,
        "Staff of Frost": 12,
        "Staff of Venom": 12,
        "Staff of Lightning": 12,
        # Artefacts / uniques get tuned individually.
        "Sword of Zot": 11,
        "Demon Blade": 13,
        "Eudemon Blade": 13,
    }
    if name in overrides:
        return overrides[name]
    skill = _WEAPON_SKILL_MAP.get(name)
    return _SKILL_DEFAULT_DELAY.get(skill, 10)


def default_min_delay(delay: int) -> int:
    """DCSS minimum delay: max(0.7, delay/2). In our integer energy units."""
    return max(3, delay // 2)


class Skill:
    MAX_LEVEL = 27.0

    def __init__(self, name: str, aptitude: int = 0):
        self.name = name
        self.level = 0.0
        self.aptitude = aptitude
        self.state = SkillState.DISABLED
        self.target = None

    def cost_for_next(self) -> float:
        multiplier = 2.0 ** (-self.aptitude / 4.0)
        return 2.0 * (self.level + 1.0) ** 1.5 * multiplier

    def add_xp(self, amount: float) -> bool:
        if self.level >= self.MAX_LEVEL:
            return False
        if amount <= 0:
            return False
        cost = self.cost_for_next()
        gain = amount / cost
        old_level = self.level
        self.level = min(self.MAX_LEVEL, self.level + gain)
        if self.target is not None and self.level >= self.target:
            self.level = self.target
            self.state = SkillState.DISABLED
        self.level = round(self.level, 3)
        return self.level != old_level


class SkillSet:
    def __init__(self, skill_names: list[str], aptitudes: dict[str, int], cross_training: dict[str, list[str]]):
        self.skills = {name: Skill(name, aptitudes.get(name, 0)) for name in skill_names}
        self.cross_training = cross_training
        self.manual_mode = False
        self.recent_actions: list[str] = []
        self.recent_actions_max = 5

    def get(self, name: str) -> Skill | None:
        return self.skills.get(name)

    def get_level(self, name: str) -> float:
        skill = self.skills.get(name)
        return skill.level if skill else 0.0

    def record(self, skill_name: str) -> None:
        if skill_name in self.skills:
            self.recent_actions.append(skill_name)
            if len(self.recent_actions) > self.recent_actions_max:
                self.recent_actions.pop(0)

    def distribute(self, xp_amount: float) -> list[str]:
        leveled: list[str] = []

        if self.manual_mode:
            active = [s for s in self.skills.values() if s.state != SkillState.DISABLED]
        else:
            recent = set(self.recent_actions)
            active = [s for s in self.skills.values()
                      if s.name in recent or s.state != SkillState.DISABLED]
            if not active:
                fighting = self.skills.get("Fighting")
                if fighting:
                    active = [fighting]

        if not active:
            return leveled

        weights = []
        for skill in active:
            if skill.state == SkillState.FOCUSED:
                weights.append(2.0)
            else:
                weights.append(1.0)

        total_weight = sum(weights)
        if total_weight == 0:
            return leveled

        for skill, weight in zip(active, weights):
            share = xp_amount * weight / total_weight
            if skill.add_xp(share):
                leveled.append(skill.name)
            for partner_name in self.cross_training.get(skill.name, []):
                partner = self.skills.get(partner_name)
                if partner:
                    ct_share = share * 0.4
                    if partner.add_xp(ct_share):
                        if partner.name not in leveled:
                            leveled.append(partner.name)

        return leveled
