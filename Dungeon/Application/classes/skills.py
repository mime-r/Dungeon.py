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
    "Staff of Earth": "Staves",
    "Staff of Flame": "Staves",
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
