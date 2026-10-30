"""NSE corporate announcements.

NSE's JSON API needs the cookies its homepage sets, plus browser-like headers.
We keep one session, refresh cookies when a call fails, and cache each
(symbol, from, to) query for 15 minutes so the digest can be rebuilt cheaply.
"""
from __future__ import annotations

import threading
import time
from datetime import date, datetime, timedelta

import requests

from .. import store
from ..config import USER_AGENT, company_name

BASE = "https://www.nseindia.com"
HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": f"{BASE}/companies-listing/corporate-filings-announcements",
}

_session: requests.Session | None = None
_cookie_ts = 0.0
_lock = threading.Lock()


def _get_session(force: bool = False) -> requests.Session:
    global _session, _cookie_ts
    with _lock:
        if _session is None or force or time.time() - _cookie_ts > 600:
            s = requests.Session()
            s.headers.update(HEADERS)
            try:
                s.get(BASE + "/", timeout=20)
            except requests.RequestException:
                pass
            _session, _cookie_ts = s, time.time()
        return _session


def _parse_dt(s: str) -> datetime:
    for fmt in ("%d-%b-%Y %H:%M:%S", "%d-%b-%Y"):
        try:
            return datetime.strptime(s.strip(), fmt)
        except ValueError:
            continue
    return datetime.now()


def fetch_announcements(symbol: str, start: date, end: date) -> list[dict]:
    """Return normalised announcements for one symbol between two dates."""
    key = f"{symbol}|{start}|{end}"
    ttl = 15 * 60 if end >= date.today() else None  # history never changes

    def _fetch():
        last_err = None
        for attempt in range(3):
            s = _get_session(force=attempt > 0)
            try:
                r = s.get(
                    BASE + "/api/corporate-announcements",
                    params={
                        "index": "equities", "symbol": symbol,
                        "from_date": start.strftime("%d-%m-%Y"),
                        "to_date": end.strftime("%d-%m-%Y"),
                    },
                    timeout=25,
                )
                if r.status_code == 200 and r.text.strip():
                    data = r.json()
                    if isinstance(data, list):
                        return [_normalise(symbol, a) for a in data]
                last_err = f"status {r.status_code}"
            except (requests.RequestException, ValueError) as e:
                last_err = str(e)
            time.sleep(0.8 * (attempt + 1))
        raise RuntimeError(f"NSE announcements failed for {symbol}: {last_err}")

    return store.cached("nse_ann", key, ttl, _fetch)


def _normalise(symbol: str, a: dict) -> dict:
    dt = _parse_dt(a.get("an_dt") or a.get("exchdisstime") or "")
    return {
        "id": str(a.get("seq_id") or f"{symbol}-{a.get('dt')}"),
        "symbol": symbol,
        "company": a.get("sm_name") or company_name(symbol),
        "industry": a.get("smIndustry"),
        "time": dt.isoformat(timespec="seconds"),
        "nse_type": (a.get("desc") or "").strip(),
        "subject": (a.get("attchmntText") or "").strip(),
        "pdf_url": a.get("attchmntFile") or None,
        "pdf_size": a.get("attFileSize"),
    }


def fetch_portfolio(symbols: list[str], hours: int | None = None,
                    start: date | None = None, end: date | None = None) -> tuple[list[dict], list[str]]:
    """Fetch announcements for many symbols. Returns (items, failed_symbols)."""
    if start is None or end is None:
        end = date.today()
        start = (datetime.now() - timedelta(hours=hours or 24)).date()
    items, failed = [], []
    for sym in symbols:
        try:
            items.extend(fetch_announcements(sym, start, end))
        except Exception:
            failed.append(sym)
    items.sort(key=lambda x: x["time"], reverse=True)
    return items, failed
