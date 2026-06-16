# Roadmap: Dungeon.py — Weapon Expansion & Hands System

## Overview

This milestone builds the weapon roster expansion as a horizontal-layer rollout: first the shared `hands` stat foundation that every other weapon depends on, then melee weapon categories (Maces & Flails, Long Blades, Polearms, Short Blades, Staves) added in a single batch since they're all independent JSON entries on top of the same model change, then the Ranged weapon category, and finally the new Throwing Weapons consumable item type — which closes out the milestone by validating that every new weapon (melee, ranged, and thrown) is reachable through existing acquisition paths and carries consistent flavor text.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [ ] **Phase 1: Hands Foundation** - Add the `hands` stat to the weapon model and assign it across all existing weapons
- [ ] **Phase 2: Melee Weapon Categories** - Add all missing Maces & Flails, Long Blades, Polearms, Short Blades, and Staves weapons
- [ ] **Phase 3: Ranged Weapons** - Add all missing Ranged category weapons
- [ ] **Phase 4: Throwing Weapons & Integration** - Introduce the new throwing-weapon consumable item type, populate it, and verify all new weapons (melee, ranged, thrown) are reachable in-game with consistent flavor text

## Phase Details

### Phase 1: Hands Foundation
**Goal**: Every weapon in the game (existing and future) carries a `hands` stat that follows a consistent one-handed vs. two-handed balance pattern, so later phases can add new weapons against a stable model.
**Depends on**: Nothing (first phase)
**Requirements**: HAND-01, HAND-02, HAND-03
**Success Criteria** (what must be TRUE):
  1. Every weapon loaded from `weapons.json` (existing and new) has a `hands` value of `One` or `Two`, visible/inspectable in-game (e.g. via inventory/equip screen)
  2. Comparing any two-handed weapon to a one-handed weapon of similar cost shows the two-handed weapon hits harder (`base_attack`/`attack_range`) and less accurately (`accuracy`)
  3. All pre-existing weapons (Club, Dagger, Rapier, Quarterstaff, Short Sword, Hand Axe, Scimitar, Mace, Flail, Spear, Trident, Morningstar, Falchion, Broad Axe, Long Sword, Halberd, Battleaxe, Glaive, War Axe, Great Mace, Executioner's Axe, the four ranged weapons, the five elemental staves, Sword of Zot, Fists) load and play exactly as before — only `hands` is added, no other stat changed
**Plans**: TBD

Plans:
- [ ] 01-01: Add `hands` field to `DungeonWeapon`/decoder and backfill all existing `weapons.json` entries with a sensible value

### Phase 2: Melee Weapon Categories
**Goal**: Players can find, buy, and fight with every missing Maces & Flails, Long Blades, Polearms, Short Blades, and Staves weapon, each fitting the existing cost-vs-stats balance curve and carrying its assigned `hands` value.
**Depends on**: Phase 1
**Requirements**: MACE-01, MACE-02, MACE-03, MACE-04, MACE-05, MACE-06, MACE-07, BLADE-01, BLADE-02, BLADE-03, BLADE-04, BLADE-05, POLE-01, POLE-02, POLE-03, POLE-04, SHORT-01, STAFF-01, STAFF-02
**Success Criteria** (what must be TRUE):
  1. A Dire flail, Giant club, and Giant spiked club (two-handed Maces & Flails) can each be equipped and dealt damage with in combat, hitting harder and less accurately than one-handed weapons of similar cost
  2. A Whip, Demon whip, Sacred scourge, and Eveningstar (one-handed Maces & Flails upgrades) can each be equipped and used in combat at a cost tier consistent with their power level
  3. A Demon blade, Eudemon blade, Double sword, Great sword, and Triple sword can each be equipped and used in combat, with the two-handed entries (Great sword, Triple sword) following the two-handed balance pattern
  4. A Demon trident, Trishula, Partisan, and Bardiche can each be equipped and used in combat, with Bardiche (two-handed) following the two-handed balance pattern
  5. A Quick blade and Lajatang can each be equipped and used in combat; if a generic "Magical staff" was added it behaves as a distinct, lower-tier alternative to the existing elemental "Staff of X" weapons
**Plans**: TBD

Plans:
- [ ] 02-01: Add Maces & Flails and Long Blades gap weapons to `weapons.json` with flavor text
- [ ] 02-02: Add Polearms, Short Blades, and Staves gap weapons to `weapons.json` with flavor text

### Phase 3: Ranged Weapons
**Goal**: Players can find, buy, and fire every missing Ranged category weapon, each fitting the existing cost-vs-stats balance curve and carrying its assigned `hands` value.
**Depends on**: Phase 1
**Requirements**: RANG-01, RANG-02, RANG-03, RANG-04
**Success Criteria** (what must be TRUE):
  1. An Orcbow and Arbalest (two-handed) can each be equipped and fired in ranged combat, trending toward lower accuracy/higher damage than existing one-handed ranged weapons
  2. A Hand cannon (one-handed, rare) can be equipped and fired with high damage and high accuracy at a cost tier consistent with its power level
  3. A Triple crossbow (two-handed, top-tier) can be equipped and fired as the highest-damage ranged weapon in the roster
**Plans**: TBD

Plans:
- [ ] 03-01: Add Ranged category gap weapons to `weapons.json` with flavor text

### Phase 4: Throwing Weapons & Integration
**Goal**: Players have a new stackable throwing-weapon item type usable from the existing ranged-attack flow without occupying the equip slot, and every weapon added this milestone (melee, ranged, and thrown) is reachable through existing acquisition paths with flavor text consistent with the existing style.
**Depends on**: Phase 2, Phase 3
**Requirements**: THROW-01, THROW-02, THROW-03, THROW-04, THROW-05, THROW-06, THROW-07, INT-01, INT-02
**Success Criteria** (what must be TRUE):
  1. Darts, Stones, Boomerangs, Javelins, and Large rocks can each be picked up, stack in inventory, and deplete by one on use
  2. A thrown dart (or any throwing weapon) can be aimed and fired through the existing ranged-attack flow without first being set as `player.equipped`
  3. Every new weapon added this milestone (Maces & Flails, Long Blades, Polearms, Ranged, Short Blades, Staves, and Throwing Weapons) appears in at least one of shop stock, vault treasure tables, or floor loot tables at a cost tier consistent with its power level
  4. Every new weapon added this milestone has `critical_hit`, `hit`, and `missed_hit` flavor text matching the existing weapon-text style
**Plans**: TBD

Plans:
- [ ] 04-01: Introduce stackable throwing-weapon item type and combat/inventory integration
- [ ] 04-02: Populate throwing weapons data and wire all new weapons (melee/ranged/thrown) into shop/vault/floor loot tables with flavor text

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 (Phases 2 and 3 may run in parallel — both depend only on Phase 1)

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Hands Foundation | 0/1 | Not started | - |
| 2. Melee Weapon Categories | 0/2 | Not started | - |
| 3. Ranged Weapons | 0/1 | Not started | - |
| 4. Throwing Weapons & Integration | 0/2 | Not started | - |
</content>
