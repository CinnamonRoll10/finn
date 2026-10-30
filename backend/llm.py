"""Model router with two tiers and a content-addressed cache.

Tiers
-----
fast   bulk extraction & classification (cheap model: Haiku / Gemini Flash)
smart  synthesis & reasoning (strong model: Opus / Gemini Pro)

Providers are picked automatically from what is configured:
    ANTHROPIC_API_KEY  -> Anthropic SDK (claude-haiku-5-5 / claude-opus-5-5)
    GEMINI_API_KEY     -> google-genai (flash / pro)
    `claude` CLI       -> Claude Code CLI on a subscription (no API spend)
    nothing            -> "none": callers fall back to rule-based output

Every call is cached on sha1(provider-tier + system + prompt), so re-reading a
transcript or re-classifying the same filing is free. A usage ledger is kept
for the /api/usage endpoint so the product can show what it cost.
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
from pathlib import Path

from . import store
from .config import DATA_DIR

# USD per 1M tokens (input, output) - used for the ledger only.
PRICES = {
    "claude-haiku-5-5": (0.10, 0.50),
    "claude-sonnet-5-5": (2.00, 10.00),
    "claude-opus-5-5": (4.00, 20.00),
    "gemini-flash-latest": (0.30, 2.50),
    "gemini-pro-latest": (1.25, 10.00),
}

MODELS = {
    "anthropic": {
        "fast": os.getenv("FINN_FAST_MODEL", "claude-haiku-5-5"),
        "smart": os.getenv("FINN_SMART_MODEL", "claude-opus-5-5"),
    },
    "gemini": {
        "fast": os.getenv("FINN_FAST_MODEL", "gemini-flash-latest"),
        "smart": os.getenv("FINN_SMART_MODEL", "gemini-pro-latest"),
    },
    # Claude Code CLI aliases; priced as the API model they map to.
    "claude-cli": {"fast": "haiku", "smart": "opus"},
}
CLI_PRICE_ALIAS = {"haiku": "claude-haiku-5-5", "sonnet": "claude-sonnet-5-5", "opus": "claude-opus-5-5"}

LEDGER_FILE = DATA_DIR / "usage.jsonl"
_ledger_lock = threading.Lock()


def detect_provider() -> str:
    forced = os.getenv("FINN_LLM_PROVIDER", "auto").lower()
    if forced != "auto":
        return forced
    if os.getenv("ANTHROPIC_API_KEY"):
        return "anthropic"
    if os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"):
        return "gemini"
    if shutil.which(os.getenv("CLAUDE_BIN", "claude")):
        return "claude-cli"
    return "none"


class LLMUnavailable(RuntimeError):
    pass


class LLM:
    def __init__(self) -> None:
        self.provider = detect_provider()
        self._anthropic = None
        self._gemini = None

    # ------------------------------------------------------------ public
    def available(self) -> bool:
        return self.provider != "none"

    def model_for(self, tier: str) -> str:
        return MODELS.get(self.provider, {}).get(tier, "none")

    def complete(
        self,
        prompt: str,
        *,
        tier: str = "fast",
        system: str | None = None,
        max_tokens: int = 4000,
        purpose: str = "",
        use_cache: bool = True,
    ) -> str:
        if not self.available():
            raise LLMUnavailable("no LLM provider configured")
        model = self.model_for(tier)
        key = hashlib.sha1(f"{self.provider}|{model}|{system or ''}|{prompt}".encode()).hexdigest()
        if use_cache:
            hit = store.get("llm", key)
            if hit is not None:
                self._log(model, tier, purpose, 0, 0, cached=True)
                return hit["text"]
        t0 = time.time()
        if self.provider == "anthropic":
            text, tin, tout = self._call_anthropic(model, tier, system, prompt, max_tokens)
        elif self.provider == "gemini":
            text, tin, tout = self._call_gemini(model, system, prompt, max_tokens)
        elif self.provider == "claude-cli":
            text, tin, tout = self._call_cli(model, system, prompt)
        else:
            raise LLMUnavailable(self.provider)
        self._log(model, tier, purpose, tin, tout, cached=False, secs=time.time() - t0)
        store.put("llm", key, {"text": text, "model": model, "ts": time.time()})
        return text

    def json(self, prompt: str, retries: int = 2, **kw) -> dict | list:
        """complete() + tolerant JSON parsing (handles code fences / prose).
        A malformed answer is retried once or twice without the cache, with the
        model told exactly where its previous output broke."""
        text = self.complete(prompt, **kw)
        for attempt in range(retries + 1):
            try:
                return parse_json(text)
            except (ValueError, json.JSONDecodeError) as e:
                if attempt == retries:
                    raise
                kw["use_cache"] = False
                text = self.complete(
                    prompt + f"\n\nYour previous answer was not valid JSON ({str(e)[:80]}). "
                    "Return the same content as strictly valid JSON only: double quotes, no trailing commas, "
                    "escape quotes inside strings, no commentary.",
                    **kw,
                )

    # ------------------------------------------------------------ providers
    def _call_anthropic(self, model, tier, system, prompt, max_tokens):
        import anthropic

        if self._anthropic is None:
            self._anthropic = anthropic.Anthropic()
        kwargs = dict(
            model=model,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
            output_config={"effort": "low" if tier == "fast" else "high"},
        )
        if system:
            kwargs["system"] = system
        resp = self._anthropic.messages.create(**kwargs)
        if resp.stop_reason == "refusal":
            raise LLMUnavailable("model refused the request")
        text = "".join(b.text for b in resp.content if b.type == "text")
        return text, resp.usage.input_tokens, resp.usage.output_tokens

    def _call_gemini(self, model, system, prompt, max_tokens):
        from google import genai
        from google.genai import types

        if self._gemini is None:
            self._gemini = genai.Client(api_key=os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"))
        cfg = types.GenerateContentConfig(system_instruction=system, max_output_tokens=max_tokens)
        resp = self._gemini.models.generate_content(model=model, contents=prompt, config=cfg)
        um = resp.usage_metadata
        return resp.text or "", int(um.prompt_token_count or 0), int(um.candidates_token_count or 0)

    def _call_cli(self, model, system, prompt):
        """Claude Code CLI in print mode. Runs in an empty temp dir so no
        project instructions leak in, with all tools disabled."""
        full = prompt
        with tempfile.TemporaryDirectory() as d:
            cmd = [os.getenv("CLAUDE_BIN", "claude"), "-p", "--model", model,
                   "--output-format", "text", "--tools", "", "--no-session-persistence"]
            if system:
                cmd += ["--system-prompt", system]
            proc = subprocess.run(cmd, input=full, capture_output=True, text=True, cwd=d, timeout=600)
        if proc.returncode != 0:
            raise RuntimeError(f"claude cli failed: {proc.stderr[-500:]}")
        # no token accounting from the CLI: estimate at ~4 chars/token
        return proc.stdout.strip(), len(full) // 4, len(proc.stdout) // 4

    # ------------------------------------------------------------ ledger
    def _log(self, model, tier, purpose, tin, tout, cached, secs=0.0):
        price = PRICES.get(CLI_PRICE_ALIAS.get(model, model), (0, 0))
        cost = (tin * price[0] + tout * price[1]) / 1e6
        row = {
            "ts": time.time(), "provider": self.provider, "model": model, "tier": tier,
            "purpose": purpose, "in": tin, "out": tout, "usd": round(cost, 5),
            "cached": cached, "secs": round(secs, 1),
            "estimated": self.provider == "claude-cli",
        }
        with _ledger_lock:
            LEDGER_FILE.parent.mkdir(parents=True, exist_ok=True)
            with LEDGER_FILE.open("a") as f:
                f.write(json.dumps(row) + "\n")


def usage_summary() -> dict:
    rows = []
    if LEDGER_FILE.exists():
        for line in LEDGER_FILE.read_text().splitlines():
            try:
                rows.append(json.loads(line))
            except Exception:
                pass
    by_model: dict[str, dict] = {}
    for r in rows:
        m = by_model.setdefault(r["model"], {"calls": 0, "cached": 0, "in": 0, "out": 0, "usd": 0.0})
        m["calls"] += 1
        m["cached"] += 1 if r.get("cached") else 0
        m["in"] += r["in"]
        m["out"] += r["out"]
        m["usd"] += r["usd"]
    for m in by_model.values():
        m["usd"] = round(m["usd"], 4)
    return {
        "provider": detect_provider(),
        "calls": len(rows),
        "cache_hits": sum(1 for r in rows if r.get("cached")),
        "usd": round(sum(r["usd"] for r in rows), 4),
        "estimated": any(r.get("estimated") for r in rows),
        "by_model": by_model,
        "by_purpose": _group(rows, "purpose"),
    }


def _group(rows, key):
    out: dict[str, dict] = {}
    for r in rows:
        g = out.setdefault(r.get(key) or "other", {"calls": 0, "usd": 0.0})
        g["calls"] += 1
        g["usd"] = round(g["usd"] + r["usd"], 4)
    return out


def parse_json(text: str):
    text = text.strip()
    m = re.search(r"```(?:json)?\s*(.*?)```", text, re.S)
    if m:
        text = m.group(1).strip()
    try:
        return json.loads(text)
    except Exception:
        pass
    start = min([i for i in (text.find("{"), text.find("[")) if i >= 0] or [0])
    end = max(text.rfind("}"), text.rfind("]"))
    if end > start:
        return json.loads(text[start:end + 1])
    raise ValueError(f"no JSON in model output: {text[:200]}")


_llm: LLM | None = None


def get_llm() -> LLM:
    global _llm
    if _llm is None:
        _llm = LLM()
    return _llm
