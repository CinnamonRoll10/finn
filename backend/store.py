"""Tiny on-disk cache + settings store.

Everything expensive (NSE calls, PDFs, LLM outputs) is cached as JSON or raw
bytes under data/cache/<namespace>/<key>. A TTL of None means "forever" —
that is what we use for LLM extractions keyed on document content, since the
same transcript never needs to be read twice.
"""
from __future__ import annotations

import hashlib
import json
import threading
import time
from pathlib import Path
from typing import Any, Callable

from .config import CACHE_DIR, DEFAULT_SETTINGS, SETTINGS_FILE

_lock = threading.Lock()


def _path(namespace: str, key: str, ext: str = "json") -> Path:
    safe = hashlib.sha1(key.encode()).hexdigest()[:20]
    d = CACHE_DIR / namespace
    d.mkdir(parents=True, exist_ok=True)
    return d / f"{safe}.{ext}"


def get(namespace: str, key: str, ttl: float | None = None) -> Any | None:
    p = _path(namespace, key)
    if not p.exists():
        return None
    if ttl is not None and time.time() - p.stat().st_mtime > ttl:
        return None
    try:
        return json.loads(p.read_text())
    except Exception:
        return None


def put(namespace: str, key: str, value: Any) -> Any:
    p = _path(namespace, key)
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(value, ensure_ascii=False, default=str))
    tmp.replace(p)
    return value


def cached(namespace: str, key: str, ttl: float | None, fn: Callable[[], Any]) -> Any:
    hit = get(namespace, key, ttl)
    if hit is not None:
        return hit
    return put(namespace, key, fn())


def get_bytes(namespace: str, key: str) -> bytes | None:
    p = _path(namespace, key, "bin")
    return p.read_bytes() if p.exists() else None


def put_bytes(namespace: str, key: str, data: bytes) -> bytes:
    p = _path(namespace, key, "bin")
    p.write_bytes(data)
    return data


# ---------------------------------------------------------------- settings

def load_settings() -> dict:
    with _lock:
        if SETTINGS_FILE.exists():
            try:
                saved = json.loads(SETTINGS_FILE.read_text())
                merged = json.loads(json.dumps(DEFAULT_SETTINGS))
                merged.update({k: v for k, v in saved.items() if k != "thresholds"})
                merged["thresholds"].update(saved.get("thresholds", {}))
                return merged
            except Exception:
                pass
        return json.loads(json.dumps(DEFAULT_SETTINGS))


def save_settings(settings: dict) -> dict:
    with _lock:
        SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
        SETTINGS_FILE.write_text(json.dumps(settings, indent=2))
    return settings
