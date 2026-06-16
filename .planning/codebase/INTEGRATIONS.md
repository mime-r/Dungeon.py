# External Integrations

**Analysis Date:** 2026-06-16

## APIs & External Services

**LLM Providers (optional, AI flavor-text features only):**
- LM Studio (local) - default provider, OpenAI-compatible chat completions API
  - SDK/Client: none — raw `urllib.request` calls in `Dungeon/Application/llm.py`
  - Endpoint: `http://127.0.0.1:1234/v1` (configurable via `LM_STUDIO_URL`)
  - Auth: `LM_STUDIO_API_KEY` env var (defaults to literal `"lm-studio"`)
  - Model: `LM_STUDIO_MODEL` env var, falls back to first model returned by `/v1/models` probe
- OpenAI - `https://api.openai.com/v1`
  - SDK/Client: none — same raw `urllib.request` client, no `openai` package dependency
  - Auth: `OPENAI_API_KEY` env var
  - Model: `OPENAI_MODEL` env var, defaults to `gpt-4o-mini`
- OpenCode Zen - configurable third-party OpenAI-compatible provider
  - SDK/Client: same raw `urllib.request` client
  - Endpoint: `OPENCODE_ZEN_URL` env var (no default)
  - Auth: `OPENCODE_ZEN_API_KEY` env var
  - Model: `OPENCODE_ZEN_MODEL` env var

All three providers are accessed through a single unified client, `LLMClient` in `Dungeon/Application/llm.py`:
- Provider selection via `LLM_PROVIDER` env var (`lm_studio` | `openai` | `opencode_zen`), default `lm_studio`
- On construction, `_probe()` calls `GET {base_url}/models` with a 5s timeout to verify reachability and pick the active model
- `complete()` calls `POST {base_url}/chat/completions` (60s default timeout) for plain text completions; `complete_json()` wraps it and strips markdown code fences before `json.loads`
- `complete_async()`/`complete_json_async()` submit work to a single-worker `ThreadPoolExecutor` so LLM calls never block the game loop
- **Fail-safe design:** every public method returns `None` on any error (unreachable server, HTTP error, bad JSON) — callers never need exception handling, and the game falls back to procedural text generation
- Consumed by `Dungeon/Application/main.py` for: per-floor biome theme generation (`FloorTheme` dataclass), ambient DM-style flavor text, item lore on pickup/identification, and NPC greeting dialogue

## Data Storage

**Databases:**
- TinyDB (embedded JSON document store) - `tinydb` package
  - File: `Dungeon/leaderboard.json` (gitignored, regenerated at runtime)
  - Client: `TinyDB("leaderboard.json")` instantiated in `Dungeon/Application/main.py` (`self.leaderboard`)
  - Schema: per-run records with `session_id`, `name`, `time`, `moves`, `datetime`, `outcome` (`"win"` / `"death"`), inserted via `record_leaderboard()` in `Dungeon/Application/main.py`
  - Queried with `tinydb.Query()` to dedupe by `session_id` and to filter wins for high-score display

**File Storage:**
- Local filesystem only. No cloud storage, S3, or remote file integration.
- Static game data (enemies, weapons, potions, scrolls, NPCs, backgrounds) loaded from JSON files via `Dungeon/Application/classes/decoder.py` (`DungeonJSONDecoder`) — bundled with the source, not user-writable at runtime.

**Caching:**
- None.

## Authentication & Identity

**Auth Provider:**
- None — single-player local application with no user accounts. The only "auth" concept is API key bearer tokens sent to LLM providers (see above), stored client-side in `.env`.

## Monitoring & Observability

**Error Tracking:**
- None — no Sentry/Bugsnag or external error reporting.

**Logs:**
- Custom local file logger: `Dungeon/Application/loggers.py` (`Logger` class)
  - Writes timestamped lines to `logs/dungeon-<unix_time>.log` (directory gitignored)
  - Log levels: `INFO`, `DEBUG`, `ERROR`, `FATAL`
  - On `FATAL`, prints the error plus full log contents to the terminal and waits for a keypress before `sys.exit(0)`
  - LLM-specific logging uses Python's standard `logging` module under logger name `dungeon.llm` (`Dungeon/Application/llm.py`)

## CI/CD & Deployment

**Hosting:**
- None — not hosted. Distributed as a source download (`README.md`/`INSTRUCTIONS.md` link to a GitHub zip archive) and run locally via the scripts in `Run/`.

**CI Pipeline:**
- `.github/` directory present at repo root but contents not inspected in this pass; no CI status badges referenced in `README.md`. Treat as "none confirmed" — verify `.github/workflows/` directly if CI behavior matters for a task.

## Environment Configuration

**Required env vars:**
- None are strictly required — the game runs fully without a `.env` file.

**Optional env vars (gate AI features only):**
- `LLM_PROVIDER` - `lm_studio` | `openai` | `opencode_zen`
- `LM_STUDIO_URL`, `LM_STUDIO_API_KEY`, `LM_STUDIO_MODEL`
- `OPENAI_API_KEY`, `OPENAI_MODEL`
- `OPENCODE_ZEN_URL`, `OPENCODE_ZEN_API_KEY`, `OPENCODE_ZEN_MODEL`

**Secrets location:**
- `.env` at project root (present locally, gitignored via `.gitignore`). `.env.example` documents the schema without real secrets. Loaded by a minimal hand-rolled parser in `Dungeon/Application/llm.py::_load_dotenv` (sets env vars only if not already set via `os.environ.setdefault`).

## Webhooks & Callbacks

**Incoming:**
- None — no HTTP server runs as part of this application.

**Outgoing:**
- Outbound HTTP requests only, to the configured LLM provider's `/v1/models` and `/v1/chat/completions` endpoints (see APIs section above). No webhook callback registration.

---

*Integration audit: 2026-06-16*
