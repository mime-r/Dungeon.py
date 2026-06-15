# Dungeon.py
Welcome to the Dungeon: a turn-based roguelike inspired by **Dungeon Crawl Stone Soup**.
Descend through eight floors of an ever-shifting dungeon, fight monsters that hunt you in
real positions on the map, seize the **Orb of Zot** from the depths, and escape back to
the surface alive.

<p align="center"><img src="/resources/Dungeon.gif?raw=true"/></p>
<br />

## How to play

Your goal: **descend to the bottom (Depth 8), pick up the Orb of Zot, then climb all the
way back to the surface up-stairs.** Monsters get tougher the deeper you go.

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
Instructions to download can be found [here](INSTRUCTIONS.md)

## Changelog:
15/6/26 v2.2 - "Depths & Disciplines"
- Character progression: choose a class (Fighter/Hunter/Acolyte/Wanderer); gain XP, levels, max HP and combat bonuses
- Status effects for player and monsters: poison, regeneration, might, haste, slow, confusion (with a small energy/speed scheduler)
- Ranged combat: bows, crossbow and sling with an on-map aiming cursor; some monsters fire back
- Traps: hidden dart / poison / teleport / alarm traps, revealed by searching
- Item identification: potions and scrolls start unidentified until used (their name is revealed the moment you use them); Scroll of Identification reveals one unknown item; starting kit and shop wares come pre-identified
- Autoexplore (`o`): auto-walk the floor until a monster appears
- Larger floors that average ~70x70 (up to 80x80) with a scrolling, player-centred map view, so you discover each level's true size by exploring
- Temples: pillared chambers that may appear on a floor, guarded but holding treasure and a healing altar
- New content: Potions of Might/Speed/Regeneration/Curing, ranged weapons, Giant Spider and Kobold Slinger
- UI polish: the HUD sizes itself to the window (header always visible); quaffing/reading returns you to the map at once

15/6/26 v2.1 - "Caverns & Crosscuts"
- Diagonal movement: player uses `y`/`u`/`b`/`n`; enemies chase with 8-direction pathfinding
- Variable map sizes per floor (50-75 wide, 22-32 tall) instead of a fixed box
- Three level generators randomly chosen per floor: rooms-and-corridors (with oval rooms), cellular automata caves, and BSP-structured layouts
- Expanded name generator: 73 first names, 40 surnames, 26 epithets (was 48/24/11)

15/6/26 v2.0 - "Stone Soup" overhaul
- Multi-floor descent with up/down stairs and the Orb of Zot win condition (find it, escape)
- Rooms-and-corridors level generation with doors, secret doors and hidden vault rooms
- Rebuilt rich UI: map panel + hero sidebar (HP bar, depth, objective) + scrolling message log
- Bump-to-attack combat with persistent monsters that wake and chase you
- 11 depth-tiered enemy types and a boss; 10 weapons; scrolls; gold; more potions
- New NPC types: Blacksmith, Merchant and Healer alongside the Chemist
- Fixed the "John Doe" naming bug with a self-contained name generator
- Turn-based stdlib input (no more `keyboard`/admin/F11); dropped `pandas` and `names` deps
- Run scripts fixed (including case-correct Linux launch)

22/8/21 v1.2
- Linux compatibility (WSL not supported)
- Major code refactoring
- Ground item pickups
- Migrated UI to Rich library

30/7/21 v1.1.6
- Bugfixes for file reorganisation in v1.1.5

29/7/21 v1.1.5
- File and directory restructure; fixed import paths

29/7/21 v1.1
- Fixed crash when revisiting a tile after killing an enemy
- Various array and rendering fixes

28/7/21 v1.0
- Fixed game-breaking array error

## Credits:
- [@mime-r](https://github.com/mime-r)
- [@NJ889](https://github.com/NicholasJohansan)
- [@duckupus](https://github.com/duckupus)
- [@Mini-Ware](https://github.com/Mini-Ware)
