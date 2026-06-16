# Requirements: Dungeon.py — Weapon Expansion & Hands System

**Defined:** 2026-06-16
**Core Value:** Every weapon a player can find or buy feels distinct and balanced against the rest of the roster — new additions slot into the existing power curve without breaking it, and two-handed weapons read as a meaningfully different playstyle from one-handed weapons.

## v1 Requirements

### Hands System (foundation — other categories depend on this)

- [ ] **HAND-01**: Every `DungeonWeapon` has a `hands` stat (`One` or `Two`)
- [ ] **HAND-02**: Two-handed weapons follow a consistent balance pattern relative to one-handed weapons of similar cost — higher `base_attack`/`attack_range`, lower `accuracy`
- [ ] **HAND-03**: All existing weapons (Club, Dagger, Rapier, Quarterstaff, Short Sword, Hand Axe, Scimitar, Mace, Flail, Spear, Trident, Morningstar, Falchion, Broad Axe, Long Sword, Halberd, Battleaxe, Glaive, War Axe, Great Mace, Executioner's Axe, the four ranged weapons, the five elemental staves, Sword of Zot, Fists) are assigned a sensible `hands` value with no other stat changes

### Maces & Flails

- [ ] **MACE-01**: Add Whip (light, fast, low damage one-handed)
- [ ] **MACE-02**: Add Demon whip (upgraded Whip — rare/late-game tier)
- [ ] **MACE-03**: Add Sacred scourge (one-handed, mid-high tier)
- [ ] **MACE-04**: Add Dire flail (two-handed)
- [ ] **MACE-05**: Add Eveningstar (one-handed, upgraded Morningstar tier)
- [ ] **MACE-06**: Add Giant club (two-handed, heavy/slow archetype)
- [ ] **MACE-07**: Add Giant spiked club (two-handed, top-tier heavy)

### Long Blades

- [ ] **BLADE-01**: Add Demon blade (one-handed, upgraded tier)
- [ ] **BLADE-02**: Add Eudemon blade (one-handed, upgraded tier)
- [ ] **BLADE-03**: Add Double sword (one-handed, fast dual-edge)
- [ ] **BLADE-04**: Add Great sword (two-handed)
- [ ] **BLADE-05**: Add Triple sword (two-handed, top-tier)

### Polearms

- [ ] **POLE-01**: Add Demon trident (one-handed, upgraded Trident tier)
- [ ] **POLE-02**: Add Trishula (one-handed, upgraded tier)
- [ ] **POLE-03**: Add Partisan (one-handed, high accuracy reach weapon)
- [ ] **POLE-04**: Add Bardiche (two-handed, top-tier reach weapon)

### Ranged

- [ ] **RANG-01**: Add Orcbow (two-handed bow, low accuracy/high damage)
- [ ] **RANG-02**: Add Arbalest (two-handed crossbow, heavy)
- [ ] **RANG-03**: Add Hand cannon (one-handed, high damage/high accuracy, rare)
- [ ] **RANG-04**: Add Triple crossbow (two-handed, top-tier)

### Short Blades

- [ ] **SHORT-01**: Add Quick blade (one-handed, fastest/lowest-damage short blade, double-strike flavor preserved narratively if not mechanically)

### Staves

- [ ] **STAFF-01**: Add Lajatang (two-handed double-bladed staff)
- [ ] **STAFF-02**: Evaluate whether a generic "Magical staff" (DCSS base staff) adds value distinct from the existing five elemental "Staff of X" weapons; add only if it fills a real gap (e.g., a cheap entry-level staff with no on-hit effect)

### Throwing Weapons

- [ ] **THROW-01**: Introduce a new consumable, stackable throwing-weapon item type, distinct from the equipped-weapon slot
- [ ] **THROW-02**: Add Dart (cheap, common, low damage)
- [ ] **THROW-03**: Add Stone (cheapest, minimal damage)
- [ ] **THROW-04**: Add Boomerang (returns/reusable flavor, mid damage)
- [ ] **THROW-05**: Add Javelin (high damage, requires Medium+ analog or just higher cost tier)
- [ ] **THROW-06**: Add Large rock (highest damage, heaviest, rarest)
- [ ] **THROW-07**: Thrown weapons are usable from the existing ranged-attack flow (aim/fire) without requiring the player to have them equipped as their `player.equipped` weapon

### Integration

- [ ] **INT-01**: All new weapons are reachable in-game through existing acquisition paths (shop, vault treasure tables, floor loot tables) at a cost tier consistent with their power level
- [ ] **INT-02**: All new weapons have flavor text (`critical_hit`, `hit`, `missed_hit`) consistent with the existing weapon-text style

## v2 Requirements

(None — full scope targeted for v1 of this milestone)

## Out of Scope

| Feature | Reason |
|---------|--------|
| Rebalancing existing 12 weapons (Club, Mace, Flail, Morningstar, Spear, Trident, Falchion, Long Sword, Scimitar, Halberd, Glaive, Quarterstaff, Great Mace) to match DCSS numbers exactly | User chose to preserve current in-game balance; only gaps are filled |
| Variable per-weapon attack delay / energy cost | Turn engine (`main.py`) stays flat-cost; no DCSS "Delay"/"Min delay" porting |
| Shields, off-hand items, dual-wielding | No new equip slot introduced; `hands` only affects damage/accuracy stats |
| Size requirements (Small/Medium/Large) | No size stat exists on player or items; not introduced |
| Skill-gated minimum delay | No skill stat exists; not introduced |
| "Cuts Hydras" mechanic | No hydra-type enemy exists in this game |
| Throwing net's "Special" mulch mechanic | Deferred unless it maps cleanly onto the new consumable item type during planning |

## Traceability

Filled in during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| HAND-01 | TBD | Pending |
| HAND-02 | TBD | Pending |
| HAND-03 | TBD | Pending |
| MACE-01..07 | TBD | Pending |
| BLADE-01..05 | TBD | Pending |
| POLE-01..04 | TBD | Pending |
| RANG-01..04 | TBD | Pending |
| SHORT-01 | TBD | Pending |
| STAFF-01..02 | TBD | Pending |
| THROW-01..07 | TBD | Pending |
| INT-01..02 | TBD | Pending |

**Coverage:**
- v1 requirements: 36 total
- Mapped to phases: 0 (pending roadmap)
- Unmapped: 36 ⚠️

---
*Requirements defined: 2026-06-16*
*Last updated: 2026-06-16 after initial definition*
