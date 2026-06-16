<!-- refreshed: 2026-06-16 -->
# Architecture

**Analysis Date:** 2026-06-16

## System Overview

```text
┌─────────────────────────────────────────────────────────────┐
│                     Process Entry Point                      │
│              `Dungeon/Dungeon.py` (module check + boot)      │
└───────────────────────┬───────────────────────────────────────┘
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                       GameWrapper                             │
│              `Dungeon/Application/wrapper.py`                 │
│   Splash screen, top-level input loop (start/exit)            │
└───────────────────────┬───────────────────────────────────────┘
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                     Dungeon (god object)                      │
│              `Dungeon/Application/main.py`                    │
│  Owns: floors dict, player, db, ui, llm client, menu, turn loop│
└───────┬─────────────────┬─────────────────┬──────────────────┘
        │                 │                 │
        ▼                 ▼                 ▼
┌──────────────┐  ┌──────────────────┐  ┌────────────────────┐
│ DungeonMenu   │  │ DungeonUI         │  │ DungeonDatabase     │
│ `classes/     │  │ `classes/ui.py`   │  │ `classes/           │
│  menus.py`    │  │ Rich-based HUD    │  │  database.py`       │
│ input loop,   │  │ render(), message │  │ item/enemy/people    │
│ LLM hint/lore │  │ log               │  │ sub-DBs              │
│ orchestration │  └──────────────────┘  └─────────┬────────────┘
└───────┬───────┘                                    │
        │                                             ▼
        │                                  ┌────────────────────┐
        │                                  │ DungeonJSONDecoder  │
        │                                  │ `classes/decoder.py`│
        │                                  │ loads `data/*.json` │
        │                                  └────────────────────┘
        ▼
┌─────────────────────────────────────────────────────────────┐
│                  World / Entity Layer                         │
│  `classes/map.py`     - DungeonCell, DungeonPlayer, DungeonMap│
│  `classes/levelgen.py`- procedural floor generators            │
│  `classes/enemies.py` - DungeonEnemy, DungeonEnemyLoader       │
│  `classes/people.py`  - DungeonPeople/Trader/Healer            │
│  `classes/items.py`   - DungeonItem and subclasses              │
│  `classes/weapons.py` - weapon text templates / enum            │
│  `classes/status.py`  - StatusSet (poison/haste/etc.)           │
└─────────────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────────┐
│              Cross-cutting infrastructure                     │
│  `Application/llm.py`     - OpenAI-compatible HTTP client       │
│  `Application/config.py`  - StyleConfig/TerrainConfig/etc.      │
│  `Application/input.py`   - cross-platform single-key reader    │
│  `Application/loggers.py` - file logger, fatal-error handler    │
│  `Application/utils.py`   - small text/markup helpers           │
│  `Application/modules.py` - dependency bootstrap (pip install)  │
└─────────────────────────────────────────────────────────────┘
```

## Component Responsibilities

| Component | Responsibility | File |
|-----------|----------------|------|
| `Dungeon` | God-object game controller: holds all state, the turn loop, save/leaderboard, LLM orchestration entry points | `Dungeon/Application/main.py` |
| `GameWrapper` | Splash screen and program-level start/exit input loop | `Dungeon/Application/wrapper.py` |
| `DungeonMenu` | In-game menus, background/character selection, hint/lore scheduling, identification state | `Dungeon/Application/classes/menus.py` |
| `DungeonUI` | Renders the HUD frame (map, sidebar, message log, controls) every turn via Rich | `Dungeon/Application/classes/ui.py` |
| `DungeonMap` / `DungeonCell` / `DungeonPlayer` | Floor grid model, per-tile state, player position/combat/inventory | `Dungeon/Application/classes/map.py` |
| `generate_level` + helpers | Procedural floor generation (rooms, caves, BSP), scenery, vaults, temples, structures | `Dungeon/Application/classes/levelgen.py` |
| `DungeonEnemy` / `DungeonEnemyLoader` | Enemy combat stats, simple chase AI, on-hit effects | `Dungeon/Application/classes/enemies.py` |
| `DungeonPeople` / `DungeonTrader` / `DungeonHealer` | NPC shop and service logic | `Dungeon/Application/classes/people.py` |
| `DungeonItem` and subclasses | Weapons, potions, scrolls, inventory, shards | `Dungeon/Application/classes/items.py` |
| `StatusSet` | Status-effect bookkeeping (poison, haste, slow, confusion, etc.) for any entity | `Dungeon/Application/classes/status.py` |
| `DungeonDatabase` (+ sub-DBs) | In-memory lookup tables built once at startup from JSON data | `Dungeon/Application/classes/database.py` |
| `DungeonJSONDecoder` | Parses `Dungeon/data/*.json` into game object instances | `Dungeon/Application/classes/decoder.py` |
| `LLMClient` | Thin OpenAI-compatible HTTP client (sync + threaded async), used for floor themes, DM hints, item lore, NPC flavor | `Dungeon/Application/llm.py` |
| `config` (module-level singleton) | Style/colour table, terrain rules, map sizing, depth/progression constants | `Dungeon/Application/config.py` |
| `input` module | Cross-platform single keypress reader (msvcrt / termios), plus a scripted-input hook for tests | `Dungeon/Application/input.py` |
| `Logger` | File-based logger; `fatal()` prints and exits the process | `Dungeon/Application/loggers.py` |
| `check_modules` | First-run dependency bootstrap: detects/installs `tinydb`, `rich` into the running interpreter | `Dungeon/Application/modules.py` |

## Pattern Overview

**Overall:** Single-process, single-threaded turn-based game loop with a classic "god object" controller (`Dungeon`) that owns all subsystems by composition. Not MVC in the formal sense, but split along similar lines: `classes/map.py`+`classes/enemies.py`+`classes/items.py` are the model, `classes/ui.py` is the view, `main.py`+`classes/menus.py` is the controller/input-to-action layer.

**Key Characteristics:**
- Everything is reachable through `game` — most classes take `game` in `__init__` and store it, then reach back into `game.map`, `game.player`, `game.db`, `game.ui`, `game.llm` as needed. There is no dependency injection framework; `game` itself is the injection container.
- Data-driven content: enemies, items, weapons, potions, scrolls, people, names, backgrounds are all defined in `Dungeon/data/*.json` and hydrated into Python objects at startup by `DungeonJSONDecoder` (`Dungeon/Application/classes/decoder.py`). Code changes are rarely needed to add new content of an existing type.
- LLM features are strictly optional and additive: `LLMClient.enabled` gates everything; all LLM call sites check `self.game.llm.enabled` (or get `None` back) before using results, so the game is fully playable with no network/API config.
- Async work (LLM completions) is offloaded to a single-worker `ThreadPoolExecutor` (`Dungeon/Application/llm.py`) and polled via `Future.done()` from the synchronous turn loop — there is no asyncio event loop anywhere in the codebase.

## Layers

**Entry/Boot Layer:**
- Purpose: verify Python environment, install missing required packages, instantiate the wrapper
- Location: `Dungeon/Dungeon.py`, `Dungeon/Application/modules.py`
- Contains: dependency declarations (`tinydb`, `rich`), pip bootstrap logic
- Depends on: nothing else in the app (runs before any game imports)
- Used by: nothing; this is the top of the call stack

**Presentation/Input Layer:**
- Purpose: splash screen, raw keypress reading, Rich-based rendering of the HUD
- Location: `Dungeon/Application/wrapper.py`, `Dungeon/Application/input.py`, `Dungeon/Application/classes/ui.py`
- Contains: `GameWrapper`, the `read_key`/`read_direction` functions, `DungeonUI`
- Depends on: `config` for styling, `rich` library
- Used by: `Dungeon` controller and `DungeonMenu` for all user interaction

**Controller Layer:**
- Purpose: interprets input keys into game actions, owns the turn loop, dispatches to model objects, schedules LLM background work
- Location: `Dungeon/Application/main.py` (class `Dungeon`), `Dungeon/Application/classes/menus.py` (class `DungeonMenu`)
- Contains: movement/attack/inventory/search/descend/ascend logic, energy-based turn scheduling (`spend_turn`, `game_tick`, `advance_world`), hint/lore prompt building
- Depends on: model layer (map/enemies/items/people), `LLMClient`, `DungeonDatabase`, `DungeonUI`
- Used by: `GameWrapper` (constructs it), itself recursively via its own methods

**Model/World Layer:**
- Purpose: represents dungeon state — the grid, tiles, player, enemies, items, NPCs, status effects
- Location: `Dungeon/Application/classes/map.py`, `levelgen.py`, `enemies.py`, `items.py`, `people.py`, `weapons.py`, `status.py`, `misc.py`
- Contains: `DungeonCell`, `DungeonMap`, `DungeonPlayer`, `Room`/`LevelLayout`/generator functions, `DungeonEnemy`, item classes, `StatusSet`, `DungeonTimeData`
- Depends on: `config` (terrain rules, styling), `status.py` for effects
- Used by: controller layer almost exclusively

**Data Access Layer:**
- Purpose: load static JSON content once at startup and expose typed/searchable collections
- Location: `Dungeon/Application/classes/database.py`, `classes/decoder.py`, `Dungeon/data/*.json`
- Contains: `DungeonDatabase`, `DungeonItemDatabase`, `DungeonEnemyDatabase`, `DungeonPeopleDatabase`, `DungeonJSONDecoder`
- Depends on: filesystem (`Dungeon/data/`), model-layer item/enemy/people classes (for hydration)
- Used by: `Dungeon.__init__` (built once as `self.db`), level generation/population, player setup

**Cross-cutting Infrastructure:**
- Purpose: configuration, logging, LLM access, small utilities — used by every other layer
- Location: `Dungeon/Application/config.py`, `loggers.py`, `llm.py`, `utils.py`
- Contains: `config` singleton, `Logger`, `LLMClient`, `style_text`/`clear_screen`/`current_time`
- Depends on: nothing app-specific (config.py has no internal imports)
- Used by: every layer above

## Data Flow

### Primary Turn/Request Path

1. `GameWrapper` blocks on `keys.read_key()` in its splash loop (`Dungeon/Application/wrapper.py:42`); pressing Enter constructs `Dungeon(logger=..., rich_console=...)` (`Dungeon/Application/main.py`).
2. `Dungeon.__init__` builds `DungeonMenu`, `DungeonUI`, `DungeonDatabase` (which triggers `DungeonJSONDecoder` to hydrate all `data/*.json` into objects), `LLMClient` (probes the configured provider), and the `DungeonPlayer`.
3. `DungeonMenu`'s constructor (`Dungeon/Application/classes/menus.py:89`) runs the interactive input loop: each iteration calls `keys.read_key()`, maps it to a direction via `keys.read_direction`, and dispatches to a `Dungeon` method (`player.move`, `pickup`, `descend`, `search`, etc.).
4. Each player action that "spends a turn" calls `game.spend_turn()` / `game.game_tick()` (`main.py:617-645`), which advances enemy AI (`DungeonEnemy` chase/attack logic in `classes/enemies.py`), ticks status effects (`StatusSet`), and may trigger `_check_state_triggers()` in `DungeonMenu` to queue an async DM hint via `LLMClient.complete_json_async`.
5. After each action, `DungeonUI.render()` (`classes/ui.py:29`) redraws the full frame: header, map panel (`game.map.render_grid`), sidebar, and message log built from `self.messages`.

### Floor Generation Flow

1. `Dungeon._new_level(depth)` (`main.py:328`) calls `generate_level(...)` (`classes/levelgen.py:85`), which picks one of three algorithms — rooms-and-corridors (`_generate_rooms`), cellular-automata caves (`_generate_cave`), or BSP (`_generate_bsp`) — optionally biased by an LLM-generated `FloorTheme.layout_bias`.
2. The generator carves the grid, places stairs/vaults/temples, scatters terrain features (ponds, trees, grass/mud) and structures from `STRUCTURE_CATALOG`, then returns a `LevelLayout`.
3. `Dungeon._populate(level, depth, is_last, theme)` (`main.py:420`) spawns enemies (biased by `theme.enemy_bias` via `DungeonEnemyDatabase.random_biased`), scatters items/gold, and fills vault/temple rooms.
4. `Dungeon._generate_floor_theme(depth)` (`main.py:347`) optionally calls `self.llm.complete_json_async(...)` to produce a `FloorTheme` before generation; if the LLM is disabled or the call fails, generation proceeds with default/neutral bias values — themes are a non-blocking enhancement layer over a structurally complete generator.

**State Management:**
- All mutable game state lives on the `Dungeon` instance (`self.levels`, `self.player`, `self.depth`, `self._floor_themes`, `self._hint_future`, `self._lore_futures`, etc.) — there is no separate state-management library or immutable store. Per-floor state (`DungeonMap`) is cached in `self.levels: dict[int, DungeonMap]` so revisited floors persist.
- Persistence is handled by TinyDB (`Dungeon/leaderboard.json`) for the leaderboard only; there is no save/resume of an in-progress run.

## Key Abstractions

**`game` reference (ambient context object):**
- Purpose: every model/controller class receives the `Dungeon` instance as `game` and uses it to reach sibling subsystems (`game.map`, `game.player`, `game.db`, `game.ui`, `game.llm`, `game.message(...)`)
- Examples: `Dungeon/Application/classes/map.py` (`DungeonCell.__init__`, `DungeonPlayer.move`), `classes/enemies.py` (`DungeonEnemy.__init__`)
- Pattern: manual service-locator / composition root — `Dungeon` is the root, everything else is a leaf holding a back-reference

**Loader vs. instance split for content classes:**
- Purpose: `*Loader` classes (`DungeonEnemyLoader`, `DungeonPeopleLoader`) wrap a `types.SimpleNamespace` of raw JSON data and act as factories/templates; the corresponding runtime classes (`DungeonEnemy`, `DungeonTrader`) are concrete instances spawned per encounter
- Examples: `Dungeon/Application/classes/enemies.py`, `Dungeon/Application/classes/people.py`, `Dungeon/Application/classes/decoder.py`
- Pattern: prototype pattern — the database holds loaders, gameplay code asks for a loader then constructs/copies a live instance

**`StatusSet`:**
- Purpose: shared status-effect container usable by both `DungeonPlayer` and `DungeonEnemy` so effect logic (poison, regen, might, haste, slow, confusion) is written once
- Examples: `Dungeon/Application/classes/status.py`, consumed in `classes/map.py` (`DungeonPlayer.effective_speed`/`combat_bonus`) and `classes/enemies.py`
- Pattern: composition over inheritance — both entity types "have a" `StatusSet` rather than sharing a base entity class

**Energy-based turn scheduling:**
- Purpose: lets entities act at different speeds (haste/slow) without a full real-time clock
- Examples: `TURN = 10` constant and `effective_speed()` in `classes/map.py`/`classes/enemies.py`, consumed by `Dungeon.game_tick`/`advance_world` (`main.py:622-645`)
- Pattern: classic roguelike "energy" turn system — entities accumulate energy each tick and act once they cross a threshold

## Entry Points

**Process entry point:**
- Location: `Dungeon/Dungeon.py`
- Triggers: run directly (`python Dungeon.py`, or via `Run/*.bat`/`Run/linux_terminal.sh`)
- Responsibilities: reconfigure stdio to UTF-8, instantiate `Logger`, call `check_modules` to ensure `tinydb`/`rich` are importable (installing if needed), then construct `GameWrapper`

**`GameWrapper.__init__`:**
- Location: `Dungeon/Application/wrapper.py:16`
- Triggers: called once from `Dungeon.py` after module checks pass
- Responsibilities: print splash art, block on key input, construct `Dungeon` (the controller) on Enter, `sys.exit()` on Escape

**`Dungeon.__init__` / `DungeonMenu` input loop:**
- Location: `Dungeon/Application/main.py` (class `Dungeon`), `Dungeon/Application/classes/menus.py:89`
- Triggers: constructed by `GameWrapper` when the player starts a game
- Responsibilities: full game session lifecycle — setup, the turn-by-turn input loop, win/lose/quit handling

## Architectural Constraints

- **Threading:** Single-threaded main/game logic. The only background thread pool is `LLMClient._executor` (`ThreadPoolExecutor(max_workers=1)` in `Dungeon/Application/llm.py`), used exclusively for non-blocking LLM completions. Results are polled with `Future.done()`/`.result()` from the main loop — never awaited with blocking calls during a render.
- **Global state:** `config` in `Dungeon/Application/config.py` is a module-level singleton instantiated at import time and imported by nearly every other module (`from .config import config`). `Logger.logs_path` is a class attribute (shared default) but each `Logger()` instance creates its own timestamped log file.
- **Circular imports:** None observed — `main.py` imports from `classes/*`, `classes/*` import from `..config`/`..utils`/`..status`, and `config.py`/`utils.py` have no internal imports, keeping the dependency graph acyclic.
- **No asyncio:** All concurrency is via `concurrent.futures.ThreadPoolExecutor`, not `asyncio`. Do not introduce `async def`/`await` without also wiring an event loop — the rest of the codebase assumes synchronous, blocking control flow except for the explicit LLM future pattern.
- **God-object coupling:** `Dungeon` (`main.py`) and `DungeonMenu` (`classes/menus.py`) are large, deeply coupled controllers (1318 and 361 lines respectively) that reach into nearly every other module. New gameplay mechanics tend to grow these two files rather than introduce new top-level classes — this is the established pattern, not an oversight.

## Anti-Patterns

### Reaching through `game` instead of passing data explicitly

**What happens:** Methods on model classes (`DungeonPlayer.move`, `DungeonEnemy` AI) call back into `self.game.map`, `self.game.player`, `self.game.message(...)` rather than receiving what they need as parameters.
**Why it's wrong:** Makes unit-testing individual classes without a full `Dungeon` instance difficult, and makes data flow hard to trace without grepping for `self.game.`.
**Do this instead:** This is the established, consistent pattern throughout the codebase (every model class takes `game` in `__init__`) — follow it for new code rather than introducing a different DI style, to keep the codebase internally consistent. Do not attempt to "fix" this in isolated files; it would create inconsistency without removing the coupling at the `Dungeon` level.

### Defaulting silently on bad/missing LLM data

**What happens:** `LLMClient.complete`/`complete_json` return `None` on any failure (network, JSON parse, HTTP error) and callers in `main.py`/`menus.py` are expected to check for `None` and fall back to default behavior (e.g. neutral `FloorTheme`).
**Why it's wrong:** It is correct behavior for this codebase (LLM features must be optional), but new call sites must remember to handle `None` explicitly — there is no exception-based signal.
**Do this instead:** When adding a new LLM-backed feature, always code the non-LLM fallback path first and treat the LLM result as a pure enhancement, matching `Dungeon._generate_floor_theme` (`main.py:347`) and `DungeonMenu._flush_hint`/`_flush_lore` (`classes/menus.py:253`, `275`).

## Error Handling

**Strategy:** Fail loud and stop for unrecoverable setup errors (missing required dependency, fatal log), fail soft and continue for optional/runtime errors (LLM unreachable, malformed LLM JSON).

**Patterns:**
- `Logger.fatal(message)` (`Dungeon/Application/loggers.py:31`) writes the message, prints logs to the console, waits for a keypress, then calls `sys.exit(0)` — used for unrecoverable startup failures (e.g. a required module that could not be installed).
- `LLMClient` methods never raise to callers — every HTTP/JSON failure is caught internally, logged via the `logging` module (`_log.warning(...)`), and surfaced as a `None` return value (`Dungeon/Application/llm.py:140-170`).

## Cross-Cutting Concerns

**Logging:** File-based only via `Logger` (`Dungeon/Application/loggers.py`), writing to `logs/<app>-<unix-timestamp>.log` relative to the process working directory. `LLMClient` separately uses Python's stdlib `logging` module under the `dungeon.llm` namespace, which is not wired to `Logger`'s file output by default.
**Validation:** Minimal/ad-hoc — JSON content from `Dungeon/data/*.json` is trusted and decoded directly into objects (`classes/decoder.py`) with no schema validation; malformed LLM JSON is caught with a `try/except json.JSONDecodeError` in `LLMClient.complete_json`.
**Authentication:** Only relevant for the optional LLM integration — API keys are read from environment variables (`OPENAI_API_KEY`, `OPENCODE_ZEN_API_KEY`, `LM_STUDIO_API_KEY`) loaded from a project-root `.env` file via a hand-rolled loader in `Dungeon/Application/llm.py` (no `python-dotenv` dependency).

---

*Architecture analysis: 2026-06-16*
