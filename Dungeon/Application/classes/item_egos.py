"""DCSS-style item ego generation: weapon brands and armour egos by floor tier.

Tier 1 (Floors 1-2):  Venom, Protection
Tier 2 (Floors 3-4):  + Flaming, Freezing, Electrocution
Tier 3 (Floors 5-6):  + Vampiric, Spectral, Heavy, Pain, Holy Wrath, Draining, Distortion
Tier 4 (Floors 7-8):  + Speed, Antimagic, Chaos (all brands available)

Armour egos use a parallel tier system. Vault floors get a +3 depth bonus to
their generation rolls (per the user's DCSS notes).
"""
import random
import copy
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .items import DungeonWeapon, DungeonArmour


# --- Brand tier tables -----------------------------------------------------

# Maps brand name -> DCSS tier (1 = earliest, 4 = latest).
BRAND_TIER: dict[str, int] = {
    # Tier 1
    "venom": 1,
    "protection": 1,
    # Tier 2
    "flaming": 2,
    "freezing": 2,
    "electrocution": 2,
    # Tier 3
    "vampiric": 3,
    "spectral": 3,
    "heavy": 3,
    "pain": 3,
    "holy_wrath": 3,
    "draining": 3,
    "distortion": 3,
    # Tier 4
    "speed": 4,
    "antimagic": 4,
    "chaos": 4,
}

# Per-tier weights for the brand pool at that depth. DCSS biases the common
# brands heavily; the rarer ones are diluted in lower tiers.
_TIER_BRAND_WEIGHTS: dict[int, dict[str, int]] = {
    1: {"venom": 80, "protection": 20},
    2: {"flaming": 30, "freezing": 30, "electrocution": 25, "venom": 10, "protection": 5},
    3: {"vampiric": 25, "spectral": 20, "heavy": 15, "pain": 10, "holy_wrath": 8,
        "draining": 7, "distortion": 5, "flaming": 3, "freezing": 3,
        "electrocution": 2, "venom": 1, "protection": 1},
    # Tier 4: all 15 brands, uniform.
    4: {b: 1 for b in BRAND_TIER.keys()},
}


def _tier_for_floor(floor: int, vault_bonus: int = 0) -> int:
    """Determine the brand tier for a given floor depth (and optional vault bonus)."""
    effective = floor + vault_bonus
    if effective <= 2:
        return 1
    if effective <= 4:
        return 2
    if effective <= 6:
        return 3
    return 4


def _available_brands_for_tier(tier: int) -> list[str]:
    return [b for b, t in BRAND_TIER.items() if t <= tier]


# --- Armour ego tier tables ------------------------------------------------

ARMOUR_EGO_TIER: dict[str, int] = {
    # Tier 1
    "stealth": 1,
    # Tier 2
    "res_fire": 2,
    "res_cold": 2,
    # Tier 3
    "will": 3,
    "see_invisible": 3,
    "archery": 3,
    # Tier 4
    "parrying": 4,
}

ARMOUR_EGO_TABLE: dict[str, dict] = {
    "stealth": {
        "label": "Stealth",
        "ev_bonus": 5,
        "valid_slots": {"cloak"},
    },
    "res_fire": {
        "label": "rF+",
        "resistances": {"fire": 1},
        "valid_slots": {"body", "cloak"},
    },
    "res_cold": {
        "label": "rC+",
        "resistances": {"cold": 1},
        "valid_slots": {"body", "cloak"},
    },
    "see_invisible": {
        "label": "SInv",
        "grant_see_invisible": True,
        "valid_slots": {"helmet"},
    },
    "will": {
        "label": "Will+",
        "resistances": {"will": 1},
        "valid_slots": {"cloak", "helmet"},
    },
    "parrying": {
        "label": "Parrying",
        "sh_bonus": 3,
        "valid_slots": {"gloves"},
    },
    "archery": {
        "label": "Archery",
        "ranged_dmg_bonus": 0.2,
        "valid_slots": {"gloves", "helmet"},
    },
}

_TIER_ARMOUR_EGO_WEIGHTS: dict[int, dict[str, int]] = {
    1: {"stealth": 1},
    2: {"stealth": 1, "res_fire": 1, "res_cold": 1},
    3: {"stealth": 1, "res_fire": 1, "res_cold": 1, "will": 1, "see_invisible": 1, "archery": 1},
    # Tier 4: all egos.
    4: {e: 1 for e in ARMOUR_EGO_TIER.keys()},
}


def _available_armour_egos_for_tier(tier: int, slot: str) -> list[str]:
    return [
        e for e, t in ARMOUR_EGO_TIER.items()
        if t <= tier and slot in ARMOUR_EGO_TABLE[e]["valid_slots"]
    ]


# --- Ego chance formula ----------------------------------------------------

def ego_chance(floor: int, vault_bonus: int = 0) -> float:
    """Probability (0-1) that a randomly spawned item has a brand/ego.

    Approximates the DCSS formula (Floor x 2.5) + base item modifier.
    Capped at 95 % so we never guarantee an ego.
    """
    return min(0.95, max(0.0, (floor + vault_bonus) * 0.025))


# --- Natural enchantment (per the unified damage formula) -------------------

# Per-tier enchantment range for items natively generated on a given floor.
# Tier 1 (F1-2): +0 to +1  Tier 2 (F3-4): +1 to +3
# Tier 3 (F5-6): +2 to +4  Tier 4 (F7-8): +3 to +5
_ENCHANT_RANGES: dict[int, tuple[int, int]] = {
    1: (0, 1),
    2: (1, 3),
    3: (2, 4),
    4: (3, 5),
}
_ENCHANT_CAP = 9  # scroll enchantment / spawn cap (DCSS spec)


def roll_natural_enchantment(floor: int, vault_bonus: int = 0, elite: bool = False) -> int:
    """Roll a natural +N enchantment level for an item spawned at the given depth.

    Vault and elite modifiers add a small chance of +1/+2 to the roll. Capped at +9.
    """
    tier = _tier_for_floor(floor, vault_bonus)
    lo, hi = _ENCHANT_RANGES[tier]
    base = random.randint(lo, hi)
    # Vault bonus: 40 % chance to nudge +1
    if vault_bonus and random.random() < 0.4:
        base = min(_ENCHANT_CAP, base + 1)
    # Elite / boss drop: flat +2
    if elite:
        base = min(_ENCHANT_CAP, base + 2)
    return base


# --- Picker functions ------------------------------------------------------

def pick_brand(floor: int, vault_bonus: int = 0) -> str | None:
    """Roll for a brand at the given depth. Returns None if no brand triggers."""
    if random.random() >= ego_chance(floor, vault_bonus):
        return None
    tier = _tier_for_floor(floor, vault_bonus)
    weights = _TIER_BRAND_WEIGHTS[tier]
    pool = list(weights.keys())
    w = [weights[b] for b in pool]
    return random.choices(pool, weights=w, k=1)[0]


def pick_armour_ego(floor: int, slot: str, vault_bonus: int = 0) -> str | None:
    """Roll for an armour ego. Returns None if no ego triggers or none fit the slot."""
    if random.random() >= ego_chance(floor, vault_bonus):
        return None
    tier = _tier_for_floor(floor, vault_bonus)
    pool = _available_armour_egos_for_tier(tier, slot)
    if not pool:
        return None
    weights = _TIER_ARMOUR_EGO_WEIGHTS[tier]
    w = [weights[e] for e in pool]
    return random.choices(pool, weights=w, k=1)[0]


# --- Apply helpers --------------------------------------------------------

def apply_brand(weapon: "DungeonWeapon", brand_name: str) -> None:
    """Mutate a weapon instance to have the given brand."""
    weapon.brand = brand_name


def apply_armour_ego(armour: "DungeonArmour", ego_name: str) -> None:
    """Mutate an armour instance to have the given ego and its bonuses."""
    spec = ARMOUR_EGO_TABLE.get(ego_name)
    if not spec:
        return
    armour.ego = ego_name
    armour.ev_bonus = max(armour.ev_bonus, spec.get("ev_bonus", 0))
    armour.sh_bonus = max(armour.sh_bonus, spec.get("sh_bonus", 0))
    armour.ranged_dmg_bonus = max(armour.ranged_dmg_bonus, spec.get("ranged_dmg_bonus", 0.0))
    armour.grant_see_invisible = armour.grant_see_invisible or spec.get("grant_see_invisible", False)
    for dmg_type, level in spec.get("resistances", {}).items():
        armour.resistances[dmg_type] = max(armour.resistances.get(dmg_type, 0), level)


# --- Public-facing generation (used by _populate) -------------------------

def maybe_brand_weapon(weapon: "DungeonWeapon", floor: int, vault_bonus: int = 0,
                       elite: bool = False) -> bool:
    """Roll for a brand on a freshly spawned weapon. Mutates the weapon.
    Always rolls a natural enchantment level (independent of brand chance).
    Returns True if a brand was applied."""
    weapon.enchant = max(weapon.enchant, roll_natural_enchantment(floor, vault_bonus, elite))
    brand = pick_brand(floor, vault_bonus)
    if brand is None:
        return False
    apply_brand(weapon, brand)
    return True


def maybe_ego_armour(armour: "DungeonArmour", floor: int, vault_bonus: int = 0,
                      elite: bool = False) -> bool:
    """Roll for an ego on a freshly spawned armour piece. Mutates the armour.
    Always rolls a natural enchantment level (independent of ego chance).
    Returns True if an ego was applied."""
    armour.enchant = max(armour.enchant, roll_natural_enchantment(floor, vault_bonus, elite))
    ego = pick_armour_ego(floor, armour.slot, vault_bonus)
    if ego is None:
        return False
    apply_armour_ego(armour, ego)
    return True
