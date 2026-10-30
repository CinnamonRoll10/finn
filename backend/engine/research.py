"""The Pull side: on-demand research grounded in primary sources only.

Inputs per company (all primary):
  * screener.in standardised financials  (numbers)
  * the last N concall transcripts        (what management said)
  * the latest annual report (opening + MD&A pages)

Routing: every document is read once by the cheap tier into a compact JSON
extraction (cached forever on the document URL). The strong tier then sees
only those extractions plus a deterministic numbers block computed in Python
- so the expensive model never reads a 500-page PDF, never does arithmetic,
and never sees broker notes or news.

Status is tracked per symbol so the UI can show progress while a build runs.
"""
from __future__ import annotations

import json
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

from .. import store
from ..llm import LLMUnavailable, get_llm
from ..sources import docs, screener

N_TRANSCRIPTS = 4
_status: dict[str, dict] = {}
_locks: dict[str, threading.Lock] = {}
_glock = threading.Lock()


def status(symbol: str) -> dict:
    return _status.get(symbol.upper(), {"state": "idle"})


def get_cached(symbol: str) -> dict | None:
    return store.get("research", symbol.upper())


def _set(symbol: str, **kw):
    cur = _status.setdefault(symbol, {"state": "idle"})
    cur.update(kw)
    cur["updated"] = time.time()


# ------------------------------------------------------------------ numbers

def _series(table, key):
    s = screener.row(table, key) if table else None
    return s or []


def _cagr(series, years):
    vals = [v for v in series if v is not None]
    if len(series) < years + 1:
        return None
    a, b = series[-1 - years], series[-1]
    if not a or not b or a <= 0 or b <= 0:
        return None
    return round(((b / a) ** (1 / years) - 1) * 100, 1)


def compute_facts(c: dict) -> dict:
    """Deterministic metrics from the screener tables (no model involved)."""
    t = c["tables"]
    pl, bs, cf, ra, q = t["profit-loss"], t["balance-sheet"], t["cash-flow"], t["ratios"], t["quarters"]
    years = [col for col in (pl["columns"] if pl else []) if col != "TTM"]
    ny = len(years)
    rev = _series(pl, "revenue")[:ny]
    pat = _series(pl, "pat")[:ny]
    opm = _series(pl, "opm")[:ny]
    ebitda = _series(pl, "ebitda")[:ny]
    facts: dict = {"years": years}
    facts["annual"] = {"revenue": rev, "ebitda": ebitda, "pat": pat, "opm_pct": opm}
    facts["revenue_cagr_3y"] = _cagr(rev, 3)
    facts["revenue_cagr_5y"] = _cagr(rev, 5)
    facts["pat_cagr_3y"] = _cagr(pat, 3)
    facts["pat_cagr_5y"] = _cagr(pat, 5)
    if opm and opm[-1] is not None and len([o for o in opm[-4:-1] if o is not None]) == 3:
        facts["opm_latest"] = opm[-1]
        facts["opm_3y_avg_prior"] = round(sum(opm[-4:-1]) / 3, 1)
    if bs:
        eq = _series(bs, "Equity Capital"); res = _series(bs, "Reserves"); debt = _series(bs, "Borrowings")
        if eq and res and debt:
            nw = [(e or 0) + (r or 0) for e, r in zip(eq, res)]
            facts["balance"] = {"years": bs["columns"], "borrowings": debt, "net_worth": nw,
                                "de": [round(d / n, 2) if n else None for d, n in zip(debt, nw)]}
            facts["de_latest"] = facts["balance"]["de"][-1]
            facts["de_3y_ago"] = facts["balance"]["de"][-4] if len(nw) >= 4 else None
    if cf:
        cfo = _series(cf, "Cash from Operating Activity"); fcf = _series(cf, "Free Cash Flow")
        facts["cash"] = {"years": cf["columns"], "cfo": cfo, "fcf": fcf}
        pat_a = pat[-len(cfo):] if cfo else []
        pairs = [(a, b) for a, b in zip(cfo[-3:], pat_a[-3:]) if a is not None and b]
        if pairs:
            facts["cfo_to_pat_3y"] = round(sum(a for a, _ in pairs) / sum(b for _, b in pairs), 2)
        if fcf:
            facts["fcf_last3"] = fcf[-3:]
    if ra:
        for k, lab in (("ROCE %", "roce"), ("Cash Conversion Cycle", "ccc"), ("Working Capital Days", "wc_days"),
                       ("Debtor Days", "debtor_days"), ("Inventory Days", "inventory_days")):
            s = _series(ra, k)
            if s:
                facts[lab] = {"latest": s[-1], "3y_ago": s[-4] if len(s) >= 4 else None, "series": s[-6:]}
        facts["ratio_years"] = ra["columns"][-6:]
    if q:
        cols = q["columns"]
        qrev, qebitda, qpat, qopm = (_series(q, k) for k in ("revenue", "ebitda", "pat", "opm"))
        rows = []
        for i, col in enumerate(cols):
            def yoy(s):
                return round((s[i] / s[i - 4] - 1) * 100, 1) if i >= 4 and s[i] is not None and s[i - 4] else None
            def qoq(s):
                return round((s[i] / s[i - 1] - 1) * 100, 1) if i >= 1 and s[i] is not None and s[i - 1] else None
            rows.append({"q": col, "revenue": qrev[i] if i < len(qrev) else None, "ebitda": qebitda[i] if i < len(qebitda) else None,
                         "pat": qpat[i] if i < len(qpat) else None, "opm_pct": qopm[i] if i < len(qopm) else None,
                         "rev_yoy": yoy(qrev) if qrev else None, "pat_yoy": yoy(qpat) if qpat else None,
                         "rev_qoq": qoq(qrev) if qrev else None})
        facts["quarters"] = rows[-8:]
    facts["top"] = c.get("top", {})
    return facts


def facts_text(f: dict) -> str:
    """Compact text block of numbers for the model."""
    lines = []
    yrs = f.get("years", [])
    a = f.get("annual", {})
    lines.append("ANNUAL (Rs crore; FY ends March): year | revenue | EBITDA | PAT | OPM%")
    for i, y in enumerate(yrs[-6:]):
        j = len(yrs) - 6 + i if len(yrs) >= 6 else i
        def g(k):
            s = a.get(k, []); return s[j] if j < len(s) and s[j] is not None else "-"
        lines.append(f"{y} | {g('revenue')} | {g('ebitda')} | {g('pat')} | {g('opm_pct')}")
    lines.append(f"Revenue CAGR 3y/5y: {f.get('revenue_cagr_3y')}% / {f.get('revenue_cagr_5y')}%; PAT CAGR 3y/5y: {f.get('pat_cagr_3y')}% / {f.get('pat_cagr_5y')}%")
    if "opm_latest" in f:
        lines.append(f"OPM latest {f['opm_latest']}% vs prior-3y avg {f['opm_3y_avg_prior']}%")
    if f.get("balance"):
        b = f["balance"]
        lines.append("BALANCE: year | borrowings | net worth | D/E")
        for y, d, n, de in list(zip(b["years"], b["borrowings"], b["net_worth"], b["de"]))[-4:]:
            lines.append(f"{y} | {d} | {n} | {de}")
    if f.get("cash"):
        c = f["cash"]
        lines.append("CASH: year | CFO | FCF")
        for y, o, fc in list(zip(c["years"], c["cfo"], c["fcf"]))[-4:]:
            lines.append(f"{y} | {o} | {fc}")
        lines.append(f"CFO/PAT last 3y: {f.get('cfo_to_pat_3y')}")
    for k, lab in (("roce", "ROCE %"), ("ccc", "Cash conversion cycle (days)"), ("wc_days", "Working capital days"), ("debtor_days", "Debtor days"), ("inventory_days", "Inventory days")):
        if f.get(k):
            lines.append(f"{lab}: {f[k]['series']} (years {f.get('ratio_years')})")
    if f.get("quarters"):
        lines.append("QUARTERS: quarter | revenue | EBITDA | PAT | OPM% | rev YoY% | PAT YoY% | rev QoQ%")
        for r in f["quarters"]:
            lines.append(f"{r['q']} | {r['revenue']} | {r['ebitda']} | {r['pat']} | {r['opm_pct']} | {r['rev_yoy']} | {r['pat_yoy']} | {r['rev_qoq']}")
    top = f.get("top", {})
    if top:
        lines.append("MARKET: " + "; ".join(f"{k} {v}" for k, v in top.items()))
    return "\n".join(lines)


# --------------------------------------------------------------- extraction

TRANSCRIPT_SYSTEM = """You are an equity analyst reading an earnings-call transcript. Extract what management committed to and claimed, verbatim where possible.
Only use the transcript. Quotes must be exact substrings (<= 25 words). JSON only."""


def extract_transcript(url: str, label: str) -> dict:
    key = f"tx|{url}"
    hit = store.get("extract", key)
    if hit:
        return hit
    text = docs.transcript_text(url)
    llm = get_llm()
    prompt = f"""Transcript ({label}):
<<<
{text}
>>>
Return JSON:
{{"quarter": "e.g. Q1 FY27", "call_date": "if stated",
 "guidance": [{{"metric": "revenue growth|margin|capex|volume|order book|other", "statement": "<= 30 words, specific numbers", "horizon": "FY27|next quarter|medium term", "quote": "exact <= 25 words"}}],
 "delivered": [{{"metric": "...", "statement": "<= 25 words: what management says was achieved this quarter, with numbers"}}],
 "themes": ["<= 6 items, <= 15 words each: demand, pricing, new businesses, cost actions"],
 "risks": ["<= 4 items, risks management or analysts raised"],
 "analyst_pushback": ["<= 4 items: what analysts pressed on and how management responded, <= 25 words each"],
 "tone": "confident|cautious|defensive|mixed", "tone_evidence": "<= 20 words"}}
Keep guidance to explicit forward-looking commitments (numbers, ranges, directions). Max 8 guidance items."""
    data = llm.json(prompt, tier="fast", system=TRANSCRIPT_SYSTEM, purpose="transcript_extract", max_tokens=3500)
    data["label"] = label
    data["url"] = url
    store.put("extract", key, data)
    return data


AR_SYSTEM = """You are an equity analyst reading an annual report (opening pages + Management Discussion & Analysis). Only use the text. JSON only."""


def extract_annual_report(url: str, year: int) -> dict:
    key = f"ar|{url}"
    hit = store.get("extract", key)
    if hit:
        return hit
    ex = docs.annual_report_excerpt(url)
    llm = get_llm()
    prompt = f"""Annual Report FY{year} - opening pages:
<<<
{ex['opening']}
>>>
Management Discussion & Analysis:
<<<
{ex['mda'] or '(MD&A not located)'}
>>>
Return JSON:
{{"business": "<= 70 words: what the company does, for whom, how it makes money",
 "segments": [{{"name": "...", "share": "% of revenue if stated else null", "comment": "<= 15 words"}}],
 "revenue_mix": "<= 30 words: geography / product / customer mix if stated",
 "strategy": ["<= 5 items, <= 15 words"],
 "outlook": "<= 40 words: management's stated outlook",
 "capex_plans": "<= 30 words or null",
 "risks": ["<= 4 items from the risk discussion"],
 "flags": "<= 30 words: contingent liabilities, auditor qualifications, related-party items if mentioned, else null"}}"""
    data = llm.json(prompt, tier="fast", system=AR_SYSTEM, purpose="ar_extract", max_tokens=2000)
    data["year"] = year
    data["url"] = url
    data["mda_page"] = ex.get("mda_page")
    data["pages"] = ex.get("pages")
    store.put("extract", key, data)
    return data


# --------------------------------------------------------------- synthesis

SYNTH_SYSTEM = """You are FINN, a buy-side analyst writing for a portfolio manager on a phone.
Rules:
- Use ONLY the material provided (numbers block, transcript extractions, annual-report extraction). No outside knowledge of the company, no news, no broker views. If the material is silent, say "not disclosed".
- Every bullet <= 24 words, concrete, with numbers where available. No adjectives without a number behind them.
- Tag each bullet with its source in square brackets: [Numbers], [Q1FY27 call], [AR FY26].
- Analyse, don't summarise: say what the numbers imply, where story and numbers disagree.
JSON only."""


def synthesise(c: dict, facts: dict, transcripts: list[dict], ar: dict | None) -> dict:
    llm = get_llm()
    tx_json = json.dumps([{k: v for k, v in t.items() if k != "url"} for t in transcripts], ensure_ascii=False)
    prompt = f"""Company: {c['name']} ({c['symbol']}). Basis: {'consolidated' if c['consolidated'] else 'standalone'}.
screener.in blurb: {c.get('about', '')[:500]}

NUMBERS:
{facts_text(facts)}

TRANSCRIPT EXTRACTIONS (newest first):
{tx_json}

ANNUAL REPORT EXTRACTION:
{json.dumps(ar, ensure_ascii=False) if ar else 'none'}

Produce JSON with:
{{"one_liner": "<= 20 words: what this company is and the single thing that matters now",
 "business": ["3-4 bullets: what it does, segments, revenue mix"],
 "financial_snapshot": ["3-4 bullets: latest quarter & TTM headline numbers, margins, ROCE/ROE, valuation from MARKET line"],
 "trajectory": ["3-4 bullets: multi-year direction - what is growing, what is compressing, with CAGRs"],
 "balance_sheet": ["3 bullets: debt, leverage trend, working-capital cycle, funding"],
 "cash_quality": ["3 bullets: CFO vs PAT, FCF trend, do profits turn into cash"],
 "narrative_vs_numbers": ["3-4 bullets: where management's story and the financials agree or diverge"],
 "guidance": ["3-5 bullets: explicit guidance on growth, margins, capex, with the call it came from"],
 "ledger": [{{"period": "quarter the promise was about", "promised": "<= 20 words, with the call it came from", "delivered": "<= 20 words with the actual number from NUMBERS", "verdict": "met|missed|partial|pending|unverifiable"}}],
 "bull": ["3 bullets"], "bear": ["3 bullets"],
 "questions": ["4 sharp questions an investor should ask management next, <= 15 words each"]}}
The ledger is the most important output: for each explicit guidance item in the transcripts, find the later quarter it applied to in NUMBERS and judge it. 4-8 rows. If guidance is qualitative, judge direction. Mark "pending" if the quarter has not reported yet."""
    return llm.json(prompt, tier="smart", system=SYNTH_SYSTEM, purpose="research_synthesis", max_tokens=6000)


# ------------------------------------------------------------------- build

def build(symbol: str, force: bool = False) -> dict:
    symbol = symbol.upper().strip()
    with _glock:
        lock = _locks.setdefault(symbol, threading.Lock())
    if not lock.acquire(blocking=False):
        return status(symbol)
    try:
        if not force:
            hit = get_cached(symbol)
            if hit:
                _set(symbol, state="ready")
                return hit
        _set(symbol, state="building", step="Reading screener.in financials", progress=5, error=None)
        c = screener.get_company(symbol)
        facts = compute_facts(c)
        llm = get_llm()
        if not llm.available():
            raise LLMUnavailable("No model configured - numbers only")

        concalls = [cc for cc in c["concalls"] if cc.get("transcript")][:N_TRANSCRIPTS]
        _set(symbol, step=f"Reading {len(concalls)} concall transcripts", progress=15)
        transcripts: list[dict] = []
        errors: list[str] = []

        def tx(cc):
            try:
                return extract_transcript(cc["transcript"], cc["label"])
            except Exception as e:
                errors.append(f"transcript {cc['label']}: {str(e)[:100]}")
                return None

        with ThreadPoolExecutor(max_workers=4) as ex:
            for r in ex.map(tx, concalls):
                if r:
                    transcripts.append(r)
        _set(symbol, step="Reading the annual report (MD&A)", progress=55)
        ar = None
        if c["annual_reports"]:
            a = c["annual_reports"][0]
            try:
                ar = extract_annual_report(a["url"], a["year"])
            except Exception as e:
                errors.append(f"annual report: {str(e)[:100]}")
        _set(symbol, step="Synthesising (strong model)", progress=75)
        synth = synthesise(c, facts, transcripts, ar)
        out = {
            "symbol": symbol, "name": c["name"], "built_at": datetime.now().isoformat(timespec="seconds"),
            "basis": "consolidated" if c["consolidated"] else "standalone",
            "about": c.get("about"), "top": c.get("top"),
            "facts": facts, "sections": synth,
            "transcripts": [{"label": t.get("label"), "quarter": t.get("quarter"), "tone": t.get("tone"),
                             "tone_evidence": t.get("tone_evidence"), "url": t.get("url"),
                             "guidance": t.get("guidance", []), "themes": t.get("themes", []),
                             "analyst_pushback": t.get("analyst_pushback", [])} for t in transcripts],
            "annual_report": ar,
            "sources": {"screener": c["source"],
                        "transcripts": [{"label": cc["label"], "url": cc["transcript"]} for cc in concalls],
                        "annual_report": c["annual_reports"][0] if c["annual_reports"] else None},
            "errors": errors,
            "model": {"fast": llm.model_for("fast"), "smart": llm.model_for("smart"), "provider": llm.provider},
        }
        store.put("research", symbol, out)
        _set(symbol, state="ready", progress=100, step="done")
        return out
    except screener.CompanyNotFound:
        _set(symbol, state="error", error=f"{symbol} not found on screener.in")
        raise
    except Exception as e:
        _set(symbol, state="error", error=str(e)[:200])
        raise
    finally:
        lock.release()


# --------------------------------------------------------------------- ask

ASK_SYSTEM = """You are FINN answering an investor's question about one company.
Answer ONLY from the research material supplied (numbers, transcript extractions, annual-report extraction). No outside knowledge, no news, no broker views. If the material does not cover it, say so in one line.
Format: <= 120 words. Lead with the answer. Short lines. Tag facts with sources like [Q1FY27 call], [AR FY26], [Numbers]. Plain text, no markdown headers."""


def ask(symbol: str, question: str, history: list[dict] | None = None, context: str | None = None) -> dict:
    r = get_cached(symbol)
    if not r:
        raise LookupError("research not built")
    llm = get_llm()
    hist = ""
    for h in (history or [])[-4:]:
        hist += f"\n{h.get('role', 'user').upper()}: {h.get('text', '')[:600]}"
    prompt = f"""Company: {r['name']} ({symbol})
NUMBERS:
{facts_text(r['facts'])}
RESEARCH (already derived from primary sources):
{json.dumps(r['sections'], ensure_ascii=False)}
TRANSCRIPTS:
{json.dumps(r['transcripts'], ensure_ascii=False)}
ANNUAL REPORT:
{json.dumps(r.get('annual_report'), ensure_ascii=False)}
{('CONTEXT (a filing the investor is looking at): ' + context) if context else ''}
{('CONVERSATION SO FAR:' + hist) if hist else ''}

QUESTION: {question}"""
    text = llm.complete(prompt, tier="smart", system=ASK_SYSTEM, purpose="ask", max_tokens=800, use_cache=False)
    return {"answer": text, "model": llm.model_for("smart")}
