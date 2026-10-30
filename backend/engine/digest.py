"""The Push side: windowed digest + triggered alerts.

Pipeline:  fetch filings -> classify (rules) -> triage -> model summaries for
the survivors -> deep enrichment for results & management changes -> tiers.

The digest is assembled instantly from caches (rules are free; summaries and
enrichments are cached per filing id), and any missing model work runs in a
background thread. The response carries `complete: false` until it lands, so
the UI shows triage immediately and fills in detail as it arrives.
"""
from __future__ import annotations

import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta

from .. import store
from ..config import PORTFOLIO, company_name
from ..llm import get_llm
from ..sources import nse, prices
from . import enrich
from .classify import classify, tier_for

MAX_DEEP = 16  # cap deep (PDF + model) enrichments per digest build
_inflight: set[str] = set()
_lock = threading.Lock()


def _window(settings, hours, start, end):
    hours = hours or settings.get("window_hours", 24)
    if start is None:
        end = date.today()
        cutoff = datetime.now() - timedelta(hours=hours)
        start = cutoff.date()
    else:
        cutoff = datetime.combine(start, datetime.min.time())
        end = end or date.today()
    return hours, start, end, cutoff, datetime.combine(end, datetime.max.time())


def build_digest(settings: dict, hours: int | None = None, start: date | None = None,
                 end: date | None = None, deep: bool = True) -> dict:
    hours, start, end, cutoff, end_dt = _window(settings, hours, start, end)
    symbols = settings["portfolio"]
    key = f"{','.join(sorted(symbols))}|{cutoff.isoformat(timespec='hours')}|{end}|{settings['thresholds']}|{sorted(settings.get('alert_categories', []))}"
    hit = store.get("digest", key, ttl=15 * 60)
    if hit and (hit.get("complete") or not deep):
        return hit

    raw, failed = nse.fetch_portfolio(symbols, start=start, end=end)
    items = [classify(dict(a)) for a in raw if cutoff <= datetime.fromisoformat(a["time"]) <= end_dt]
    items = _dedupe(items)
    out = _assemble(settings, items, failed, hours, cutoff, end_dt, key)
    if deep and not out["complete"] and get_llm().available():
        with _lock:
            if key not in _inflight:
                _inflight.add(key)
                threading.Thread(target=_fill, args=(settings, items, failed, hours, cutoff, end_dt, key), daemon=True).start()
    return out


def _assemble(settings, items, failed, hours, cutoff, end_dt, key) -> dict:
    t0 = time.time()
    muted = set(settings.get("muted_categories", []))
    alert_cats = set(settings.get("alert_categories", []))
    for it in items:
        s = it["rule_score"]
        if it["category"] in muted:
            s = min(s, 25)
        if it["category"] in alert_cats:
            s += 5
        it["score"] = s

    summaries = enrich.cached_summaries(items)
    pending = 0
    for it in items:
        s = summaries.get(it["id"])
        if s:
            it["headline"] = s.get("headline") or it["subject"][:120]
            it["why"] = s.get("why")
            if s.get("category") in {"results", "M&A", "management_change", "litigation", "fund_raise"} and it["category"] in ("press_release", "unclassified"):
                it["category"] = s["category"]
            mat = s.get("materiality")
            if isinstance(mat, (int, float)):
                it["score"] = round(0.55 * it["score"] + 0.45 * float(mat) * 20)
        else:
            it["headline"] = _fallback_headline(it)
            it["why"] = None
            if it["score"] >= 38:
                pending += 1
        it["tier"] = tier_for(it["score"])

    for kind, it in _deep_jobs(items):
        hit = store.get("item_enrich", it["id"])
        if hit is None:
            pending += 1
            continue
        if hit:  # {} means "tried, nothing usable"
            it["results" if kind == "results" else "people"] = hit
            if kind == "results" and hit.get("why"):
                it["why"] = hit["why"]
            if kind == "mgmt" and hit.get("so_what"):
                it["why"] = hit["so_what"]

    items.sort(key=lambda x: (-x["score"], x["time"]))
    try:
        tape = prices.market_tape(settings["portfolio"], settings["thresholds"])
    except Exception:
        tape = []
    for it in items:
        it["name"] = company_name(it["symbol"])
        it["sector"] = PORTFOLIO.get(it["symbol"], ("", "", ""))[1]
    out = {
        "window": {"from": cutoff.isoformat(timespec="minutes"), "to": end_dt.isoformat(timespec="minutes"), "hours": hours},
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "assemble_secs": round(time.time() - t0, 1),
        "complete": pending == 0 or not get_llm().available(),
        "pending": pending,
        "counts": {
            "total": len(items),
            "attention": sum(1 for i in items if i["tier"] == "attention"),
            "glance": sum(1 for i in items if i["tier"] == "glance"),
            "routine": sum(1 for i in items if i["tier"] == "routine"),
        },
        "items": items,
        "tape": tape,
        "alerts": _alerts(items, tape, alert_cats),
        "failed_symbols": failed,
    }
    store.put("digest", key, out)
    return out


def _fill(settings, items, failed, hours, cutoff, end_dt, key):
    """Background: run the model work, then re-assemble from caches."""
    try:
        survivors = [it for it in items if it["score"] >= 38 and store.get("item_summary", it["id"]) is None]
        enrich.summarise(survivors)
        # re-score with summaries so deep jobs pick the right tier
        fresh = [classify(dict(it)) for it in items]
        _assemble(settings, fresh, failed, hours, cutoff, end_dt, key)
        jobs = [(k, it) for k, it in _deep_jobs(fresh) if store.get("item_enrich", it["id"]) is None]

        def run(job):
            kind, it = job
            try:
                res = enrich.results_numbers(it) if kind == "results" else enrich.management_change(it)
            except Exception:
                res = None
            store.put("item_enrich", it["id"], res or {})

        with ThreadPoolExecutor(max_workers=4) as ex:
            list(ex.map(run, jobs))
        final = [classify(dict(it)) for it in items]
        _assemble(settings, final, failed, hours, cutoff, end_dt, key)
    finally:
        with _lock:
            _inflight.discard(key)


def _deep_jobs(items: list[dict]) -> list[tuple[str, dict]]:
    jobs = []
    for it in sorted(items, key=lambda x: -x["score"]):
        if len(jobs) >= MAX_DEEP:
            break
        if it["category"] == "results" and it.get("subtype") == "filed" and it.get("tier") == "attention" and it.get("pdf_url"):
            jobs.append(("results", it))
        elif it["category"] == "management_change" and it.get("tier") != "routine":
            jobs.append(("mgmt", it))
    return jobs


PERIOD_RE = re.compile(r"(quarter|half ?year|nine months|year)[^.]{0,30}?ended\s+([A-Za-z]+ \d{1,2},? \d{4}|\d{1,2}(?:st|nd|rd|th)? [A-Za-z]+,? \d{4}|\d{2}[./-]\d{2}[./-]\d{4})", re.I)


def _fallback_headline(it: dict) -> str:
    if it["category"] == "results" and it.get("subtype") in ("filed", "ad"):
        m = PERIOD_RE.search(it["subject"] or "")
        if m:
            return f"Results for the {m.group(1).lower()} ended {m.group(2)}" + (" (newspaper ad)" if it["subtype"] == "ad" else "")
    s = it["subject"] or it["nse_type"]
    s = s.replace(f"{it['company']} has informed the Exchange", "").strip(" :-")
    s = s.replace("regarding", "").replace("about", "").strip(" :-")
    return (s[:1].upper() + s[1:])[:140] if s else it["nse_type"]


def _dedupe(items: list[dict]) -> list[dict]:
    """Collapse duplicates: identical filings, and multiple results filings
    from one company on one day (outcome + results + press release)."""
    seen: dict[tuple, dict] = {}
    for it in items:
        k = (it["symbol"], it["nse_type"], (it["subject"] or "")[:80])
        if k in seen:
            seen[k]["duplicates"] = seen[k].get("duplicates", 0) + 1
        else:
            seen[k] = it
    out: list[dict] = []
    results_day: dict = {}
    for it in seen.values():
        if it["category"] == "results" and it.get("subtype") == "filed":
            rk = (it["symbol"], it["time"][:10])
            prev = results_day.get(rk)
            if prev is None:
                results_day[rk] = it
                out.append(it)
            else:
                # keep the one whose PDF is the actual results (bigger file)
                def size(x):
                    try:
                        return float((x.get("pdf_size") or "0").split()[0]) * (1024 if "MB" in (x.get("pdf_size") or "") else 1)
                    except Exception:
                        return 0
                if size(it) > size(prev):
                    out.remove(prev); prev["related"] = True
                    results_day[rk] = it; out.append(it)
                    it["duplicates"] = prev.get("duplicates", 0) + 1
                else:
                    prev["duplicates"] = prev.get("duplicates", 0) + 1
        else:
            out.append(it)
    return out


def _alerts(items: list[dict], tape: list[dict], alert_cats: set[str]) -> list[dict]:
    alerts = []
    for t in tape:
        if "price" in t["flags"]:
            alerts.append({
                "id": f"price-{t['symbol']}-{t['date']}", "kind": "price", "symbol": t["symbol"],
                "name": company_name(t["symbol"]), "time": t["date"],
                "title": f"{'+' if t['move_pct'] > 0 else ''}{t['move_pct']}% on the day",
                "detail": f"Close ₹{t['close']:,}. Volume {t['volume_x']}x its recent average.",
                "value": t["move_pct"],
            })
        if "volume" in t["flags"]:
            alerts.append({
                "id": f"vol-{t['symbol']}-{t['date']}", "kind": "volume", "symbol": t["symbol"],
                "name": company_name(t["symbol"]), "time": t["date"],
                "title": f"Volume {t['volume_x']}x average",
                "detail": f"{t['volume']:,} shares vs {t['avg_volume']:,} avg. Price {'+' if t['move_pct'] > 0 else ''}{t['move_pct']}%.",
                "value": t["volume_x"],
            })
    for it in items:
        if it["category"] in alert_cats and it["tier"] == "attention":
            alerts.append({
                "id": f"filing-{it['id']}", "kind": "filing", "symbol": it["symbol"],
                "name": company_name(it["symbol"]), "time": it["time"],
                "category": it["category"], "title": it["headline"], "detail": it.get("why"),
                "item_id": it["id"],
            })
    alerts.sort(key=lambda a: a["time"], reverse=True)
    return alerts
