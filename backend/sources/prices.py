"""End-of-day prices & volumes via yfinance, plus the anomaly detector.

An "unusual move" is user-defined: |close-to-close %| above a threshold, or
volume above N x the trailing average. Both come from settings.
"""
from __future__ import annotations

import warnings
from datetime import date

import pandas as pd

from .. import store

warnings.filterwarnings("ignore")


def _download(symbols: list[str]) -> dict[str, list[dict]]:
    import yfinance as yf

    tickers = [f"{s}.NS" for s in symbols]
    df = yf.download(tickers, period="4mo", interval="1d", group_by="ticker",
                     auto_adjust=False, progress=False, threads=True)
    out: dict[str, list[dict]] = {}
    for sym, tk in zip(symbols, tickers):
        try:
            sub = df[tk] if len(tickers) > 1 else df
            sub = sub.dropna(subset=["Close"])
            rows = []
            for idx, r in sub.iterrows():
                rows.append({
                    "d": idx.strftime("%Y-%m-%d"),
                    "c": round(float(r["Close"]), 2),
                    "v": int(r["Volume"]) if not pd.isna(r["Volume"]) else 0,
                })
            out[sym] = rows
        except Exception:
            out[sym] = []
    return out


def get_history(symbols: list[str]) -> dict[str, list[dict]]:
    """Daily closes/volumes per symbol, cached for an hour per trading day."""
    symbols = sorted(set(symbols))
    key = f"{date.today()}|{','.join(symbols)}"
    return store.cached("prices", key, 3600, lambda: _download(symbols))


def summarise(symbol: str, rows: list[dict], thresholds: dict) -> dict | None:
    if len(rows) < 2:
        return None
    look = int(thresholds.get("lookback_days", 20))
    last, prev = rows[-1], rows[-2]
    hist = rows[-(look + 1):-1]
    avg_vol = sum(r["v"] for r in hist) / max(1, len(hist))
    move = (last["c"] / prev["c"] - 1) * 100 if prev["c"] else 0.0
    vol_x = last["v"] / avg_vol if avg_vol else 0.0
    wk = rows[-6]["c"] if len(rows) >= 6 else rows[0]["c"]
    mo = rows[-22]["c"] if len(rows) >= 22 else rows[0]["c"]
    s = {
        "symbol": symbol,
        "date": last["d"],
        "close": last["c"],
        "move_pct": round(move, 2),
        "volume": last["v"],
        "avg_volume": int(avg_vol),
        "volume_x": round(vol_x, 2),
        "ret_1w_pct": round((last["c"] / wk - 1) * 100, 2) if wk else None,
        "ret_1m_pct": round((last["c"] / mo - 1) * 100, 2) if mo else None,
        "spark": [r["c"] for r in rows[-30:]],
        "flags": [],
    }
    if abs(move) >= float(thresholds.get("price_move_pct", 4.0)):
        s["flags"].append("price")
    if vol_x >= float(thresholds.get("volume_multiple", 2.0)) and last["v"] > 0:
        s["flags"].append("volume")
    return s


def market_tape(symbols: list[str], thresholds: dict) -> list[dict]:
    hist = get_history(symbols)
    tape = []
    for sym in symbols:
        s = summarise(sym, hist.get(sym, []), thresholds)
        if s:
            tape.append(s)
    return tape
