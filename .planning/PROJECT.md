# Dungeon.py — Weapon Expansion & Hands System

## What This Is

Dungeon.py is a terminal-based, single-player roguelike (Python + Rich, turn-based, energy-scheduled) with procedurally generated floors, an optional LLM-flavored content layer, and a TinyDB leaderboard. This milestone expands the weapon roster to cover all standard DCSS-style weapon categories (Maces & Flails, Long Blades, Polearms, Ranged, Short Blades, Staves, Throwing Weapons) and introduces a "hands" (one-handed/two-handed) stat that fits into the existing balance model.

## Core Value

Every weapon a player can find or buy feels distinct and balanced against the rest of the roster — new additions slot into the existing power curve (cost vs. base_attack/attack_range/accuracy) without breaking it, and two-handed weapons read as a meaningfully different playstyle (harder-hitting, less accurate) from one-handed weapons.

## Requirements

### Validated

- ✓ Data-driven weapon definitions loaded from `Dungeon/data/weapons.json` via `DungeonJSONDecoder` — existing
- ✓ Single equipped-weapon slot (`player.equipped`) with melee/ranged combat resolution in `main.py` — existing
- ✓ Weapon balance model: `cost`, `base_attack`, `attack_range` (damage roll), `accuracy`, optional `on_hit` status effect — existing
- ✓ Flat per-action energy cost (`TURN = 10`) regardless of weapon — existing, unchanged by this milestone
- ✓ Item base classes (`DungeonItem`, `DungeonWeapon`, stackable potions/scrolls patterns) — existing

### Active

- [ ] Add all missing weapons from the Maces & Flails category (Whip, Demon whip, Sacred scourge, Dire flail, Eveningstar, Giant club, Giant spiked club)
- [ ] Add all missing weapons from the Long Blades category (Demon blade, Eudemon blade, Double sword, Triple sword)
- [ ] Add all missing weapons from the Polearms category (Trishula, Partisan, Bardiche)
- [ ] Add all missing weapons from the Ranged category (Orcbow, Arbalest, Hand cannon, Triple crossbow)
- [ ] Add all missing weapons from the Short Blades category (Quick blade)
- [ ] Add all missing weapons from the Staves category (Magical staff variant distinct from existing "Staff of X" elemental staves, Lajatang)
- [ ] Add a `hands` stat (One/Two) to the weapon model, fit to the existing balance pattern: two-handed weapons trend toward higher `base_attack`/`attack_range` and lower `accuracy` than one-handed weapons of similar cost
- [ ] Apply the `hands` stat to all new weapons; existing weapons keep their current stats unchanged but get a sensible `hands` value assigned
- [ ] Add throwing weapons (Dart, Stone, Boomerang, Javelin, Large rock; Throwing net deferred if mechanically inapplicable) as a new consumable, stackable item type distinct from the equipped-weapon slot
- [ ] All new weapons are reachable in-game through existing acquisition paths (shop/vault/floor loot) consistent with their cost tier

### Out of Scope

- Rebalancing/renaming existing weapons (Mace, Flail, Morningstar, Spear, Trident, Falchion, Long Sword, Scimitar, Halberd, Glaive, Quarterstaff) to match DCSS stats exactly — keeping current in-game balance, only filling gaps
- Variable per-weapon attack speed / energy cost (DCSS "Delay"/"Min delay") — turn cost stays flat; no changes to the energy scheduler in `main.py`
- Shields, off-hand items, or dual-wielding — no new equip slot is introduced
- Size requirements, skill-gated minimum delay, and "cuts hydras" — these DCSS mechanics have no equivalent system in this game (no size stat, no skill stat, no hydra-type enemy) and are not being introduced
- Throwing net's special "Special" mulch mechanic, if it doesn't map cleanly onto the new consumable throwing-weapon model

## Context

- Brownfield codebase; mapped previously via `/gsd-map-codebase` (`.planning/codebase/`).
- Weapon data lives in `Dungeon/data/weapons.json`, decoded by `Dungeon/Application/classes/decoder.py` into `DungeonWeapon` instances (`Dungeon/Application/classes/items.py`) carrying `DungeonWeaponTexts` (`Dungeon/Application/classes/weapons.py`).
- Combat resolution (accuracy roll, damage roll, on-hit effects) lives in `Dungeon/Application/main.py` (~lines 933-950 for melee, ~875 for ranged fire).
- No automated test suite exists in the repo (per `.planning/codebase/CONCERNS.md`) — verification for this milestone will rely on manual playtesting/data inspection rather than unit tests, unless the user requests tests be added.
- The DCSS reference tables include several mechanics (Delay/Min delay tied to skill, Size requirements, Cuts Hydras) that don't correspond to anything in this codebase; these are explicitly excluded rather than partially ported.

## Constraints

- **Existing balance**: New weapons must fit the established cost-vs-stats curve so they don't trivially outclass or get outclassed by neighboring-cost weapons — Why: avoids breaking shop/loot economy and difficulty curve.
- **No new equip slots**: Implementation must work within the current single `player.equipped` weapon slot plus a new stackable throwing-weapon inventory category — Why: avoids a larger refactor of the equip/inventory system, which is out of scope for this milestone.
- **Data-driven**: New weapons should be added as JSON entries in `Dungeon/data/weapons.json` (and a new throwing-weapons data file/category if needed), consistent with the existing data-driven content pattern — Why: matches established convention; no code changes needed to add future content of the same type.

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Keep existing weapons' stats unchanged; only add missing ones | User chose to preserve current in-game balance rather than re-derive 11 existing weapons from DCSS numbers | — Pending |
| "Hands" system affects damage/accuracy/range only, not turn cost or equip slots | User chose the smallest-scope option; the energy scheduler currently charges a flat cost per action regardless of weapon, and adding shields/off-hand items would be a much larger change | — Pending |
| Throwing weapons become a new consumable stackable item type | User chose this over skipping throwables or treating them as infinite-ammo ranged weapons, to preserve the DCSS "mulch" flavor (limited-use ammo) without copying the exact mulch-percentage mechanic | — Pending |
| DCSS Size/Skill/Hydra mechanics excluded entirely | No equivalent stat (size, skill) or enemy type (hydra) exists in this codebase; partially porting them would add unused complexity | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-06-16 after initialization*
