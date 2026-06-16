# Testing Patterns

**Analysis Date:** 2026-06-16

## Test Framework

**Runner:**
- None detected. No `pytest`, `unittest`, or other test runner is configured or listed in `requirements.txt` (which only contains `rich` and `tinydb`).
- No `pytest.ini`, `pyproject.toml`, `setup.cfg`, or `tox.ini` exists in the repo root.

**Assertion Library:**
- Not applicable — no test code exists.

**Run Commands:**
```bash
# No test command exists in this project.
# requirements.txt only declares runtime dependencies: rich, tinydb
```

## Test File Organization

**Location:**
- No `test_*.py`, `*_test.py`, `tests/`, or `Run/tests*` directories exist anywhere in the repository (verified via repo-wide search for "test" in filenames — only matches are unrelated, e.g. none found).

**Naming:**
- Not applicable.

**Structure:**
```
No test directory structure exists.
```

## Test Structure

Not applicable — there is no existing suite to model new tests on. If tests are introduced, there is no established in-repo convention to follow; choose `pytest` (lightweight, no config required) and co-locate tests under a new top-level `tests/` directory mirroring `Dungeon/Application/` structure, e.g. `tests/classes/test_database.py` for `Dungeon/Application/classes/database.py`.

## Mocking

**Framework:** None present.

**What would need mocking if tests are added:**
- File I/O: `Dungeon/Application/classes/people.py` (`_name_pool()` reads `data/names.json`), `Dungeon/Application/loggers.py` (writes to `logs/dungeon-<ts>.log`), `Dungeon/Application/classes/decoder.py` (JSON data loading)
- Network calls: `Dungeon/Application/llm.py` (`urllib.request.urlopen` calls to LM Studio/OpenAI/OpenCode Zen endpoints in `_probe()` and chat completion methods) — these are the most isolated/mockable boundary in the codebase since `LLMClient` already swallows all exceptions and exposes `status`/`enabled` flags for verification
- `tinydb.TinyDB` persistence used in `Dungeon/Application/main.py` for the leaderboard (`leaderboard.json`)
- `random` module usage is pervasive in name generation, loot tables, and enemy spawning (`Dungeon/Application/classes/people.py`, `Dungeon/Application/classes/database.py`) — seed `random` or inject a controllable RNG if writing deterministic tests
- Terminal/keyboard input: `Dungeon/Application/input.py` reads raw keypresses — would need a fake input stream or dependency injection to test menu/game-loop flows

## Fixtures and Factories

None exist. Sample JSON data files under `Dungeon/data/` (referenced by `decoder.py` and `people.py` via `DATA_DIR`) could serve as the basis for test fixtures, but no fixture loading helpers currently exist for tests.

## Coverage

**Requirements:** None enforced — no coverage tool (`coverage.py`, `pytest-cov`) is configured.

**View Coverage:**
```bash
# Not applicable; no coverage tooling present.
```

## Test Types

**Unit Tests:** None exist. Best candidates for first unit tests (pure logic, minimal I/O): `Dungeon/Application/utils.py` (`style_text`, `controls_style`, `current_time`), `Dungeon/Application/classes/database.py` search/filter methods (`search_item`, `search_enemy`, `random_for_depth`, `all_for_depth`), `Dungeon/Application/classes/items.py` item dataclasses.

**Integration Tests:** None exist. Would require fixturing JSON data files in `Dungeon/data/` and constructing a `DungeonDatabase`/`Dungeon` game instance to test loader and decoder wiring end-to-end (`Dungeon/Application/classes/decoder.py`, `Dungeon/Application/classes/database.py`).

**E2E Tests:** Not used. The game is a terminal/TUI roguelike driven by raw keyboard input (`Dungeon/Application/input.py`) and Rich console rendering, which makes traditional E2E testing impractical without a terminal-automation harness.

## Common Patterns

**Async Testing:**
```python
# Not applicable. The only concurrency in the codebase is a single-worker
# ThreadPoolExecutor in Dungeon/Application/llm.py (LLMClient._executor),
# used to run blocking HTTP calls off the main thread. No asyncio is used.
```

**Error Testing:**
```python
# No existing pattern. Given the "never raises" contract documented in
# Dungeon/Application/llm.py, future tests for LLMClient should assert on
# the public `status` string and `enabled` boolean rather than expecting
# exceptions to propagate.
```

---

*Testing analysis: 2026-06-16*
