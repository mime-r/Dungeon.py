# Changelog

## 23/6/26 v2.6 — "Scrolls, Brands & Hands"

**DCSS Scroll System (all 19 scrolls from DCSS)**
- New `scrolls.json` data file with rarity weights matching DCSS (Very Common 26%, Common 13%, Uncommon 5%, Rare 2%, Very Rare 1%)
- New effect handlers in `use_scroll`: identify, teleport, amnesia, blinking, butterflies, enchant_weapon, enchant_armour, fear, fog, immolation, noise, poison_cloud, revelation, silence, summoning, torment, vulnerability, brand_weapon, acquirement
- Scrolls are unidentified until read; reading reveals the true name; some scrolls (identify, amnesia, enchant, brand) preserve the scroll if you cancel
- "Reasonable action" check refuses scrolls when their effect would have no target (e.g., amnesia with no spells learned)
- New Scroll of Acquirement offers 3 random items tailored to your skills (or 500 gold) with a 1-of-3 picker UI

**DCSS Weapon Brand System (15 brands)**
- `BRAND_TABLE` per-brand specs with style/verb, damage roll, status effect, and `on_hit` callback
- Brands grouped into 4 tiers with per-floor availability:
  - **Tier 1 (F1-2):** Venom, Protection
  - **Tier 2 (F3-4):** + Flaming, Freezing, Electrocution
  - **Tier 3 (F5-6):** + Vampiric, Spectral, Heavy, Pain, Holy Wrath, Draining, Distortion
  - **Tier 4 (F7-8):** + Speed, Antimagic, Chaos (all 15)
- Brand callbacks for complex behaviours: Antimagic silences the target + drains MP, Chaos rolls a random effect, Distortion translocates/banishes, Vampiric heals, Protection grants +AC, Spectral summons a Spectral Weapon
- `apply_weapon_brand` fires during the attack roll, before status checks; `apply_weapon_on_hit` handles magical staves (existing)
- Heavy and Speed brands modify `effective_speed()`; Speed also adds accuracy_mod

**DCSS Armour Ego System (7 egos)**
- New `item_egos.py` with `ARMOUR_EGO_TABLE`, per-floor tier availability, `ego_chance`, `pick_armour_ego`, `apply_armour_ego`
- Egos: Stealth (cloak +EV), rF+/rC+ (body/cloak), Will+ (cloak/helmet), SInv (helmet, grants see_invisible), Archery (gloves/helmet, +% ranged dmg), Parrying (gloves, +SH)
- DungeonArmour fields: `ego`, `enchant`, `resistances`, `ev_bonus`, `sh_bonus`, `ranged_dmg_bonus`, `grant_see_invisible`
- Player aggregation: `aggregate_resistances()`, `ranged_damage_bonus()`, `has_see_invisible()`, `apply_resistance(damage_type, amount)` (r+ reduces damage by 33%)
- Player resistance wired into `_detonate_inner_flame` and `_tick_burning_terrain`
- See Invisible status and SInv helmet integrated into `update_fov`

**Unified Enchantment + Brand System**
- Natural enchantment rolls on every spawned weapon/armour using per-floor tier ranges (F1-2: 0-1, F3-4: 1-3, F5-6: 2-4, F7-8: 3-5)
- Vault bonus (+3 floor) gives 40% chance of +1; elite tag adds +2
- Scroll of Enchant Weapon/Armour capped at +9 (preserves the scroll on refusal)
- Enchantment grants +1 to-hit per +1 enchant (accuracy bonus wired into `attack()`)
- `display_name` now appends `+N` suffix to enchanted items
- Damage and accuracy in pack list stat line now include enchant
- Sacred Scourge: `dmg_pct_vs_holiness: {undead: 0.5, demonic: 0.25}` — now actually works

**Attack Delay System (DCSS-style)**
- `DungeonWeapon.delay` (base swing time) and `min_delay` (skill-floor); defaults by weapon name/skill
- Per-weapon DCSS-tuned delays: Dagger 8, Long Sword 14, Great Sword 17, Battleaxe 17, Hand Cannon 23, Triple Crossbow 25
- Magical staves slower (~12), Quarterstaff 11, Whips 8
- `DungeonPlayer.attack_cost()` returns energy cost; reduces by 1 per 2 skill levels, floored at min_delay
- `move()` and `fire()` return cost (int) instead of bool; `spend_turn(cost)` accepts the cost
- `handle()` returns cost; main loop calls `spend_turn(cost=cost)`
- Magical staves cannot be branded or enchanted (DCSS rule)

**Holiness System (Sacred Scourge / Holy Wrath)**
- Enemies tagged with `holiness`: "natural" (default), "undead" (Skeleton/Zombie/Wraith), "demonic" (Imp/Demon — new enemies)
- 2 new enemies: Imp (depth 3-6, demonic) and Demon (depth 5-8, demonic)
- `DungeonWeapon.dmg_pct_vs_holiness` (per-tag bonus); brand spec also supports this
- Holy Wrath brand: +75% damage vs undead and demonic (DCSS spec)
- Examine mode shows `(undead)` / `(demonic)` next to enemy names

**Spell System Updates**
- Spellcasting rebalanced: `BASE_FAILURE 52→30`, `DIFFICULTY_PER_LEVEL 10→8`, `INT_WEIGHT 2.0→3.0`
- Level 2 spells at Spellcasting 4: 20% → 4% failure (within the 5-10% target)
- Silence aura (Scroll of Silence) blocks both spellcasting and scroll reading
- Channeled spells: `_channel_targets` dict keyed by spell name, properly saved
- Visual cast animations: cast announcement + 0.12s pause + colored impact message
- Damage-type-keyed styles (fire/ice/lightning/poison/arcane) for all spells

**Background System Update**
- Each background gets its own `aptitudes` (moved from skills.json into backgrounds.json)
- `skill_defs.json` replaces `skills.json` (master skill list + cross-training)
- All backgrounds now start with exactly 1 L1 + 1 L2 relevant spell
- Background catalog is fully data-driven

**Floor Theme Fallback**
- `_FALLBACK_BIOMES` list of 10 hand-crafted biome tuples when LLM is disabled
- Each biome has name, description, water_density, structures, terrain_features
- `_fallback_theme()` picks a random biome with deeper floors biased toward wet biomes
- Used in `_new_level` whenever the LLM returns None

**Quality of Life**
- Save/load system extended (SAVE_VERSION bumped to 2): brand, enchant, ego, holiness, fog, silence, dmg_pct_vs_holiness all round-trip
- Sidebar compacted: HP/MP bars (12 chars), single-line weapon+AC, single-line pack, single-line sigil
- Examine cursor in `x` mode restricted to visible or previously-explored tiles
- Movement restricted to visible or previously-explored tiles
- Auto-explore filters dead enemies; clearer "halted: a X is in view" message
- Enchantment shows as `+N` suffix on identified items

**Bugfixes**
- Items that no longer exist in the DB (renamed scrolls) crash fixed: `_stock_item` now returns `None` and the caller filters
- Trader "no attribute cost" crash fixed: `Magical Staff` → `Magic Staff` typo, `Scroll of Magic Mapping` → `Scroll of Revelation` rename
- `_read_save_state` returns None for v1 saves (graceful no-save)
- `effective_speed` now considers the equipped weapon's brand (Speed/Heavy)
- `is_summon` correctly applied to Spectral Weapon and Butterfly entities

## 22/6/26 v2.5 — "Save & Restore"

**Save/Restore System**
- New `S` key saves game state to `savegame.json` (player, inventory, equipment, all levels, enemies, NPCs, floor themes)
- Splash screen detects existing save and offers `R` to resume with depth/HP/shards summary
- Full round-trip serialization: player stats, inventory, armour, equipped weapon, status effects, skills, spells, known items, auto-pickup config
- Per-level persistence: terrain, items, enemies, summons, NPCs with full state (HP, position, status effects, trader stock)
- Controls HUD updated — `S` save shown, "restart to restore" hint displayed
- Bugfix: `burning` tile style no longer overwrites wall color (orange `#` fix)
- Bugfix: NPC `symbol`/`style` attributes defaulted in base class so restore doesn't crash on traders/healers

## 16/6/26 v2.4 — "The Magic Expansion"

**Spellcasting Rework**
- Magic staff now boosts all spell schools via Spellcasting skill
- `_MAGIC_SCHOOLS` expanded with generic "Spellcasting" school for Magic Staff
- Staff damage multiplier now uses Spellcasting level for all spells
- Staff Boosted label in spell menu for generic staves

**New Spells (8)**
- Ice Shard (lvl 2, Ice Magic) — projectile + slow
- Static Touch (lvl 2, Conjuration) — touch + confusion
- Stone Fist (lvl 2, Earth Magic) — projectile
- Venom Bolt (lvl 3, Poison Magic) — projectile + poison
- Phase Shift (lvl 3, Translocation) — self-teleport
- Summon Spectral Wolf (lvl 4, Summoning) — summon wolf ally
- Blizzard (lvl 5, Ice Magic) — expanding AoE + slow
- Chain Lightning (lvl 7, Conjuration) — explosion
- All spells have unique cast_text flavour displayed on cast

**New Spellbooks (3)**
- Book of Ice, Book of Venom, Book of the Storm
- Existing books updated: Book of Summoning, Book of Fire, Book of Earth, Book of Power

**New Backgrounds (6)**
- Frostbringer (Ice Magic), Venomancer (Poison Magic), Stormcaller (Air/Lightning)
- Arcanist (Translocation), Shadowblade (Phase Shift), Crusader (no MP, all combat)
- Background selection paginated (9 per page) with description column replacing starting kit
- Inspect screen now shows starting spells
- ESC in class selection prompts exit instead of auto-picking Wanderer

**Quality of Life**
- Gold auto-pickup toggleable in `\` menu (default ON)
- Sidebar objective text removed for zero-shard state (help screen covers it)
- AoE spells now apply status effects via `_expanding_aoe` / `_explosion`

**Bugfixes**
- Wolf enemy added for Spectral Wolf summon
- Class selection pagination correctly maps page-local numbers to global indices
- Fixed Rich markup collision in exit prompt

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
