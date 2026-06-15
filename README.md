# Dungeon.py

Welcome to the Dungeon: a turn-based roguelike inspired by **Dungeon Crawl Stone Soup**.
Descend through eight floors of an ever-shifting dungeon, fight monsters that hunt you in
real positions on the map, collect the **three shards of the Broken Sigil** from the deep
floors, and escape back to the surface alive.

<p align="center"><img src="/resources/Dungeon.gif?raw=true"/></p>

## Features

### 🎮 Core Gameplay
- **Multi-floor descent** - 8 procedurally generated floors with up/down stairs
- **3 shard win condition** - collect all three sigil shards from depths 6, 7, 8, then escape
- **Boss fights** - Flame Guardian, Stone Guardian, Shadow Guardian guard each shard
- **Character classes** - Fighter, Hunter, Acolyte, or Wanderer, each with unique starting kit
- **Level & XP system** - kill monsters to gain XP, levels, more HP, and better attacks
- **Ranged combat** - bows, crossbow, sling with an on-map aiming cursor
- **Status effects** - poison, regeneration, might, haste, slow, confusion for player and monsters
- **Traps** - hidden dart, poison, teleport, and alarm traps revealed by searching (`s`)
- **Item identification** - potions and scrolls start unidentified; discover them by using
- **Autoexplore** (`o`) - auto-walk until a monster appears
- **Diagonal movement** - 8-direction player movement and monster pathfinding

### 🗺️ Dynamic World Generation
- **Three level generators** - rooms-and-corridors, cellular automata caves, BSP layouts
- **Variable map sizes** - floors average ~70×70 with scrolling player-centred view
- **7 terrain types** - shallow/deep water, lava, trees, chasms, grass, mud
- **3 floor features** - shrubs, mushrooms, rubble
- **Secret doors** and **hidden vault rooms**
- **Temples** - pillared chambers guarded by monsters but holding treasure

### 🤖 AI-Powered Features
*All AI features are optional - the game runs perfectly without any configuration.*

- **Biome theme generation** - each floor gets a unique AI-generated theme (volcanic rift, fungal depths, sacred shrine, etc.) that shapes enemy composition, loot, traps, terrain, and structure blueprints
- **DM-style ambient hints** - atmospheric flavour text when your HP drops low or during quiet moments every ~30 turns
- **Item lore** - one-sentence grim backstories generated when you pick up or identify an item
- **NPC dialogue** - traders and healers greet you with unique, in-character voice lines

Configure via `.env` (see [INSTRUCTIONS.md](INSTRUCTIONS.md) for details).

### 🏪 NPCs & Items
- **4 NPC types** - Chemist, Blacksmith, Merchant, Healer with unique shops
- **10+ weapons**, potions, scrolls, gold
- **Hidden wares** - NPCs have a base stock plus randomised extra items

## How to play

Your goal: **collect all three shards of the Broken Sigil** - one on each of depths 6, 7,
and 8 - then **climb back to the surface**. Each shard is guarded by a boss. The exit only
unlocks once you carry the complete sigil. Monsters get tougher the deeper you go.

At the start you choose a **class** (Fighter, Hunter, Acolyte or Wanderer), each with
its own starting kit and health. Killing monsters grants **XP and levels** (more HP and
better attacks).

| Key | Action |
| --- | --- |
| arrow keys or `h` `j` `k` `l` | move - walk into a monster to attack it |
| `y` `u` `b` `n` | diagonal movement (north-west / north-east / south-west / south-east) |
| `f` | fire a ranged weapon (aim, then `f`/`enter`; `tab` cycles targets) |
| `o` | autoexplore the floor (stops when a monster appears) |
| `g` | pick up items on your tile (choose which, or take all) |
| `i` / `d` | use / equip / unequip / drink / read / drop items from your pack |
| `>` / `<` | take stairs down / up |
| `s` | search adjacent tiles for secret doors and traps |
| `.` or space | wait one turn |
| `p` | pause · `?` | help · `esc` | quit |

The dungeon is full of doors (`+`), gold (`$`), potions (`!`), scrolls (`?`), weapons
(`)`), hidden vault rooms, **traps** (`^`), and traders - Chemists, Blacksmiths, Merchants
and Healers - who can outfit you for the journey down. Potions and scrolls start
**unidentified** until you use them; some potions grant status effects (Might, Speed,
Regeneration, Curing) and some monsters poison or slow you. Combat resolves in the message
log as you bump into foes; keep an eye on your HP bar and the status line.

## Instructions

Download and run instructions can be found [here](INSTRUCTIONS.md).

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for the full version history.

## Credits

- [@mime-r](https://github.com/mime-r)
- [@NJ889](https://github.com/NicholasJohansan)
- [@duckupus](https://github.com/duckupus)
- [@Mini-Ware](https://github.com/Mini-Ware)
