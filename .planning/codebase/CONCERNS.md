# Codebase Concerns

**Analysis Date:** 2026-06-16

## Tech Debt

**Monolithic main game class:**
- Issue: `Dungeon/Application/main.py` is 1318 lines and contains the entire `Dungeon` game-state class — rendering, input dispatch, combat, leaderboard, menus, save-free session handling, and the game loop all live in one file/class.
- Files: `Dungeon/Application/main.py`
- Impact: Any change to one subsystem (e.g. combat) risks touching unrelated code in the same class; hard to unit test in isolation; cognitive load is high for new contributors.
- Fix approach: Split into mixins or composed services (e.g. `CombatController`, `LeaderboardService`, `InputDispatcher`) that the `Dungeon` class composes, similar to how `classes/map.py`, `classes/menus.py`, etc. are already separated.

**Large level generator:**
- Issue: `Dungeon/Application/classes/levelgen.py` is 1000 lines, mixing room/corridor generation, biome theming, trap placement, and enemy/NPC population in one module.
- Files: `Dungeon/Application/classes/levelgen.py`
- Impact: Difficult to test individual generation steps; bugs in trap placement vs. room carving are hard to isolate.
- Fix approach: Extract distinct phases (room carving, corridor connection, decoration/population) into separate functions or small classes with clear inputs/outputs.

**Defensive `getattr` fallback pattern instead of validated data models:**
- Issue: Code repeatedly uses `getattr(e.data, "spawn_weight", 0)` and `getattr(e.data, "depth", [1, 99])`-style fallbacks rather than validating loaded JSON data up front.
- Files: `Dungeon/Application/classes/database.py:39-40`, `:52-54`, similar patterns likely throughout `classes/decoder.py` and `levelgen.py`.
- Impact: Malformed or incomplete JSON content data (e.g. in `data/*.json`) silently falls back to defaults instead of failing loudly, which can mask content bugs (an enemy intended to spawn on depths 3-5 silently spawning depths 1-99 if the key is misspelled).
- Fix approach: Validate JSON-loaded data schemas once at decode time (`classes/decoder.py`) and raise/log clearly on missing required fields, rather than scattering `getattr` defaults through consumer code.

**Relative-path dependent file I/O:**
- Issue: The leaderboard database is opened with a bare relative path: `TinyDB("leaderboard.json")` in `Dungeon/Application/main.py:129`, and logs are written under `Path.cwd() / "logs"` in `Dungeon/Application/loggers.py:19`.
- Files: `Dungeon/Application/main.py:129`, `Dungeon/Application/loggers.py:19`
- Impact: Behavior depends on the current working directory the process is launched from. Launching via `Run/windows_terminal.bat`, `python.bat`, or directly with `py Dungeon.py` from a different directory can create `leaderboard.json` and `logs/` in unexpected locations, fragmenting save/leaderboard data and logs across multiple copies.
- Fix approach: Anchor both paths to a fixed location (e.g. relative to `Dungeon/Dungeon.py`'s directory, or a platform user-data directory) instead of `cwd`.

**Minimal hand-rolled `.env` loader:**
- Issue: `Dungeon/Application/llm.py:23-36` implements its own `.env` parser (`_load_dotenv`) instead of using a vetted library, with naive `partition("=")` and `strip("\"'")` logic that does not handle escaped characters, multi-line values, or `#` inside quoted values correctly.
- Files: `Dungeon/Application/llm.py:23-40`
- Impact: Subtly malformed `.env` values (e.g. containing `#` or `=` in unexpected positions) will silently misparse rather than error, leading to confusing "LLM unreachable" failures that are hard to diagnose.
- Fix approach: Document the parser's limitations in `.env.example`, or adopt `python-dotenv` if an extra dependency is acceptable (`requirements.txt` currently lists none for env loading).

## Known Bugs

**None confirmed via static review** — no `TODO`/`FIXME`/`HACK` markers exist anywhere in `Dungeon/**/*.py`, and no bare `except:` clauses were found. This suggests the codebase is actively maintained, but also means latent bugs are not self-documented; manual playtesting is the only way most issues would surface.

## Security Considerations

**Auto-installs third-party packages without integrity checks:**
- Risk: `Dungeon/Application/modules.py:_pip_install` (lines 14-26) runs `pip install <module>` directly against PyPI using `sys.executable -m pip install`, triggered automatically the first time a required/optional dependency (`tinydb`, `rich`) is missing, after only a single `y`/`n` prompt with no hash pinning or `requirements.txt` enforcement at install time.
- Files: `Dungeon/Application/modules.py:14-26`, `Dungeon/Dungeon.py:12,27-31`
- Current mitigation: User must type `y` to confirm install; module names are hardcoded in `Dungeon/Dungeon.py:16-22` (not user-controlled), so this is not directly exploitable by a malicious save/content file today.
- Recommendations: Pin versions matching `requirements.txt` when invoking `pip install` (currently installs latest unpinned version), and consider checking if `requirements.txt` is present to install via `-r requirements.txt` instead of per-module installs, to keep installed versions consistent with what's been tested.

**LLM integration sends/executes externally-sourced JSON without strict validation:**
- Risk: `Dungeon/Application/llm.py:complete_json` (lines 159-170) parses model output as JSON via `json.loads` and returns it directly to callers; if callers in `main.py` use returned fields (e.g. dialogue text, item names) without validating types/lengths before display or game-state mutation, a misbehaving or compromised LLM backend (especially `opencode_zen` with a configurable base URL, or a self-hosted LM Studio instance) could inject malformed or oversized data into rendered output.
- Files: `Dungeon/Application/llm.py:159-174`
- Current mitigation: `complete()` strips/limits via `max_tokens`; JSON parse failures return `None` rather than raising.
- Recommendations: Validate the shape of `complete_json` results against an expected schema/key-set at each call site before use, and cap string lengths before passing into Rich-rendered panels (Rich markup injection from untrusted text is also a risk — see below).

**Untrusted text rendered through Rich markup without sanitization:**
- Risk: Throughout `Dungeon/Application/main.py`, player names, NPC names, and potentially LLM-generated flavor text are interpolated directly into f-strings passed to `self.print(...)` / `Panel(...)`, which Rich interprets as markup (e.g. `f"[name]{self.player.name}[/name]"` at `main.py:1290`, `:1297`). If a player name or LLM output contains literal `[...]` sequences, it could break formatting or, combined with the LLM integration, allow an LLM response to inject arbitrary Rich style tags into displayed text.
- Files: `Dungeon/Application/main.py:1281`, `:1290`, `:1297`; `Dungeon/Application/llm.py` (text source)
- Current mitigation: Player names are generated from a curated `data/names.json` pool (`Dungeon/Application/classes/people.py:_name_pool`), not free-form user input, which limits exposure today.
- Recommendations: If free-form player name entry or LLM-generated text is ever rendered, escape Rich markup characters (`rich.markup.escape`) before interpolation.

## Performance Bottlenecks

**Synchronous LLM calls block the game loop if used incorrectly:**
- Problem: `LLMClient.complete()` in `Dungeon/Application/llm.py:110-153` is a blocking call with up to 60s timeout; `complete_async`/`complete_json_async` exist to offload this to a single-worker `ThreadPoolExecutor` (`llm.py:64`), but any direct call to the synchronous `complete()`/`complete_json()` from the main game loop thread would freeze input handling and rendering for the duration of the HTTP round-trip.
- Files: `Dungeon/Application/llm.py:64`, `:110-174`
- Cause: Single-worker executor serializes all async LLM requests; if multiple are queued, later ones wait behind earlier ones even though each result may only be needed individually.
- Improvement path: Audit all call sites in `main.py` to confirm only the `_async` variants are used during active gameplay, and consider increasing `max_workers` if concurrent LLM requests (e.g. simultaneous NPC dialogue) become a feature.

**Leaderboard JSON file grows unbounded:**
- Problem: `record_leaderboard` (`main.py:1262-1273`) inserts a new TinyDB record on every game-over event and never prunes old entries; `winners` are sorted and only the top 10 are displayed (`main.py:1280`), but the underlying `leaderboard.json` file keeps every record ever recorded.
- Files: `Dungeon/Application/main.py:1262-1282`
- Cause: No retention policy or archival for non-winning/old entries.
- Improvement path: Periodically trim `leaderboard.json` to the top N winners plus recent N entries, or migrate to a capped ring-buffer style store, since TinyDB loads the entire JSON file into memory on each open (`main.py:129`) and re-serializes on every write.

## Fragile Areas

**Game loop has no top-level exception recovery per turn:**
- Files: `Dungeon/Application/main.py:1143-1154` (`gameloop`), `Dungeon/Application/main.py:1305-1318` (`__start__`)
- Why fragile: A single uncaught exception anywhere inside `advance_world()`, `render()`, or `handle()` during a turn propagates all the way up to `__start__`'s `except Exception` handler, which calls `logger.fatal(...)` — and `Logger.fatal` (`Dungeon/Application/loggers.py:42-52`) terminates the process via `sys.exit(0)` after writing logs. There is no per-turn isolation, so any single bad enemy AI calculation, malformed content JSON, or level-generation edge case ends the entire session immediately with no recovery, mid-game save, or retry.
- Safe modification: When adding new turn-processing logic (status effects, traps, ranged combat), wrap risky operations (e.g. ones that index into possibly-empty lists, or `getattr` chains on content data) in narrow try/except blocks with in-game error messages rather than letting exceptions bubble to the fatal handler.
- Test coverage: No automated tests directory was found in the repository; all current confidence relies on manual play.

**Content-driven systems trust JSON shape implicitly:**
- Files: `Dungeon/Application/classes/decoder.py`, `Dungeon/Application/classes/database.py`
- Why fragile: `DungeonJSONDecoder` (referenced in `database.py:13`) is the single point converting raw JSON content files into loader objects; if a content file in `data/` is hand-edited incorrectly (missing key, wrong type), failures can surface far away from the decode site — e.g. inside `random_for_depth` (`database.py:34-46`) via silently-defaulted `getattr` calls, or much later during rendering.
- Safe modification: When adding new content fields (new enemy stat, new trap type), update `decoder.py` to validate/require the field explicitly rather than relying on consumer-side `getattr` defaults.
- Test coverage: No schema validation tests found for `data/*.json` content files.

## Scaling Limits

**Single-process, single-player, local-only design:**
- Current capacity: Designed for one interactive terminal session at a time; TinyDB leaderboard file (`leaderboard.json`) is not safe for concurrent multi-process writes (TinyDB has no built-in locking).
- Limit: Running multiple game instances simultaneously from the same working directory (e.g. two terminals) risks leaderboard write corruption/race conditions since both processes open the same `leaderboard.json` independently.
- Scaling path: Not a concern for a single-player terminal roguelike under normal use; if multi-instance or networked play is ever considered, the leaderboard storage would need a proper lock or migration to a real database.

## Dependencies at Risk

**`tinydb` for leaderboard persistence:**
- Risk: TinyDB reads/writes the entire JSON document on every operation (no incremental writes), which does not scale well as `leaderboard.json` grows (see Performance Bottlenecks above) and has no schema enforcement.
- Impact: Slower leaderboard reads/writes over time; potential data corruption on crash mid-write since TinyDB's default storage is not atomic.
- Migration plan: For a small leaderboard, this is acceptable; if growth becomes an issue, switch to `sqlite3` (standard library, atomic writes via transactions) with minimal API surface change since only `insert`/`search`/`all` are used (`Dungeon/Application/main.py:129,144-145,1263,1275`).

**Self-rolled `.env` parsing instead of `python-dotenv`:**
- Risk: See Tech Debt section above — edge cases in env file parsing are unhandled.
- Impact: Confusing failures for users configuring `LM_STUDIO_URL`/`OPENAI_API_KEY`/etc. if their `.env` has unusual formatting.
- Migration plan: Low priority; current implementation works for the documented `.env.example` format. Revisit only if user reports surface parsing issues.

## Missing Critical Features

**No automated test suite:**
- Problem: No `tests/`, `test_*.py`, or `*_test.py` files were found anywhere in the repository (`Dungeon/**`).
- Blocks: Any refactor of `main.py` or `levelgen.py` (both flagged above as overly large) cannot be safely verified without manual playtesting end-to-end. Regressions in combat math, level generation validity (e.g. unreachable stairs), or leaderboard recording would only be caught by a human playing the game.

**No save/resume capability:**
- Problem: The game loop (`Dungeon/Application/main.py:1143-1154`) has no mid-game persistence; only final outcomes are recorded to the leaderboard. A crash (see Fragile Areas) or accidental terminal close loses all progress.
- Blocks: Long play sessions are entirely at risk from any unhandled exception terminating the process.

## Test Coverage Gaps

**Entire codebase:**
- What's not tested: Every module — combat resolution, level generation correctness (connectivity, stair placement), status effect interactions (`Dungeon/Application/classes/status.py`), item/equipment logic (`Dungeon/Application/classes/items.py`, `weapons.py`), and the LLM client's error paths (`Dungeon/Application/llm.py`).
- Files: All of `Dungeon/Application/**`
- Risk: Any change risks silent regressions; the LLM client in particular (`llm.py`) has many branchy error-handling paths (`URLError`, `HTTPError`, generic `Exception`, JSON decode failure) that are well-structured but entirely unverified by automated tests.
- Priority: High — given `main.py` and `levelgen.py` are both large, frequently-changed files (per recent commit history: "Add character classes and status effects", "The Terrain Update"), a regression test suite for level generation invariants (e.g. "stairs are always reachable") and combat math would have the highest risk-reduction value.

---

*Concerns audit: 2026-06-16*
