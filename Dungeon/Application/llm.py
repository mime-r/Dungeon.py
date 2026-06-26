"""Thin LLM client for Dungeon.py.

Supports three OpenAI-compatible providers configured via .env:
  lm_studio    - local LM Studio at http://127.0.0.1:1234
  openai       - api.openai.com
  opencode_zen - OpenCode Zen (configurable base URL)

All public methods return None on any error; callers never need to handle exceptions.
"""

import json
import logging
import os
import re
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

_log = logging.getLogger("dungeon.llm")


def _load_dotenv(path: Path) -> None:
    """Minimal .env loader - no external dependency required."""
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, val = line.partition("=")
                key = key.strip()
                val = val.strip().strip("\"'")
                os.environ.setdefault(key, val)
    except OSError:
        pass


# Load .env from the project root (three levels up from this file)
_load_dotenv(Path(__file__).parent.parent.parent / ".env")


class LLMClient:
    """OpenAI-compatible chat completions client with async support."""

    def __init__(self) -> None:
        provider = os.getenv("LLM_PROVIDER", "lm_studio").lower()

        if provider == "openai":
            self._base_url = "https://api.openai.com/v1"
            self._api_key = os.getenv("OPENAI_API_KEY", "")
            self._model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        elif provider == "opencode_zen":
            self._base_url = os.getenv("OPENCODE_ZEN_URL", "").rstrip("/")
            self._api_key = os.getenv("OPENCODE_ZEN_API_KEY", "")
            self._model = os.getenv("OPENCODE_ZEN_MODEL", "")
        else:  # lm_studio (default)
            self._base_url = os.getenv("LM_STUDIO_URL", "http://127.0.0.1:1234").rstrip("/") + "/v1"
            self._api_key = os.getenv("LM_STUDIO_API_KEY", "lm-studio")
            self._model = os.getenv("LM_STUDIO_MODEL", "")

        self.status: str = "disabled"   # "ok" | "disabled" | error description
        self.enabled: bool = False
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="llm")

        if self._api_key and self._base_url:
            self._probe()

    # ------------------------------------------------------------------

    def _probe(self) -> None:
        """Hit /v1/models to confirm the server is reachable and pick the active model."""
        req = urllib.request.Request(
            f"{self._base_url}/models",
            headers={"Authorization": f"Bearer {self._api_key}"},
        )
        try:
            with urllib.request.urlopen(req, timeout=5.0) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                models = [m["id"] for m in data.get("data", [])]
        except urllib.error.URLError as e:
            self.status = f"unreachable ({e.reason})"
            _log.warning("LLM server unreachable: %s", e)
            return
        except Exception as e:
            self.status = f"probe failed ({e})"
            _log.warning("LLM probe failed: %s", e)
            return

        if not models:
            self.status = "no models loaded in LM Studio"
            _log.warning("LLM: no models returned by /v1/models")
            return

        # If the configured model is present, use it; otherwise fall back to the first loaded model.
        if self._model and self._model in models:
            chosen = self._model
        else:
            chosen = models[0]
            if self._model and self._model not in models:
                _log.info("LLM: configured model %r not found; using %r", self._model, chosen)

        self._model = chosen
        self.enabled = True
        self.status = f"ok ({chosen})"
        _log.info("LLM ready: %s", self.status)

    # ------------------------------------------------------------------

    def complete(
        self,
        messages: list[dict],
        max_tokens: int = 1500,
        timeout: float = 60.0,
        temperature: float = 0.85,
    ) -> str | None:
        """Synchronous chat completion. Returns stripped text or None on any failure.

        max_tokens is high to give reasoning models enough budget to think and still
        produce a response. content is preferred over reasoning_content - we never
        display raw internal monologue.
        """
        if not self.enabled:
            return None
        payload = json.dumps({
            "model": self._model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": False,
        }).encode("utf-8")
        req = urllib.request.Request(
            f"{self._base_url}/chat/completions",
            data=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self._api_key}",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                msg = data["choices"][0]["message"]
                # Use content only - reasoning_content is internal monologue we never show.
                text = (msg.get("content") or "").strip()
                return text or None
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")
            _log.warning("LLM HTTP %s: %s", e.code, body[:200])
            return None
        except Exception as e:
            _log.warning("LLM complete failed: %s", e)
            return None

    def complete_async(self, messages: list[dict], **kwargs):
        """Submit a completion to the background thread. Returns a Future."""
        return self._executor.submit(self.complete, messages, **kwargs)

    def complete_json(self, messages: list[dict], **kwargs) -> dict | None:
        """Like complete() but parses the result as a JSON object. Returns None on failure."""
        text = self.complete(messages, **kwargs)
        if not text:
            return None
        text = re.sub(r'^```[a-z]*\s*', '', text.strip())
        text = re.sub(r'\s*```$', '', text)
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            _log.warning("LLM returned invalid JSON: %.120s", text)
            return None

    def complete_json_async(self, messages: list[dict], **kwargs):
        """Submit a JSON completion to the background thread. Returns a Future."""
        return self._executor.submit(self.complete_json, messages, **kwargs)
