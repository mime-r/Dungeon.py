# Codebase Structure

**Analysis Date:** 2026-06-16

## Directory Layout

```
Dungeon.py/                         # repo root
├── Dungeon/                        # the actual Python application package
│   ├── Dungeon.py                  # process entry point (run this file)
│   ├── __version__.py              # version string
│   ├── leaderboard.json            # TinyDB-backed leaderboard (runtime data, gitignored content grows)
│   ├── logs/                       # per-run log files, generated at runtime (not curated)
│   ├── data/                       # static JSON game content (enemies, items, NPCs, names, backgrounds)
│   └── Application/                # all game source code
│       ├── __init__.py
│       ├── main.py                 # Dungeon controller: god object, turn loop, gameplay actions
│       ├── wrapper.py              # GameWrapper: splash screen + start/exit
│       ├── menus.py is NOT here    # (menus.py lives under classes/, see below)
│       ├── modules.py              # dependency bootstrap (pip install missing packages)
│       ├── input.py                # cross-platform single-keypress reader
│       ├── loggers.py              # file Logger class
│       ├── llm.py                  # OpenAI-compatible LLM client (optional AI features)
│       ├── config.py               # StyleConfig/TerrainConfig/MapConfig/etc. singleton
│       ├── utils.py                # style_text, clear_screen, current_time helpers
│       └── classes/                # model + sub-controller classes
│           ├── __init__.py
│           ├── map.py              # DungeonCell, DungeonMap, DungeonPlayer
│           ├── levelgen.py          # procedural floor generation (rooms/cave/BSP)
│           ├── enemies.py           # DungeonEnemy, DungeonEnemyLoader, combat text
│           ├── people.py            # DungeonPeople/DungeonTrader/DungeonHealer
│           ├── items.py             # DungeonItem and subclasses (weapon/potion/scroll/etc.)
│           ├── weapons.py           # WeaponType enum, DungeonWeaponTexts
│           ├── status.py            # StatusSet (status effects)
│           ├── menus.py             # DungeonMenu: input loop, hint/lore orchestration
│           ├── ui.py                # DungeonUI: Rich-based HUD rendering
│           ├── database.py          # DungeonDatabase + Item/Enemy/People sub-databases
│           ├── decoder.py           # DungeonJSONDecoder: loads data/*.json into objects
│           └── misc.py              # DungeonTimeData (elapsed time / pause)
├── Run/                            # launch scripts for different platforms
│   ├── windows_terminal.bat
│   ├── command_prompt.bat
│   ├── python.bat
│   └── linux_terminal.sh
├── resources/                      # images used in README (gif, screenshot)
├── .claude/                        # Claude Code local settings
├── .planning/                      # GSD planning artifacts (this document lives here)
├── .github/workflows/              # CI (CodeQL analysis)
├── README.md, CHANGELOG.md, INSTRUCTIONS.md, CLAUDE.md, ideas.txt, LICENSE
├── requirements.txt                 # pinned/required pip packages
├── .env / .env.example              # LLM provider configuration (never read contents — see forbidden_files)
└── .gitignore
```

## Directory Purposes

**`Dungeon/`:**
- Purpose: the runnable application package; `python Dungeon.py` (or the `Run/` scripts) execute `Dungeon/Dungeon.py` with `Dungeon/` as the working directory
- Contains: entry script, version file, runtime-generated `logs/` and `leaderboard.json`, static `data/`, and all source under `Application/`
- Key files: `Dungeon/Dungeon.py`, `Dungeon/__version__.py`

**`Dungeon/Application/`:**
- Purpose: all first-party Python source for the game (everything importable as `from Application... import ...` or `from . import ...` / `from .. import ...` inside `classes/`)
- Contains: the controller (`main.py`), the splash wrapper (`wrapper.py`), infrastructure modules (`config.py`, `input.py`, `loggers.py`, `llm.py`, `utils.py`, `modules.py`), and the `classes/` subpackage
- Key files: `Application/main.py` (1318 lines, largest file — core gameplay logic), `Application/classes/levelgen.py` (1000 lines — procedural generation)

**`Dungeon/Application/classes/`:**
- Purpose: model classes (world/entities/items) plus two sub-controllers (`menus.py`, `ui.py`) and the data-access pair (`database.py`, `decoder.py`)
- Contains: one class-family per file, generally named `Dungeon<Noun>` (e.g. `DungeonEnemy`, `DungeonPlayer`, `DungeonItem`)
- Key files: `classes/map.py` (grid + player), `classes/levelgen.py` (floor generation), `classes/database.py` + `classes/decoder.py` (content loading)

**`Dungeon/data/`:**
- Purpose: static, hand-authored JSON content that defines all spawnable enemies, NPCs, items, names, and starting backgrounds
- Contains: `enemies.json`, `people.json`, `weapons.json`, `potions.json`, `scrolls.json`, `inventory.json`, `names.json`, `backgrounds.json`
- Key files: each file maps 1:1 to a `fetch_*` method on `DungeonJSONDecoder` (`Application/classes/decoder.py`)

**`Dungeon/logs/`:**
- Purpose: runtime output only — one timestamped log file per process run, created by `Logger.__init__` (`Application/loggers.py`)
- Generated: Yes
- Committed: No (not curated source; safe to ignore/delete)

**`Run/`:**
- Purpose: convenience launch scripts so non-developers can start the game without typing a `python` command manually, across Windows (`.bat`) and Linux (`.sh`)
- Contains: `windows_terminal.bat`, `command_prompt.bat`, `python.bat`, `linux_terminal.sh`

**`resources/`:**
- Purpose: static images referenced by `README.md` (gameplay GIF, biome screenshot)
- Generated: No
- Committed: Yes

## Key File Locations

**Entry Points:**
- `Dungeon/Dungeon.py`: process entry point — stdio setup, dependency check, boots `GameWrapper`
- `Dungeon/Application/wrapper.py`: `GameWrapper` — splash screen, constructs `Dungeon` controller on Enter

**Configuration:**
- `Dungeon/Application/config.py`: all game-tuning constants and Rich style strings (colours, terrain rules, map size, depth/progression formulas)
- `.env` / `.env.example` (root): LLM provider selection and API credentials — existence noted only, never read by this analysis

**Core Logic:**
- `Dungeon/Application/main.py`: the `Dungeon` class — turn loop, player actions (move/attack/pickup/descend/search/apply potion/use scroll), LLM theme/hint orchestration
- `Dungeon/Application/classes/menus.py`: `DungeonMenu` — interactive input loop, background selection, identification bookkeeping, hint/lore prompt building
- `Dungeon/Application/classes/levelgen.py`: all procedural floor generation algorithms and scenery placement

**Testing:**
- Not detected — no `tests/`, `*.test.*`, or `*.spec.*` files found in the repository. `Application/input.py` exposes a `feed_keys()`/`clear_scripted()` scripted-input hook explicitly intended for future headless/test driving of the game loop, but no test suite currently uses it.

## Naming Conventions

**Files:**
- Lowercase, singular nouns describing the module's content domain: `map.py`, `enemies.py`, `items.py`, `people.py`, `status.py`, `weapons.py`
- Infrastructure/utility files use a verb-ish or role-based name: `loggers.py`, `modules.py`, `utils.py`, `wrapper.py`, `decoder.py`

**Directories:**
- `classes/` holds all class-based model/sub-controller code, distinguishing it from the flatter infrastructure modules directly under `Application/`
- `data/` holds only static JSON, never Python

**Classes:**
- Prefixed `Dungeon<Noun>` for nearly every domain class: `DungeonCell`, `DungeonMap`, `DungeonPlayer`, `DungeonEnemy`, `DungeonItem`, `DungeonMenu`, `DungeonUI`, `DungeonDatabase`. This prefix convention should be followed for any new top-level game class.
- `<Noun>Loader` for factory/template classes that wrap raw JSON data before a live instance is spawned: `DungeonEnemyLoader`, `DungeonPeopleLoader`.
- `<Noun>Texts` for bundles of combat/flavor string templates: `EnemyTexts` (`classes/enemies.py`), `DungeonWeaponTexts` (`classes/weapons.py`).

## Where to Add New Code

**New enemy, item, NPC, or background (data-only content):**
- Add an entry to the appropriate file in `Dungeon/data/` (`enemies.json`, `weapons.json`, `potions.json`, `scrolls.json`, `inventory.json`, `people.json`, `backgrounds.json`)
- No Python changes needed unless the new content requires a new mechanic (e.g. a new `on_hit` effect type)

**New gameplay mechanic / player action:**
- Add the action method to the `Dungeon` class in `Dungeon/Application/main.py`, following the existing pattern of methods like `pickup()`, `descend()`, `apply_potion()`, `use_scroll()`, `search()`
- Wire the new key/action into the input dispatch inside `DungeonMenu`'s loop in `Dungeon/Application/classes/menus.py`

**New entity type (e.g. a companion, a new occupant kind for `DungeonCell`):**
- Create a new class in `Dungeon/Application/classes/` named `Dungeon<Noun>`, taking `game` in `__init__` per the established convention
- If it needs a `StatusSet`, status-effect logic already lives in `Application/classes/status.py` and is reusable as-is

**New level generation algorithm or terrain feature:**
- Add a `_generate_<name>` function alongside `_generate_rooms`/`_generate_cave`/`_generate_bsp` in `Dungeon/Application/classes/levelgen.py`, and register it in `generate_level()`'s dispatch logic
- New scenery types follow the `_place_*`/`_scatter_*` function naming already used in that file

**New LLM-backed feature:**
- Add a prompt-building method and a `_flush_*` consumer to `DungeonMenu` (`Application/classes/menus.py`), mirroring `_build_hint_prompt`/`_flush_hint` and `_build_lore_prompt`/`_flush_lore`
- Always code the non-LLM fallback first; `LLMClient.complete`/`complete_json` (`Application/llm.py`) return `None` on any failure and callers must handle that gracefully

**Utilities:**
- Small, dependency-free text/markup/time helpers go in `Dungeon/Application/utils.py`
- Anything Rich-markup-styling related should reuse `style_text()` from `utils.py` and the named styles in `config.py`'s `StyleConfig`, not new ad-hoc ANSI/markup strings

## Special Directories

**`Dungeon/logs/`:**
- Purpose: one log file per process run (`dungeon-<unix-timestamp>.log`)
- Generated: Yes
- Committed: No

**`Dungeon/Application/__pycache__/`:**
- Purpose: Python bytecode cache
- Generated: Yes
- Committed: No

**`Dungeon/leaderboard.json`:**
- Purpose: TinyDB JSON-file database of past run results (used by `Dungeon.leaderboard` in `Application/main.py`)
- Generated: Yes (grows at runtime)
- Committed: depends on `.gitignore` — treat as runtime data, not source

---

*Structure analysis: 2026-06-16*
