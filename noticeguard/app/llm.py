"""Provider-agnostic LLM access with a content-addressed on-disk cache.

Providers (env LLM_PROVIDER):
  gemini      google-genai SDK, model LLM_MODEL (default gemini-3.8-flash)
  anthropic   anthropic SDK, model LLM_MODEL (default claude-sonnet-5)
  claude_cli  shells out to the local `claude -p` CLI (Claude Code login; no API key).
              Temperature cannot be set through the CLI, so it uses the CLI's default sampling.

Every call is cached at cache/llm/<sha256(provider, model, prompt, docs, temperature, run)>.json
unless caching is disabled (NOTICEGUARD_CACHE=0 or use_cache=False).
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

try:  # optional .env loading
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
except Exception:  # pragma: no cover
    pass

ROOT = Path(__file__).resolve().parents[1]
CACHE_DIR = ROOT / "cache" / "llm"

DEFAULT_MODELS = {
    "gemini": "gemini-3.8-flash",
    "anthropic": "claude-sonnet-5",
    "claude_cli": "sonnet",
}


def detect_provider() -> str:
    p = os.environ.get("LLM_PROVIDER", "").strip().lower()
    if p:
        return p
    # Production defaults to Gemini; never silently fall back to a local Claude login.
    return "gemini"


class LLMUnavailable(RuntimeError):
    pass


@dataclass
class LLMResponse:
    text: str
    cached: bool
    provider: str
    model: str
    cache_key: str
    elapsed_ms: int = 0


def _extract_json(text: str) -> Any:
    """Robustly pull the first JSON object/array out of a model response."""
    text = text.strip()
    fence = re.search(r"```(?:json)?\s*(.*?)```", text, re.S)
    if fence:
        text = fence.group(1).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # find outermost braces
    for opener, closer in (("{", "}"), ("[", "]")):
        start = text.find(opener)
        end = text.rfind(closer)
        if start != -1 and end > start:
            try:
                return json.loads(text[start : end + 1])
            except json.JSONDecodeError:
                continue
    raise ValueError("no JSON found in model output")


class LLM:
    def __init__(self, provider: Optional[str] = None, model: Optional[str] = None,
                 use_cache: Optional[bool] = None, cache_dir: Optional[Path] = None):
        self.provider = (provider or detect_provider()).lower()
        env_model = os.environ.get("LLM_MODEL", "").strip()
        # LLM_MODEL from .env is meant for the configured provider; only use it if it matches
        self.model = model or (env_model if (env_model and self._model_fits(env_model)) else DEFAULT_MODELS.get(self.provider, "gemini-3.8-flash"))
        if use_cache is None:
            use_cache = os.environ.get("NOTICEGUARD_CACHE", "1") not in ("0", "false", "no")
        self.use_cache = use_cache
        self.cache_dir = cache_dir or CACHE_DIR
        self.calls = 0
        self.cache_hits = 0
        self._client: Any = None
        self._client_lock = threading.Lock()

    def _model_fits(self, m: str) -> bool:
        m = m.lower()
        if self.provider == "gemini":
            return m.startswith("gemini")
        if self.provider == "anthropic":
            return m.startswith("claude")
        if self.provider == "claude_cli":
            return not m.startswith("gemini")
        return True

    # ------------------------------------------------------------------ cache
    def cache_key(self, prompt: str, docs: str, temperature: float, run: int, system: str = "") -> str:
        h = hashlib.sha256()
        h.update(json.dumps([self.provider, self.model, system, prompt, docs, temperature, run], ensure_ascii=False).encode())
        return h.hexdigest()

    def _cache_path(self, key: str) -> Path:
        return self.cache_dir / f"{key}.json"

    # ------------------------------------------------------------------ public
    def complete(self, prompt: str, *, docs: str = "", system: str = "", temperature: float = 0.0,
                 run: int = 0, json_schema: Optional[dict] = None, max_tokens: int = 4096) -> LLMResponse:
        key = self.cache_key(prompt, docs, temperature, run, system)
        path = self._cache_path(key)
        if self.use_cache and path.exists():
            data = json.loads(path.read_text())
            self.cache_hits += 1
            return LLMResponse(text=data["text"], cached=True, provider=data.get("provider", self.provider),
                               model=data.get("model", self.model), cache_key=key)
        full_prompt = prompt if not docs else f"{prompt}\n\n----- DOCUMENT -----\n{docs}\n----- END DOCUMENT -----"
        t0 = time.time()
        text = self._call(full_prompt, system=system, temperature=temperature, json_schema=json_schema, max_tokens=max_tokens)
        elapsed = int((time.time() - t0) * 1000)
        self.calls += 1
        if self.use_cache:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps({
                "provider": self.provider, "model": self.model, "temperature": temperature, "run": run,
                "system": system, "prompt": prompt, "docs": docs, "text": text, "elapsed_ms": elapsed,
                "created": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            }, ensure_ascii=False, indent=1))
        return LLMResponse(text=text, cached=False, provider=self.provider, model=self.model, cache_key=key, elapsed_ms=elapsed)

    def complete_json(self, prompt: str, **kw) -> tuple[Any, LLMResponse]:
        """Completion parsed as JSON, with one retry if parsing fails."""
        resp = self.complete(prompt, **kw)
        try:
            return _extract_json(resp.text), resp
        except ValueError:
            retry_prompt = prompt + "\n\nYour previous answer was not valid JSON. Output ONLY a single valid JSON value, nothing else."
            resp2 = self.complete(retry_prompt, **kw)
            return _extract_json(resp2.text), resp2

    # ------------------------------------------------------------------ providers
    def _call(self, prompt: str, *, system: str, temperature: float, json_schema: Optional[dict], max_tokens: int) -> str:
        if self.provider == "gemini":
            return self._call_gemini(prompt, system, temperature, json_schema, max_tokens)
        if self.provider == "anthropic":
            return self._call_anthropic(prompt, system, temperature, json_schema, max_tokens)
        if self.provider == "claude_cli":
            return self._call_claude_cli(prompt, system, json_schema)
        raise LLMUnavailable(f"unknown LLM_PROVIDER {self.provider!r}")

    def _call_gemini(self, prompt, system, temperature, json_schema, max_tokens) -> str:
        key = os.environ.get("GEMINI_API_KEY")
        if not key:
            raise LLMUnavailable("GEMINI_API_KEY is not set and no cached response exists for this call")
        from google import genai
        from google.genai import types

        # Extraction runs in parallel. Initialise once so competing clients are
        # not discarded (and their HTTP transports closed) during active calls.
        with self._client_lock:
            if self._client is None:
                self._client = genai.Client(api_key=key, http_options=types.HttpOptions(timeout=90000))
        cfg: dict[str, Any] = {"temperature": temperature, "max_output_tokens": max_tokens,
                               "automatic_function_calling": types.AutomaticFunctionCallingConfig(disable=True)}
        # These are constrained tagging/classification calls. Do not consume the
        # 512-token mapping output allowance with Gemini 2.5 Flash thought tokens.
        if self.model == "gemini-2.5-flash":
            cfg["thinking_config"] = types.ThinkingConfig(thinking_budget=0)
        elif self.model.startswith("gemini-3"):
            cfg["thinking_config"] = types.ThinkingConfig(thinking_level="low")
            # Gemini counts thoughts within the total output allowance. Reserve
            # room for reasoning without truncating the required JSON/tagged text.
            cfg["max_output_tokens"] = max_tokens + 4096
        if system:
            cfg["system_instruction"] = system
        if json_schema is not None:
            cfg["response_mime_type"] = "application/json"
        try:
            resp = self._client.models.generate_content(model=self.model, contents=prompt, config=types.GenerateContentConfig(**cfg))
        except genai.errors.APIError as exc:
            # Do not put provider payloads or credential-bearing request details in the UI.
            raise LLMUnavailable(f"Gemini request failed (HTTP {exc.code}). Check the API key, quota and model availability.") from None
        if not resp.text:
            raise LLMUnavailable("Gemini returned no text. Please retry the check.")
        return resp.text

    def _call_anthropic(self, prompt, system, temperature, json_schema, max_tokens) -> str:
        key = os.environ.get("ANTHROPIC_API_KEY")
        if not key:
            raise LLMUnavailable("ANTHROPIC_API_KEY is not set and no cached response exists for this call")
        import anthropic

        if self._client is None:
            self._client = anthropic.Anthropic(api_key=key)
        kwargs: dict[str, Any] = dict(model=self.model, max_tokens=max_tokens, temperature=temperature,
                                      messages=[{"role": "user", "content": prompt}])
        if system:
            kwargs["system"] = system
        msg = self._client.messages.create(**kwargs)
        return "".join(getattr(b, "text", "") for b in msg.content)

    def _call_claude_cli(self, prompt, system, json_schema) -> str:
        exe = shutil.which("claude")
        if not exe:
            raise LLMUnavailable("`claude` CLI not found on PATH and no cached response exists for this call")
        # Sandboxed: an empty working directory (so no CLAUDE.md, project memory or repo files are visible),
        # tools disabled, and a plain replacement system prompt. The model sees only the prompt we send.
        cmd = [exe, "-p", "--model", self.model, "--output-format", "json", "--no-session-persistence",
               "--tools", "", "--disallowedTools", "*", "--setting-sources", "", "--exclude-dynamic-system-prompt-sections",
               "--system-prompt", system or "You are a helpful assistant. Answer the user's request directly."]
        env = {k: v for k, v in os.environ.items() if k not in ("CLAUDECODE", "CLAUDE_CODE_ENTRYPOINT")}
        sandbox = Path(tempfile.gettempdir()) / "noticeguard-llm-sandbox"
        sandbox.mkdir(parents=True, exist_ok=True)
        proc = subprocess.run(cmd, input=prompt, capture_output=True, text=True, timeout=300, env=env, cwd=str(sandbox))
        if proc.returncode != 0:
            raise LLMUnavailable(f"claude CLI failed ({proc.returncode}): {proc.stderr[-500:]}")
        try:
            data = json.loads(proc.stdout)
            if isinstance(data, dict) and data.get("is_error"):
                raise LLMUnavailable(f"claude CLI error: {data.get('result')}")
            return data.get("result", "") if isinstance(data, dict) else str(data)
        except json.JSONDecodeError:
            return proc.stdout


_default: Optional[LLM] = None


def get_llm(use_cache: Optional[bool] = None) -> LLM:
    global _default
    if use_cache is not None:
        return LLM(use_cache=use_cache)
    if _default is None:
        _default = LLM()
    return _default
