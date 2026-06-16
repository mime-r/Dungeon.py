# Coding Conventions

**Analysis Date:** 2026-06-16

## Naming Patterns

**Files:**
- Lowercase, single-word module names: `main.py`, `utils.py`, `loggers.py`, `config.py`, `modules.py`, `wrapper.py`, `input.py`, `llm.py`
- Domain classes live under `Dungeon/Application/classes/` grouped by concern: `items.py`, `enemies.py`, `people.py`, `map.py`, `menus.py`, `status.py`, `weapons.py`, `database.py`, `decoder.py`, `misc.py`, `ui.py`

**Classes:**
- `Dungeon`-prefixed PascalCase for nearly all domain classes: `DungeonPlayer`, `DungeonItem`, `DungeonWeapon`, `DungeonDatabase`, `DungeonMenu`, `DungeonTrader`, `DungeonHealer`, `DungeonTimeData` (see `Dungeon/Application/classes/people.py`, `Dungeon/Application/classes/database.py`)
- `*Loader` suffix for classes that build a domain object from JSON data, e.g. `DungeonPeopleLoader` in `Dungeon/Application/classes/people.py`
- `*Config` suffix for static configuration containers, e.g. `StyleConfig` in `Dungeon/Application/config.py`
- `Enum` subclasses for fixed string sets, e.g. `LogType(str, Enum)` in `Dungeon/Application/loggers.py`, `ItemUseType(str, Enum)` in `Dungeon/Application/classes/items.py`

**Functions/Methods:**
- snake_case throughout, e.g. `generate_name()`, `search_item()`, `random_for_depth()` in `Dungeon/Application/classes/database.py`
- Private/module-internal helpers prefixed with a single underscore: `_name_pool()`, `_NAME_POOL` in `Dungeon/Application/classes/people.py`; `_load_dotenv()`, `_probe()` in `Dungeon/Application/llm.py`
- Dunder-style lifecycle methods used intentionally for emphasis, e.g. `Dungeon.__start__()` static entry method in `Dungeon/Application/main.py`

**Variables:**
- snake_case for locals and attributes (`heal_cost_per_hp`, `potential_sales`, `base_url`)
- Module-level constants in SCREAMING_SNAKE_CASE: `DATA_DIR`, `_NAME_POOL` (`Dungeon/Application/classes/people.py`), `_APPLICATION_NAME` (`Dungeon/Application/loggers.py`)

**Types:**
- Python 3.10+ union syntax used for optional/typed params: `name: str | None = None`, `dict | None`
- Light use of `list[X]` / `dict` generics for attribute annotations, e.g. `self.potions: list[DungeonPotion]` in `Dungeon/Application/classes/database.py`
- Type hints are applied to function signatures and class attributes but not exhaustively enforced; many internal helpers omit return types when trivial

## Code Style

**Formatting:**
- No formatter config (no `.prettierrc`, `pyproject.toml`, or `black`/`ruff` config detected) — formatting is manually consistent: 4-space indentation, double quotes preferred for strings
- Docstrings are short, one-to-three line triple-quoted summaries placed directly under class/function signatures (Google/plain style, no full Sphinx/NumPy sections)
- Module-level docstrings used for non-trivial modules to explain purpose/contract, e.g. the top of `Dungeon/Application/llm.py` documents the three supported providers and the "never raises" contract

**Linting:**
- No `.eslintrc`/`ruff`/`flake8` config found in the repo. No enforced lint pipeline detected.

## Import Organization

**Order (observed in `Dungeon/Application/main.py`):**
1. Standard library imports (`datetime`, `os`, `sys`, `time`, `operator`, `traceback`, `random`, `dataclasses`)
2. Third-party imports (`tinydb`, `rich`)
3. Local relative imports, ordered from package-level to nested (`from . import input as keys`, `from .config import config`, `from .utils import ...`, then `from .classes.X import ...`)

**Path Aliases:**
- None — all internal imports use explicit relative imports (`from .classes.map import DungeonMap`), no path aliasing or absolute package shortcuts configured.

## Error Handling

**Patterns:**
- Narrow `try/except` blocks around I/O and network calls, with typed exception classes caught first and a generic `Exception` fallback last, e.g. `Dungeon/Application/llm.py` (`except urllib.error.URLError as e: ... except Exception as e: ...`)
- Library/integration modules document a "never raises" contract in their module docstring and enforce it by catching broadly and returning `None`/sentinel state instead of propagating — see `Dungeon/Application/llm.py` (`"All public methods return None on any error; callers never need to handle exceptions."`)
- Top-level game loop in `Dungeon/Application/main.py` (`Dungeon.__start__`, around line 1305) is the single place where uncaught exceptions are handled: `SystemExit` is re-raised, `KeyboardInterrupt` exits cleanly with a logged message, and any other `Exception` is routed to `logger.fatal()` with a full traceback string built via `traceback.format_tb`.
- `Logger.fatal()` in `Dungeon/Application/loggers.py` is the terminal error path: it writes to the log file, prints a `[FATAL ERROR]` banner with the log path, waits for a keypress, then calls `sys.exit(0)`. Use this when an error should end the program with user-visible diagnostics.
- Defensive `getattr(data, "field", default)` is used throughout loader/decoder classes instead of try/except for optional JSON fields, e.g. `getattr(people_data, "personality", "")` in `Dungeon/Application/classes/people.py`.
- Silent best-effort fallbacks are acceptable for non-critical paths (e.g. `_name_pool()` swallows any load error and falls back to a minimal built-in name pool; `_load_dotenv()` swallows `OSError` if `.env` is missing).

## Logging

**Framework:** Custom `Logger` class in `Dungeon/Application/loggers.py` (file-based, not Python's `logging` module for game events); the `llm.py` module additionally uses the standard `logging` module (`logging.getLogger("dungeon.llm")`) for its own internal warnings.

**Patterns:**
- One `Logger` instance is created per run, writing to `logs/dungeon-<unix-timestamp>.log` (`Dungeon/Application/loggers.py`)
- Use `logger.info(...)` for normal lifecycle events ("dungeon set up is done, starting game"), `logger.debug(...)` for verbose diagnostic detail, `logger.fatal(...)` only for unrecoverable errors that should terminate the process
- `LogType` enum constrains log levels to `INFO`, `DEBUG`, `ERROR`, `FATAL`
- User-facing game text uses Rich markup via `style_text()` (`Dungeon/Application/utils.py`) and `Panel`/`self.print(...)`, not `print()` directly, except for early bootstrap messages before the Rich console exists (e.g. `print("Loading...")` near the top of `Dungeon/Application/main.py`)

## Comments

**When to Comment:**
- Section-divider comments (`# --- terrain / map tiles ---`) group related config attributes in `Dungeon/Application/config.py`
- Inline comments explain *why*, not *what*, e.g. `# Load .env from the project root (three levels up from this file)` in `Dungeon/Application/llm.py`
- `# ---...---` horizontal rule comments separate logical sections within a class, e.g. between `__init__` and `_probe` in `LLMClient`

**Docstrings:**
- Every public class gets a one-line docstring describing its responsibility, written in third person without "This class" boilerplate, e.g. `"""Root database that aggregates item, enemy, and people sub-databases."""`
- Non-obvious methods get a short docstring explaining intent/algorithm, e.g. `"""Like random_for_depth but biases towards preferred_names when possible."""` in `Dungeon/Application/classes/database.py`
- No formal TSDoc/Sphinx param/return blocks are used — docstrings stay prose-only and brief

## Function Design

**Size:** Most functions are short (under ~20 lines); larger orchestration methods exist in `Dungeon/Application/main.py` (the `Dungeon` game-loop class) and `Dungeon/Application/classes/levelgen.py`, where procedural generation logic is necessarily longer.

**Parameters:** Keyword arguments with defaults are favored for optional configuration (`occupation: str = "trader"`, `heal_cost_per_hp: int = 1`). Constructors that need shared context take an explicit `game` or `global_db` reference rather than using globals (e.g. `DungeonPeopleLoader.__init__(self, game, data)`).

**Return Values:** Search/lookup methods return `None` (or empty list) when nothing matches rather than raising, e.g. `search_item()`, `search_enemy()` in `Dungeon/Application/classes/database.py` (`return results[0] if results else None`). Follow this convention for any new lookup helper.

## Module Design

**Exports:** No `__all__` lists are used; modules rely on explicit `from .module import Name` imports at call sites. `Dungeon/Application/classes/__init__.py` and `Dungeon/Application/__init__.py` are present but minimal/empty — they exist to mark packages, not to re-export.

**Barrel Files:** Not used. Each consumer imports directly from the specific submodule (`from .classes.map import DungeonMap, DungeonPlayer`), so add new classes to their relevant `classes/*.py` file and import them explicitly where needed — do not add a re-export barrel.

---

*Convention analysis: 2026-06-16*
