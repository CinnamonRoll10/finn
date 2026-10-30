"""Model-backed enrichment of the filings that survive triage.

Three jobs, each on the cheap tier:
  * summarise()         one-line headline + "why it matters" for a batch of items
  * results_numbers()   headline numbers from a results filing (QoQ / YoY)
  * management_change() who the person is, from the Reg-30 disclosure itself
"""
from __future__ import annotations

import json
import re
from concurrent.futures import ThreadPoolExecutor

from .. import store
from ..llm import LLMUnavailable, get_llm
from datetime import datetime
from ..sources import docs, screener
from .classify import CATEGORIES

SUMMARY_SYSTEM = """You are FINN, a terse buy-side analyst's assistant for Indian equities.
You write for a portfolio manager who reads on a phone. One idea per line. No filler, no hedging, no adjectives.
Only use facts in the input. Never invent numbers. Answer with JSON only."""


def summarise(items: list[dict]) -> dict[str, dict]:
    """Batch headline/why/materiality for items. Returns {id: {...}}."""
    llm = get_llm()
    if not llm.available() or not items:
        return {}
    out: dict[str, dict] = {}
    todo = []
    for it in items:
        hit = store.get("item_summary", it["id"])
        if hit:
            out[it["id"]] = hit
        else:
            todo.append(it)
    batches = [todo[i:i + 12] for i in range(0, len(todo), 12)]

    def run(batch):
        payload = [{"id": it["id"], "company": it["company"], "nse_type": it["nse_type"],
                    "subject": it["subject"][:700], "rule_category": it["category"]} for it in batch]
        prompt = f"""For each exchange filing below, produce:
- headline: <= 12 words, specific (names, amounts, dates if present). Not a restatement of the filing type.
- why: <= 22 words on why an investor in this stock should or should not care. Say "Routine." if routine.
- category: one of {CATEGORIES}
- materiality: 1 (noise) to 5 (could move the stock)

Filings:
{json.dumps(payload, ensure_ascii=False)}

Return JSON: {{"items": [{{"id": "...", "headline": "...", "why": "...", "category": "...", "materiality": 3}}]}}"""
        try:
            res = llm.json(prompt, tier="fast", system=SUMMARY_SYSTEM, purpose="digest_summaries", max_tokens=3000)
            return {r["id"]: r for r in res.get("items", []) if "id" in r}
        except Exception:
            return {}

    with ThreadPoolExecutor(max_workers=4) as ex:
        for res in ex.map(run, batches):
            for k, v in res.items():
                store.put("item_summary", k, v)
            out.update(res)
    return out


def cached_summaries(items: list[dict]) -> dict[str, dict]:
    """Cache-only lookup (no model calls) - used for the instant digest."""
    out = {}
    for it in items:
        hit = store.get("item_summary", it["id"])
        if hit:
            out[it["id"]] = hit
    return out


RESULTS_SYSTEM = """You extract headline numbers from Indian quarterly results filings (SEBI LODR format).
Return JSON only. Use the CONSOLIDATED statement if present anywhere in the text (it often comes after the standalone one), else standalone. Numbers in the filing's own unit (usually Rs crore or Rs lakh - report the unit).
Columns in these filings are typically: current quarter | previous quarter | same quarter last year | half-year columns | full year.
If a value is absent, use null. Never guess."""


def results_numbers(item: dict) -> dict | None:
    """Headline numbers for a results filing: filing first, screener as fallback."""
    symbol = item["symbol"]
    out: dict = {"source": None}
    llm = get_llm()
    text = ""
    if item.get("pdf_url") and llm.available():
        try:
            text = docs.filing_text(item["pdf_url"], max_pages=16, max_chars=40_000)
        except Exception:
            text = ""
    if text and re.search(r"revenue|total income|profit", text, re.I):
        prompt = f"""Filing text (extracted from PDF, tables may be flattened):
<<<
{text}
>>>
Extract for the quarter being reported:
{{"period": "e.g. Q2 FY27 (quarter ended 30 Sep 2026)", "basis": "consolidated|standalone", "unit": "Rs crore|Rs lakh|Rs million",
 "current": {{"revenue": n, "ebitda": n, "pbt": n, "pat": n, "finance_cost": n, "depreciation": n, "exceptional": n}},
 "prev_quarter": {{same keys}}, "year_ago": {{same keys}},
 "notes": "<= 25 words on one-offs / exceptional items / anything that distorts comparison, else empty"}}
revenue = Revenue from operations (for banks: total income). ebitda only if the filing states it (else null; it will be derived). pat = profit after tax attributable to owners if shown, else net profit."""
        try:
            data = llm.json(prompt, tier="fast", system=RESULTS_SYSTEM, purpose="results_extract", max_tokens=1500)
            out = _finish_results(data)
            out["source"] = "filing"
        except Exception:
            out = {"source": None}
    nulls = sum(1 for r in out.get("rows", []) if r["value"] is None)
    if out.get("source") is None or nulls >= 2:
        try:
            scr = _results_from_screener(symbol, item.get("time"))
        except Exception:
            scr = None
        if scr:
            if out.get("source") is None:
                out = scr
            else:  # fill gaps from the standardised table
                by = {r["metric"]: r for r in scr["rows"]}
                for r in out["rows"]:
                    if r["value"] is None and by.get(r["metric"], {}).get("value") is not None:
                        r.update(by[r["metric"]])
                out["notes"] = (out.get("notes") or "") + " Gaps filled from screener.in."
        elif out.get("source") is None:
            return None
    out["why"] = results_why(out)
    return out


def results_why(res: dict) -> str | None:
    """One deterministic line from the numbers - no model needed."""
    by = {r["metric"]: r for r in res.get("rows", [])}
    rev, pat, ebitda = by.get("Revenue", {}), by.get("PAT", {}), by.get("EBITDA", {})
    parts = []
    if rev.get("yoy_pct") is not None:
        parts.append(f"Revenue {rev['yoy_pct']:+.0f}% YoY")
    if pat.get("yoy_pct") is not None:
        parts.append(f"PAT {pat['yoy_pct']:+.0f}% YoY")
    if rev.get("value") and ebitda.get("value") and rev.get("yoy_pct") is not None and ebitda.get("yoy_pct") is not None:
        gap = ebitda["yoy_pct"] - rev["yoy_pct"]
        parts.append("margins expanded" if gap > 2 else "margins compressed" if gap < -2 else "margins held")
    if not parts:
        return None
    line = ", ".join(parts) + "."
    if pat.get("qoq_pct") is not None and abs(pat["qoq_pct"]) >= 15:
        line += f" PAT {pat['qoq_pct']:+.0f}% QoQ."
    return line


def _expected_quarter(filing_time: str | None) -> str | None:
    """Filing in Oct-Nov -> 'Sep YYYY' quarter, etc."""
    if not filing_time:
        return None
    d = datetime.fromisoformat(filing_time)
    m = d.month
    if m in (1, 2):
        return f"Dec {d.year - 1}"
    if m in (4, 5, 6):
        return f"Mar {d.year}"
    if m in (7, 8, 9):
        return f"Jun {d.year}"
    if m in (10, 11, 12):
        return f"Sep {d.year}"
    return f"Dec {d.year - 1}" if m == 3 else None


def _derive_ebitda(block: dict | None) -> dict | None:
    if not block:
        return None
    b = {k: (float(v) if isinstance(v, (int, float)) else None) for k, v in block.items()}
    if b.get("ebitda") is None and b.get("pbt") is not None:
        fc, dep = b.get("finance_cost") or 0.0, b.get("depreciation") or 0.0
        if fc or dep:
            b["ebitda"] = b["pbt"] + fc + dep
            b["ebitda_derived"] = True
    return b


def _pct(a, b):
    if a is None or b in (None, 0):
        return None
    return round((a / b - 1) * 100, 1)


def _finish_results(data: dict) -> dict:
    cur, prev, ya = (_derive_ebitda(data.get(k)) for k in ("current", "prev_quarter", "year_ago"))
    rows = []
    for key, label in (("revenue", "Revenue"), ("ebitda", "EBITDA"), ("pbt", "PBT"), ("pat", "PAT")):
        c = (cur or {}).get(key)
        rows.append({
            "metric": label, "value": c,
            "qoq_pct": _pct(c, (prev or {}).get(key)),
            "yoy_pct": _pct(c, (ya or {}).get(key)),
            "derived": bool((cur or {}).get("ebitda_derived")) if key == "ebitda" else False,
        })
    unit = (data.get("unit") or "Rs crore").lower()
    # normalise everything to Rs crore for display consistency
    factor = 100 if "lakh" in unit else 10 if "million" in unit else 0.01 if "billion" in unit else 1
    if factor != 1:
        for r in rows:
            if r["value"] is not None:
                r["value"] = round(r["value"] / factor, 1)
    unit = "Rs crore"
    return {"period": data.get("period"), "basis": data.get("basis"), "unit": unit,
            "rows": rows, "notes": data.get("notes") or ""}


def _results_from_screener(symbol: str, filing_time: str | None = None) -> dict | None:
    c = screener.get_company(symbol, ttl=6 * 3600)
    q = c["tables"]["quarters"]
    cols = q["columns"]
    exp = _expected_quarter(filing_time)
    if exp and cols and cols[-1] != exp:
        return None  # screener has not caught up with this filing yet
    rows = []
    for key, label in (("revenue", "Revenue"), ("ebitda", "EBITDA"), ("pbt", "PBT"), ("pat", "PAT")):
        series = screener.row(q, key) or []
        cur = series[-1] if series else None
        prev = series[-2] if len(series) > 1 else None
        ya = series[-5] if len(series) > 4 else None
        rows.append({"metric": label, "value": cur, "qoq_pct": _pct(cur, prev), "yoy_pct": _pct(cur, ya),
                     "derived": key == "ebitda"})
    return {"period": f"Quarter {cols[-1]}" if cols else None, "basis": "consolidated" if c["consolidated"] else "standalone",
            "unit": "Rs crore", "rows": rows, "notes": "From screener.in standardised table (filing not parsed).",
            "source": "screener"}


MGMT_SYSTEM = """You read Indian stock-exchange disclosures about appointments/resignations of directors and key managerial personnel (SEBI LODR Reg 30, Schedule III).
These filings include a mandatory brief profile of the appointee. Extract it faithfully. JSON only. Never invent a background."""


def management_change(item: dict) -> dict | None:
    llm = get_llm()
    if not llm.available():
        return None
    text = ""
    if item.get("pdf_url"):
        try:
            text = docs.filing_text(item["pdf_url"], max_pages=6, max_chars=14_000)
        except Exception:
            text = ""
    prompt = f"""Subject: {item['subject'][:600]}
Filing text:
<<<
{text or '(no PDF text available - use the subject only)'}
>>>
Return JSON:
{{"changes": [{{"person": "name", "role": "position", "event": "appointed|resigned|retired|elevated|redesignated|ceased",
   "effective": "date or null", "reason": "<= 20 words, as stated, or null",
   "background": "<= 60 words: prior roles, employers, years, qualifications - only from the filing",
   "is_kmp": true/false (CEO/CFO/MD/WTD/Chairman/CS = true; independent/non-exec director = false)}}],
 "so_what": "<= 25 words: what an investor should take from this (continuity, succession, red flag, or routine)"}}"""
    try:
        data = llm.json(prompt, tier="fast", system=MGMT_SYSTEM, purpose="mgmt_change", max_tokens=1200)
        if isinstance(data, dict) and data.get("changes"):
            return data
    except Exception:
        pass
    return None
