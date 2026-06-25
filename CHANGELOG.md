# Changelog

## 26/6/26 v2.7.1 — "Polish & Theme"

**Themed Enemy Picker**
- New `FLOOR_THEMES` data structure (8 floors × curated flavor pool + tier mix) so each floor spawns a thematically consistent mob mix instead of a uniform random sample
  - Floor 1 "Surface Lair" — vermin, small reptiles, fungi (70% weak / 30% mid)
  - Floor 2 "Early Dungeon" — goblinoids, hounds, imps (40/50/10)
  - Floor 3 "Winding Depths" — snakes, ogres, wraiths (10/60/30)
  - Floor 4 "Deep Halls" — manticores, nagas, liches (0/50/50)
  - Floor 5 "Lair of Drakes" — drakes, bears, basilisks (0/30/70)
  - Floor 6 "Murk & Brine" — nagas, jellies, oklob plants (0/20/80)
  - Floor 7 "Vaults of Hell" — dragons, demonspawn, brimstone fiends (0/10/90)
  - Floor 8 "Pandemonium" — hellbinders, eldritch, ancient horrors (0/0/100)
- New `_pick_themed_enemy(depth, theme)` method on `Dungeon`:
  - LLM `theme.enemy_bias` (up to 5 names) takes priority as a full-weight override
  - Otherwise rolls a tier from the floor's `tier_mix`, then picks 70% from the flavor pool and 30% from the full depth pool (both filtered by the chosen tier)
  - Falls back gracefully if the flavor pool has no candidates in the chosen tier
- LLM `enemy_bias` validation now accepts any mob name valid at the current depth (was hardcoded to 12 names); prompt updated to reflect this and the new 0-5 cap
- Bosses and `spawn_weight=0` mobs are skipped by the picker; boss-tier is reserved for the 3 guardians

**Floor Introduction**
- `enter_level` prints the floor's name and description in the message log on first entry (e.g. "Depth 6 — Murk & Brine. A flooded swamp of jellies, nagas, and slithering vines."), using the LLM-generated theme or the `FLOOR_THEMES` fallback

**Item Spawn Display**
- Weapons and armour now print a one-line announcement in the message log when they spawn with a brand or ego, showing enchantment + label + effect description
  - Example: `[flavor]depth 3:[/flavor] +1 Sling (Flaming) — scorches for 2-5 dmg (50%)`
  - Example: `[action]Vault:[/action] +4 Battleaxe (Heavy) — crushes for 3-6 dmg (60%); -3 swing speed; +60% base dmg`
- New helpers in `item_egos.py`: `describe_brand()` produces a one-line effect text for any of the 15 brands (e.g. "summons a Spectral Weapon on hit", "+75% vs undead/demonic"); `describe_ego()` for any of the 7 egos (e.g. "rF+ (33% fire res)", "+20% ranged dmg"); `announce_spawn()` composes the full line
- Items with no enchant, no brand, and no ego stay quiet (most early-floor drops)
- Vault prefix `[action]Vault:[/action]` for items placed in vault rooms

**Inventory Polish**
- Equipped items are always shown as the first entries on every page, even before any sorting (preserves their relative order)
- New `s` key in the pack screen triggers `_sort_inventory()` which reorders the underlying list by: equipped → weapon → armour → throwable → spellbook → potion → scroll → inventory bag → shard, then by name, then by enchantment (descending)
- Pages now show a `-- equipped --` / `-- pack --` sub-header when the page straddles the boundary
- Page-local selection (`1-9`) maps back to the real `player.inventory` index so drop/equip/unequip work unchanged
- Footer updated: `[1-9] select item  [s] auto-sort  [,] prev  [.] next  [esc] exit`

**Splash Screen**
- Multi-colour ASCII banner (red→orange→yellow→cyan→purple)
- Version display (`v2.7.0`) and tagline ("A turn-based roguelike in the spirit of Dungeon Crawl Stone Soup")
- 5 feature bullets highlighting the new content (531 monsters, casters, breaths, etc.)
- New `g` key opens the project on GitHub via `webbrowser.open(_GITHUB_URL, new=2, autoraise=True)`; re-renders the splash after the browser steals focus
- Tip line with one-liner gameplay hint
- `_GITHUB_URL` constant at the top of `wrapper.py` — easy to change

**Spawn Count**
- `enemies_base` 4 → 6, `enemies_per_depth` stays at 1
- Per floor: 6, 7, 8, 9, 10, 11, 12, 13 (76 total per run, +27% from the original 60)
- The thematic picker keeps the floor feel coherent despite the higher count

## 25/6/26 v2.7 — "The Menagerie"

**The Mob Expansion — 531 monsters (was 20)**
- Data-driven roster: 511 new general mobs (non-uniques) added to `enemies.json`, all derived from the DCSS bestiary reference
- Per-mob depth band, tier, and spawn weight tuned so each of the 8 floors feels distinct
- Floor 1 (surface): rats, bats, quokkas, small lizards, early vermin
- Floor 2-3 (entry): orcs, gnolls, hounds, wraiths, imps, nagas, first casters
- Floor 4-5 (mid): deep trolls, drakes, liches, deep elves, spriggans, demonspawn, beholders
- Floor 6 (swamp/snakes): nagas, anacondas, slime creatures, jellies, oklob plants, merfolk
- Floor 7-8 (vaults/hell): dragons, liches, brimstone/ice fiends, pandemonium lords, eldritch horrors

**New Status Effects (8)**
- `paralysis` — target skips turns (sea snake, basilisk, orb spider, scorpion)
- `blind` — accuracy penalty, expires (sun moth, spark wasp, glass eye, screaming refraction)
- `bleed` — DoT, scales with mobility (warg, tyrant leech, warcries)
- `drain_max_hp` — vampires, vampire mosquitoes, ancient liches
- `drain_mp` — mana vipers, ghosts, mummy priests, soul eaters
- `constricted` — player can't walk (snakes, nagas, kraken tentacles, oni incarcerators)
- `invisible` — render as `?` unless player has see-invisible (shadows, phantasmal warriors, will-o-wisps, drudes)
- `corrosion` — slowly degrades armour (yellow draconians, jellies, obsidian bats, caustic shrikes)

**New Enemy Mechanics (data-driven, backwards-compatible)**
- **Constriction**: snake/naga/kraken mobs grab the target; player can't move but can bump-attack; mob damages the held target each turn
- **Invisibility**: invisible mobs don't appear on the map unless the player has see-invisible; mobs can't target the player when invisible
- **Flight / Swimming / Amphibious**: passable terrain expanded for these mobs (dragons, harpies, kraken, frogs, electric eels)
- **Death FX — Explosion**: AoE damage at the death tile (bombardier beetle, ball lightning, hellfire mortar, monarch bomb)
- **Death FX — Spore Cloud**: lingering area effect + immediate status (toadstool, deathcap, caustic sporangium, wandering mushroom)
- **Death FX — Split**: spawn smaller copies on death (jellies, endoplasm, slimes, pharaoh ants)
- **Death FX — Shriek**: wake every monster on the floor one-shot (killer bee, queen bee, wailing wraith, doom howl, laughing skull, howler monkey)
- **Death FX — Ally Buff**: buff nearby allies on death (Pikel haste, orc warlord might, wendigo haste)
- **Death FX — Demon Spawn**: boss-tier mobs summon demon allies on death (Pandemonium Lord → Cacodemon/Hellwing, Cerebov → Balrug/Hellion, Asmodeus → Brimstone Fiend, Tiamat → 3 dragons)
- **Death FX — Minion Spawn**: spawn a specific minion (Pikel → Pikel Minion, Pargi → splits into two)

**Spellcasting AI (113 casters)**
- New enemy infrastructure: `spells: list[str]` and `spell_chance: float` per mob
- `pick_spell()` weighted random pick (off-cooldown): damage/control spells weighted 2.0, summons 1.5 if below cap, self_teleport 0 above 50% HP and 4.0 below (flee behaviour)
- Per-spell cooldowns: 2 + min(5, level-1) turns
- All 9 spell effect types implemented for enemies: projectile, touch, expanding_aoe, explosion, status_chain (Petrify), ignite_flora, self_teleport, summon, channel
- Reuses the existing `DungeonSpell` pool — no new spell definitions needed
- Enemies cast freely: no MP, no miscast
- Casters inserted into `act()` ahead of melee/ranged decisions; stationary mobs (turrets, statues) skip movement

**Cone Breath Weapons (39 mobs)**
- New `breath_weapon: {type, damage, range, width, cooldown, status?}` field
- 90-degree cone from caster toward the player; respects line-of-sight; respects player's `apply_resistance`
- Element-keyed style: fire/cold/lightning/poison/steam/acid
- Tagged on all 13 elemental dragons + Storm/Quicksilver/Mottled/Shadow/Bone variants + all drakes + elementals + salamander/wendigo line + cannons/mortars + crabbies
- Cooldown 4-7 turns via existing `_breath_cd`; cone math reuses `bfs_path` Manhattan-style projection

**Summoners & Broods**
- `Summon Small Mammal`, `Summon Canine Familiar`, `Summon Spectral Wolf` reused for enemy casters
- Per-summoner cap (`max_active`); summons tagged with `_summoned_by` so the same caster won't exceed cap
- Broodmother: web/insect summon template
- Pandemonium Lord, Cerebov, Asmodeus, Antaeus, Mnoleg, Lom Lobon, Gloorx Vloq, Ereshkigal, Tiamat, Geryon — all summon on death
- Pikel pair: ally_buff on death + spawns a Pikel Minion
- Parghit pair: Pargi splits into two on death

**Floor Distribution & Balance**
- Tiered tiers retuned: 83 weak / 205 mid / 239 strong / 3 boss
- 8-floor identity: surface → dungeon → mid → lair → swamp → snake/slime → vaults → pandemonium
- Early floors (1-3) restricted to weak/mid (no `atk_base >= 7` on floors 1-3)
- Original 20 mobs preserved with their pre-Phase-0 depths and tiers (no regression)
- 4 entries kept at `spawn_weight=0` to suppress from random pool (Training Dummy, Snake, Canine, Wolf) — they remain in the data for completeness

**Save/Restore Compatibility**
- `SAVE_VERSION` 2 → 3 (per-instance cooldowns/breath_cd/shrieked fields)
- `_save_entity` writes: `cooldowns`, `breath_cd`, `shrieked`
- `_load_entity` restores them; data-driven config (spells, breath, on_death, etc.) reloads from the DB on load — consistent with the existing pattern
- Save/load roundtrip verified: Naga `constricts` + `on_hit` preserved, Fire Dragon `breath_weapon` reloaded + `breath_cd` restored, Lich `spells` + per-instance `cooldowns` restored, Pikel `on_death.ally_buff` preserved, summon `despawn_timer` preserved

**Splash Screen**
- Multi-colour banner (red→orange→yellow→cyan→purple)
- Version display (`v2.7.0`) and tagline
- 5 feature bullets highlighting the new content (531 monsters, casters, breaths, etc.)
- New `g` key opens the project on GitHub via `webbrowser.open(_GITHUB_URL, new=2, autoraise=True)`
- Re-renders the splash after the browser steals focus so the menu stays visible
- Tip line with one-liner gameplay hint
- `_GITHUB_URL` constant at the top of `wrapper.py` — easy to change

**Status:** v2.7 → 531 enemies · 113 casters · 39 breath weapons · 0 unique mobs · 8 floors · save/load v3.

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
