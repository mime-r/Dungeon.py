# Changelog

## 15/6/26 v2.3 — "The Terrain Update"

**Terrain & Scenery**
- 7 new terrain types: shallow water (`~`), deep water (`≈`), lava (`▒`), trees (`♣`), chasms (`░`), grass (`,`), mud (`;`) — each with distinct walkability, sight-blocking, and visual style
- 3 new floor features rendered on top of terrain: shrubs (`%`), mushrooms (`"`), rubble (`:`)
- Organic scenery pass runs on every floor: ponds grow inside large rooms with a 2-cell safety margin, trees scatter only in fully open room interiors, grass and mud patches blend with corridors, mushrooms and shrubs dot qualifying cells

**Dynamic Floor Biomes**
- Each floor generates a unique biome theme (AI-assisted) that shapes its enemy composition, loot, traps, terrain, and structures into a coherent setting — volcanic rift, ancient fungal depths, sacred shrine, and more
- 8 hand-crafted structure blueprints placed according to the floor's theme:

  | Structure | Effect |
  | --- | --- |
  | `shrine` | 4 diagonal wall pillars + altar at center |
  | `mushroom_grove` | Mud floor flooded with dense mushroom features |
  | `overgrown_room` | Grass flood, isolated trees, scattered shrubs |
  | `ruined_hall` | Pillar row across room center + rubble debris |
  | `frozen_pond` | Shallow-water ice pool with a rubble rim |
  | `campsite` | Grass patch, rubble campfire, shrub bedrolls |
  | `poison_marsh` | Mud/shallow-water mix with shrubs |
  | `standing_stones` | 8-pillar octagonal ring on a grass center |

- 2 special terrain feature overlays: `lava_pools` (impassable lava oval) and `chasms` (impassable void oval)
- Every biome combination produces a different dungeon feel without breaking navigation or connectivity

**Win Condition**
- Collect three sigil shards (`*`) hidden on depths 6, 7, and 8; the exit only unlocks when you carry all three
- Each shard is guarded by a depth-specific boss: Flame Guardian (depth 6), Stone Guardian (depth 7), Shadow Guardian (depth 8)
- Shard progress tracked in the sidebar (`Sigil: N/3 shards`)
- The dungeon awakens (all monsters wake) when the final shard is collected

## 15/6/26 v2.2 — "Depths & Disciplines"
- Character progression: choose a class (Fighter/Hunter/Acolyte/Wanderer); gain XP, levels, max HP and combat bonuses
- Status effects for player and monsters: poison, regeneration, might, haste, slow, confusion (with a small energy/speed scheduler)
- Ranged combat: bows, crossbow and sling with an on-map aiming cursor; some monsters fire back
- Traps: hidden dart / poison / teleport / alarm traps, revealed by searching
- Item identification: potions and scrolls start unidentified until used (their name is revealed the moment you use them); Scroll of Identification reveals one unknown item; starting kit and shop wares come pre-identified
- Autoexplore (`o`): auto-walk the floor until a monster appears
- Larger floors that average ~70×70 (up to 80×80) with a scrolling, player-centred map view, so you discover each level's true size by exploring
- Temples: pillared chambers that may appear on a floor, guarded but holding treasure and a healing altar
- New content: Potions of Might/Speed/Regeneration/Curing, ranged weapons, Giant Spider and Kobold Slinger
- UI polish: the HUD sizes itself to the window (header always visible); quaffing/reading returns you to the map at once

## 15/6/26 v2.1 — "Caverns & Crosscuts"
- Diagonal movement: player uses `y`/`u`/`b`/`n`; enemies chase with 8-direction pathfinding
- Variable map sizes per floor (50–75 wide, 22–32 tall) instead of a fixed box
- Three level generators randomly chosen per floor: rooms-and-corridors (with oval rooms), cellular automata caves, and BSP-structured layouts
- Expanded name generator: 73 first names, 40 surnames, 26 epithets (was 48/24/11)

## 15/6/26 v2.0 — "Stone Soup" overhaul
- Multi-floor descent with up/down stairs and a three-shard win condition (find all shards, escape)
- Rooms-and-corridors level generation with doors, secret doors and hidden vault rooms
- Rebuilt rich UI: map panel + hero sidebar (HP bar, depth, objective) + scrolling message log
- Bump-to-attack combat with persistent monsters that wake and chase you
- 11 depth-tiered enemy types and a boss; 10 weapons; scrolls; gold; more potions
- New NPC types: Blacksmith, Merchant and Healer alongside the Chemist
- Fixed the "John Doe" naming bug with a self-contained name generator
- Turn-based stdlib input (no more `keyboard`/admin/F11); dropped `pandas` and `names` deps
- Run scripts fixed (including case-correct Linux launch)

## 22/8/21 v1.2
- Linux compatibility (WSL not supported)
- Major code refactoring
- Ground item pickups
- Migrated UI to Rich library

## 30/7/21 v1.1.6
- Bugfixes for file reorganisation in v1.1.5

## 29/7/21 v1.1.5
- File and directory restructure; fixed import paths

## 29/7/21 v1.1
- Fixed crash when revisiting a tile after killing an enemy
- Various array and rendering fixes

## 28/7/21 v1.0
- Fixed game-breaking array error
