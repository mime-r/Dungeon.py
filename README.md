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

| Key | Action |
| --- | --- |
| arrow keys or `h` `j` `k` `l` | move — walk into a monster to attack it |
| `y` `u` `b` `n` | diagonal movement (north-west / north-east / south-west / south-east) |
| `g` | pick up the item you are standing on |
| `i` / `d` | use / equip / drink / read / drop items from your pack |
| `>` / `<` | take stairs down / up |
| `s` | search adjacent walls for secret doors |
| `.` or space | wait one turn |
| `p` | pause · `?` | help · `esc` | quit |

The dungeon is full of doors (`+`), gold (`$`), potions (`!`), scrolls (`?`), weapons
(`)`), hidden vault rooms, and traders — Chemists, Blacksmiths, Merchants and Healers —
who can outfit you for the journey down. Combat resolves in the message log as you bump
into foes; keep an eye on your HP bar.

## Instructions
Instructions to download can be found [here](INSTRUCTIONS.md)

## Changelog:
15/6/26 v2.1 — "Caverns & Crosscuts"
- Diagonal movement: player uses `y`/`u`/`b`/`n`; enemies chase with 8-direction pathfinding
- Variable map sizes per floor (50–75 wide, 22–32 tall) instead of a fixed box
- Three level generators randomly chosen per floor: rooms-and-corridors (with oval rooms), cellular automata caves, and BSP-structured layouts
- Expanded name generator: 73 first names, 40 surnames, 26 epithets (was 48/24/11)

15/6/26 v2.0 — "Stone Soup" overhaul
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
- added compatabilty to linux (WSL currently not supported)
- MAJOR refactoring of code (credits to NJ)
- pick up items from the ground
- Changed to rich libary for UI

30/7/21 v1.1.6
- fixed bugs regarding the change of the order of files in v1.1.5

29/7/21 v1.1.5
- major noticible change of files and directory stuff, and fixed a minor bug with importing files :/

29/7/21 v1.1
- major bugfix
  - fixed the bug where when the user comes to the same square after killing an enemy, an array error comes up.
  - various other minor bugs regarding arrays and printing

28/7/21 v1.0
- minor bugfix
  - fixed the bug where player could not finish the game due to an annoying array error.

## Credits:
- [@mime-r](https://github.com/mime-r)
- [@NJ889](https://github.com/NicholasJohansan)
- [@duckupus](https://github.com/duckupus)
- [@Mini-Ware](https://github.com/Mini-Ware)
