# Dungeon.py

Welcome to the Dungeon: a turn-based roguelike inspired by **Dungeon Crawl Stone Soup**.
Descend through eight floors of an ever-shifting dungeon, fight monsters that hunt you in
real positions on the map, collect the **three shards of the Broken Sigil** from the deep
floors, and escape back to the surface alive.

<p align="center"><img src="/resources/Dungeon.gif?raw=true"/></p>

## What's new in v2.7.3

- **Fixed inventory size** - pack capacity is now static (no more `DungeonInventory` bag drops); the item, its data file, and all its plumbing are gone
- **MP HUD fix** - max MP renders as `10` instead of `10.0` for saves that round-tripped through `float()`

For prior release notes, see [CHANGELOG.md](CHANGELOG.md).

## What's new in v2.7.1

- **531 monsters** (was 20) - dragons, demons, liches, slimes, beholders, and a menagerie from the DCSS bestiary
- **8 themed floors** - each floor spawns a thematically consistent mob mix (vermin on the surface, liches in the deep halls, hellbinders in pandemonium) with tier-mix balancing (weak on floor 1, strong on floor 8)
- **8 new status effects** - paralysis, blind, bleed, drain_max_hp, drain_mp, constricted, invisible, corrosion
- **Spellcasting AI** - 113 casters (oracles, pyromancers, liches, demonspawn) pick from their spell list with cooldowns
- **Cone breath weapons** - 39 dragons and elementals breathe fire/cold/lightning/poison/steam/acid
- **Death FX** - explode, spore cloud, split, shriek, ally buff, demon spawn, minion spawn
- **Inventory auto-sort** - press `s` in the pack screen; equipped items are always shown first
- **Item spawn display** - weapons/armour now print their enchantment + brand/ego effect when they spawn
- **Floor intro** - on descent, the message log shows the floor's name and description
- **Splash screen** - multi-colour banner, version, `g` key to open the project on GitHub
- **Save v3** - per-instance cooldowns, breath cooldown, and shriek tracker now persist

## Features

### Gameplay
- **Multi-floor descent** - 8 procedurally generated floors with up/down stairs
- **3 shard win condition** - collect all three sigil shards from depths 6, 7, 8, then escape
- **Boss fights** - Flame Guardian, Stone Guardian, Shadow Guardian guard each shard
- **Character classes** - 12 classes (Fighter, Hunter, Acolyte, Wanderer, Frostbringer, Venomancer, Stormcaller, Arcanist, Shadowblade, Crusader, and more) each with unique starting kit, spells, and aptitudes
- **Level & XP system** - kill monsters to gain XP, levels, more HP, and better attacks
- **Ranged combat** - bows, crossbow, sling with an on-map aiming cursor
- **Spellcasting** - 21 spells across 8 schools (Conjuration, Fire Magic, Ice Magic, Earth Magic, Poison Magic, Summoning, Translocation, Transmutation); staves boost matching schools
- **Attack delay** - DCSS-style swing times (Daggers swing twice as fast as Battleaxes); weapon skill reduces delay toward a per-weapon minimum
- **Status effects** - 18 effects: poison, regeneration, might, haste, slow, confusion, silence, see-invisible, vulnerability, inner flame, paralysis, blind, bleed, drain_max_hp, drain_mp, constricted, invisible, corrosion
- **Traps** - hidden dart, poison, teleport, and alarm traps revealed by searching (`s`)
- **Item identification** - potions and scrolls start unidentified; discover them by using
- **Autoexplore** (`o`) - auto-walk until a monster appears
- **Diagonal movement** - 8-direction player movement and monster pathfinding

### Monsters (531)
- **Themed floors** - 8 curated biomes (Surface Lair, Early Dungeon, Winding Depths, Deep Halls, Lair of Drakes, Murk & Brine, Vaults of Hell, Pandemonium) shape the spawn mix
- **8 new status effects** - paralysis (sea snake), blind (sun moth), bleed (warg), drain_max_hp (vampire), drain_mp (mummy), constricted (kraken), invisible (shadow), corrosion (yellow draconian)
- **Spellcasting mobs** - 113 casters with weighted random spell selection, per-spell cooldowns, summon caps
- **Breath weapons** - 90-degree cone, element-keyed style, 4-7 turn cooldown
- **Death FX** - explode on death (bombardier beetle), spore cloud (deathcap), split (azure jelly), shriek (killer bee), ally buff (Pikel), demon spawn (Pandemonium Lord), minion spawn (Pikel Minion)
- **Boss-tier guardians** - the 3 shard-guardians are reserved via spawn_weight=0; they only spawn via the boss-fight trigger

### Items, Brands & Enchantment
- **15 weapon brands** with per-floor tier availability (Venom/Protection early -> Flaming/Freezing/Electrocution mid -> Vampiric/Spectral/Heavy late -> Speed/Antimagic/Chaos endgame)
- **7 armour egos** (Stealth, rF+, rC+, Will+, SInv, Archery, Parrying) - similar per-floor tier system
- **Unified enchantment system** - weapons and armour spawn with +0 to +5 natural enchantment based on floor tier; +1 per scroll of enchant up to +9
- **Scroll of Brand Weapon** applies a random brand to a chosen weapon (refuses magical staves and already-branded weapons)
- **Sacred Scourge** - the holy flail that actually works: +50% damage vs undead, +25% vs demonic
- **Holy Wrath brand** - +75% damage vs undead and demonic enemies
- **Holiness tags** - Skeleton/Zombie/Wraith (undead), Imp/Demon (demonic); visible in the examine panel
- **Spawn display** - weapons/armour with a brand or ego print their enchantment and effect in the message log when they spawn

### 19 Scrolls (DCSS-style)
- **Very Common:** Identification
- **Common:** Teleportation
- **Uncommon:** Amnesia, Blinking, Butterflies, Enchant Armour, Enchant Weapon, Fear, Fog, Immolation, Noise, Revelation, Silence, Summoning, Vulnerability
- **Rare:** Brand Weapon, Poison, Torment
- **Very Rare:** Acquirement
- All scrolls are unidentified until read; Scroll of Identification reveals an unknown item; reading a scroll consumes it (unless its target was impossible, in which case it's preserved)

### Dynamic World Generation
- **Three level generators** - rooms-and-corridors, cellular automata caves, BSP layouts
- **Variable map sizes** - floors average ~70x70 with scrolling player-centred view
- **7 terrain types** with 3 floor features (shrubs, mushrooms, rubble)
- **Biome themes** - each floor generates a unique AI-assisted setting (volcanic rift, fungal depths, sacred shrine, etc.) with hand-crafted fallback biomes when the LLM is disabled
- **Secret doors** and **hidden vault rooms**
- **Temples** - pillared chambers guarded by monsters but holding treasure
- **Fog of war** - Scroll of Fog spreads a screen-blocking cloud

### AI-Powered Features
*All AI features are optional - the game runs perfectly without any configuration.*

- **Biome theme generation** - each floor gets a unique AI-generated theme (volcanic rift, fungal depths, sacred shrine, etc.) that shapes enemy composition, loot, traps, terrain, and structure blueprints
- **DM-style ambient hints** - atmospheric flavour text when your HP drops low or during quiet moments every ~30 turns
- **Item lore** - one-sentence grim backstories generated when you pick up or identify an item
- **NPC dialogue** - traders and healers greet you with unique, in-character voice lines

Configure via `.env` (see [INSTRUCTIONS.md](INSTRUCTIONS.md) for details).

### Inventory
- **Equipped-first view** - equipped items are always shown as the first entries on every page
- **Auto-sort** - press `s` in the pack screen to permanently sort by equipped -> type -> name -> enchantment
- **Page-local sub-headers** - pages with both equipped and unequipped items show a `-- equipped --` / `-- pack --` divider
- **Sub-headers** separate the equipped section from the rest of the pack for quick scanning

### Save & Restore
- **Save anytime** with `S` - preserves full game state: player, inventory, equipment, all floors, enemies, NPCs, floor themes, brand/ego/enchant/holiness/silence/fog state
- **Resume** on next launch by pressing `R` at the splash screen
- Game state persists to `savegame.json` (v3 format; v1 and v2 saves gracefully rejected)
- **v3 per-instance state** - enemy cooldowns, breath cooldown, and shriek tracker round-trip with the save

### NPCs & Items
- **4 NPC types** - Chemist, Blacksmith, Merchant, Healer with unique shops
- **50+ weapons**, 5 staves, potions, scrolls, spellbooks, gold
- **Hidden wares** - NPCs have a base stock plus randomised extra items

## How to play

Your goal: **collect all three shards of the Broken Sigil** - one on each of depths 6, 7,
and 8 - then **climb back to the surface**. Each shard is guarded by a boss. The exit only
unlocks once you carry the complete sigil. Monsters get tougher the deeper you go.

At the start you choose a **class** from 12 options (Fighter, Hunter, Acolyte, Wanderer, Frostbringer, Venomancer, Stormcaller, Arcanist, Shadowblade, Crusader, and more), each with
its own starting kit, spells, skills and health. Killing monsters grants **XP and levels** (more HP and
better attacks).

Items spawn with a natural enchantment level that scales with depth. Use Scrolls of Enchant
Weapon/Armour strategically - early enchantments are wasted on weak bases; hoard them
until you find a +3 or better base, then burn them all to hit the +9 cap. Scrolls of Brand
Weapon ignore the tier system (use them on your endgame weapon to roll for Speed or
Vampiric).

| Key | Action |
| --- | --- |
| arrow keys or `h` `j` `k` `l` | move - walk into a monster to attack it |
| `y` `u` `b` `n` | diagonal movement (north-west / north-east / south-west / south-east) |
| `f` | fire a ranged weapon (aim, then `f`/`enter`; `tab` cycles targets) |
| `o` | autoexplore the floor (stops when a monster appears) |
| `g` | pick up items on your tile (choose which, or take all) |
| `i` / `d` | use / equip / unequip / drink / read / drop items from your pack |
| `>` / `<` | take stairs down / up |
| `s` | search adjacent tiles for secret doors and traps (also: auto-sort the pack) |
| `x` | examine mode (cursor over a tile to read full details) |
| `S` | save game (`R` to restore on next launch) |
| `.` or space | wait one turn |
| `p` | pause / `?` | help / `esc` | quit |
| `g` (splash) | open the project on GitHub in your browser |

The dungeon is full of doors (`+`), gold (`$`), potions (`!`), scrolls (`?`), weapons
(`)`), hidden vault rooms, **traps** (`^`), and traders - Chemists, Blacksmiths, Merchants
and Healers - who can outfit you for the journey down. Potions and scrolls start
**unidentified** until you use them; some potions grant status effects (Might, Speed,
Regeneration, Curing) and some monsters poison or slow you. Weapons can be branded with
elemental effects (Flaming, Freezing, Electrocution) and armour can spawn with ego
properties (rF+, Stealth, SInv). Combat resolves in the message log as you bump into foes;
keep an eye on your HP bar and the status line.

## Instructions

Download and run instructions can be found [here](INSTRUCTIONS.md).

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for the full version history.

## Credits

- [@mime-r](https://github.com/mime-r)
- [@NJ889](https://github.com/NicholasJohansan)
- [@duckupus](https://github.com/duckupus)
- [@Mini-Ware](https://github.com/Mini-Ware)
