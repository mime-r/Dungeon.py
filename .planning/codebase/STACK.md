# Technology Stack

**Analysis Date:** 2026-06-16

## Languages

**Primary:**
- Python 3.10+ - entire codebase (`Dungeon/Dungeon.py`, `Dungeon/Application/*.py`), tested on 3.11 and 3.14 per `INSTRUCTIONS.md`

**Secondary:**
- JSON - static game data files loaded by `Dungeon/Application/classes/decoder.py` (enemies, items, weapons, NPCs, backgrounds) and the `Dungeon/leaderboard.json` TinyDB store
- Shell/Batch - launcher scripts in `Run/` (`Run/windows_terminal.bat`, `Run/command_prompt.bat`, `Run/python.bat`, `Run/linux_terminal.sh`)

## Runtime

**Environment:**
- CPython 3.10+ (no virtualenv tooling committed; `Run/` scripts invoke the system `py`/`python3` interpreter directly)
- Terminal/console application — no GUI, no web server. Runs as a single-process interactive CLI game.

**Package Manager:**
- `pip`, via `requirements.txt`
- Lockfile: missing (no `requirements-lock.txt`, `Pipfile.lock`, or `poetry.lock`; `requirements.txt` has unpinned versions)
- Self-bootstrapping dependency installer: `Dungeon/Application/modules.py` checks for `tinydb`/`rich` at startup and offers to `pip install` them into `sys.executable` if missing (invoked from `Dungeon/Dungeon.py`)

## Frameworks

**Core:**
- `rich` (unpinned) - terminal UI rendering: panels, tables, styled text, live rendering. Used throughout `Dungeon/Application/wrapper.py`, `Dungeon/Application/main.py`, `Dungeon/Application/classes/ui.py`, `Dungeon/Application/classes/menus.py`
- `tinydb` (unpinned) - embedded JSON-document database. Used only for the leaderboard: `Dungeon/Application/main.py` (`TinyDB("leaderboard.json")`), persisted to `Dungeon/leaderboard.json`

**Testing:**
- None detected. No `pytest`, `unittest` test files, or test configuration found anywhere in the repo.

**Build/Dev:**
- None — no build step. The game runs directly from source via `python Dungeon/Dungeon.py` (or the `Run/` launcher scripts).
- `Dungeon/Application/modules.py` acts as a lightweight runtime dependency installer in place of a formal build/setup tool.

## Key Dependencies

**Critical:**
- `rich` - all terminal rendering (colors, panels, live HUD, tables); without it the game cannot display anything
- `tinydb` - leaderboard persistence (`Dungeon/leaderboard.json`); a required import per `Dungeon/Dungeon.py` even though only used for leaderboard records

**Infrastructure:**
- Python standard library only otherwise: `urllib.request`/`urllib.error` (LLM HTTP calls in `Dungeon/Application/llm.py`), `json`, `pathlib`, `dataclasses`, `concurrent.futures.ThreadPoolExecutor`, `subprocess`, `importlib`

## Configuration

**Environment:**
- `.env` file at project root (gitignored, present locally), loaded by a hand-rolled minimal parser in `Dungeon/Application/llm.py::_load_dotenv` — no `python-dotenv` dependency
- `.env.example` documents available variables (file exists but unreadable under current tool permissions; variable names/usage confirmed via `Dungeon/Application/llm.py` and `INSTRUCTIONS.md`)
- All `.env` variables are optional and gate only AI/LLM features; the game runs fully without any `.env` file
- Game configuration constants (colors, symbols, terrain, spawn rates, progression curve) live in `Dungeon/Application/config.py` as plain Python classes (`StyleConfig`, `TerrainConfig`, `SymbolConfig`, `MapConfig`, `DepthConfig`, `SpawnConfig`, `ProgressionConfig`, `PlayerConfig`), aggregated into a single `Config`/`config` object

**Build:**
- No build config files (no `pyproject.toml`, `setup.py`, `setup.cfg` found)
- `requirements.txt` (root) — two lines: `rich`, `tinydb` (no versions pinned)

## Platform Requirements

**Development:**
- Python 3.10+ installed and on PATH (or available as `py` launcher on Windows)
- Any terminal capable of ANSI/Unicode rendering (Windows Terminal recommended per `README.md`/`INSTRUCTIONS.md`; legacy code pages are handled defensively in `Dungeon/Dungeon.py` via `stdout`/`stderr` UTF-8 reconfiguration)
- Optional: a local LM Studio server (`http://127.0.0.1:1234`) or OpenAI/OpenCode Zen API access for AI features

**Production:**
- No deployment target — distributed as a downloadable source zip (per `INSTRUCTIONS.md`, from the GitHub repo) run locally by the end user, not hosted as a service
- Game state and logs persist to the local filesystem only: `Dungeon/leaderboard.json` (TinyDB) and `logs/*.log` (`Dungeon/Application/loggers.py`, gitignored)

---

*Stack analysis: 2026-06-16*
