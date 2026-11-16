"""The Network: who in the investor's own circle can explain what just happened.

Everything here is deterministic graph work over three small tables:

    people      the investor's contacts, each with a career and an education
    orgs        companies / schools with aliases, a ticker where listed, themes
    ecosystem   competitor / supplier / customer edges between companies

No model sees a contact. Names in filings are matched to organisations by
alias, tenures are compared by year, and every link carries the evidence it
rests on ("both at ICICI Bank 2017-2021") or says plainly that the dates are
not in the filing. The only model call in this file is an optional planner
for free-form questions, and it is given the question, the theme list and the
company list - never a person.
"""
from __future__ import annotations

import json
import re
from datetime import date, datetime
from difflib import SequenceMatcher

from .. import store
from ..config import PORTFOLIO, RESEARCH_SET, ROOT, company_name
from ..llm import get_llm

NETWORK_FILE = ROOT / "seed" / "network.json"
COLD_DAYS = 150           # a tie counts as "going cold" after this long
MATERIAL = {"results", "M&A", "management_change", "fund_raise", "litigation", "capex",
            "credit_rating", "pledging", "press_release", "bonus_split"}
UPSI = "Current employee: industry context only, nothing unpublished."

# which kind of experience explains which kind of event
EVENT_FN = {
    "M&A": {"strategy", "finance", "general"},
    "capex": {"operations", "supply_chain", "strategy"},
    "litigation": {"legal", "finance", "risk"},
    "results": {"finance", "sales", "ir", "strategy"},
    "fund_raise": {"finance", "strategy", "ir"},
    "credit_rating": {"finance", "risk"},
    "pledging": {"finance"},
    "press_release": {"sales", "operations", "supply_chain"},
    "management_change": {"general", "strategy", "finance", "sales", "operations"},
}
EVENT_ASK = {
    "M&A": "Does this fit how {co} has allocated capital before, or is it a change of direction?",
    "capex": "Is the timeline realistic, and where has {co} slipped on projects like this before?",
    "litigation": "Is this routine for the industry, or the kind of order that changes behaviour?",
    "results": "Which line in these numbers would worry someone who has run this business?",
    "fund_raise": "Why raise now, and what does it say about growth against the balance sheet?",
    "credit_rating": "What would the agency have been shown that the market has not?",
    "pledging": "Is the promoter under pressure elsewhere in the group?",
    "press_release": "Is this size and margin normal for {co}, and how lumpy is the execution?",
    "management_change": "What changes on the ground at {co} when the person in this chair changes?",
    "price": "Is anything happening on the ground at {co} that would explain today's move?",
}
REL_LABEL = {"inside": "Inside", "alumni": "Used to work there", "competitor": "At a competitor",
             "supplier": "At a supplier", "customer": "At a customer", "sector": "Knows the sector"}

# words in a company description -> theme, so companies outside the demo set still find experts
THEME_WORDS = {
    "private banks": ["bank"], "NBFC": ["nbfc", "non-banking", "housing finance", "consumer finance"],
    "rural lending": ["rural", "microfinance", "tractor", "vehicle finance"],
    "IT services": ["it services", "information technology", "software services", "it - software", "computers - software"],
    "pharma": ["pharma", "drug", "formulation"], "US generics": ["generic"],
    "steel": ["steel"], "aluminium": ["alumin"], "metals and mining": ["mining", "metal", "zinc", "copper"],
    "paints": ["paint", "coating"], "cables and wires": ["cable", "wire"],
    "consumer electricals": ["fan", "switchgear", "appliance", "electrical"],
    "real estate": ["real estate", "realty", "residential project"],
    "FMCG": ["fmcg", "packaged", "personal care", "consumer goods", "food products"],
    "passenger vehicles": ["passenger vehicle", "automobile", "cars", "two-wheeler", "2/3 wheelers"],
    "auto components": ["auto component", "auto ancillar", "automotive component"],
    "auto software": ["automotive software", "embedded software"],
    "electric vehicles": ["electric vehicle", " ev "],
    "specialty chemicals": ["specialty chemical", "speciality chemical", "chemicals"],
    "agrochemicals": ["agrochem", "agro chem", "crop protection", "pesticide"],
    "electronics manufacturing": ["electronics manufactur", "ems ", "consumer electronics", "contract manufactur"],
    "semiconductors": ["semiconductor"],
    "infrastructure and EPC": ["epc", "construction", "infrastructure"],
    "capital goods": ["capital goods", "engineering", "heavy electrical", "industrial product"],
    "beverages": ["beverage", "bottl", "soft drink"], "jewellery retail": ["jewel", "gems"],
    "quick commerce": ["quick commerce", "food delivery"], "consumer internet": ["e-commerce", "online platform", "internet"],
    "organised retail": ["retail"], "telecom": ["telecom"], "life insurance": ["insurance"],
    "refining and petrochemicals": ["refiner", "petrochem", "oil & gas", "petroleum"], "new energy": ["renewable", "solar"],
    "railways and PSUs": ["railway"], "fintech": ["fintech", "payments"], "capital markets": ["broking", "asset management", "capital markets"],
    "engines and powertrain": ["engine", "powertrain"],
}

_cache: dict = {}


# ------------------------------------------------------------------ load

def _raw() -> dict:
    mt = NETWORK_FILE.stat().st_mtime
    if _cache.get("mt") != mt:
        data = json.loads(NETWORK_FILE.read_text())
        _cache.update(mt=mt, data=data, index=_build_index(data))
    return _cache["data"]


def _build_index(data: dict) -> dict:
    orgs = data["orgs"]
    by_symbol = {o["symbol"]: oid for oid, o in orgs.items() if o.get("symbol")}
    aliases = []  # (alias, org_id), longest first so "ICICI Securities" beats "ICICI"
    for oid, o in orgs.items():
        for a in {o["name"], *o.get("aliases", [])}:
            aliases.append((a, oid))
    aliases.sort(key=lambda x: -len(x[0]))
    rel: dict[str, dict[str, set]] = {oid: {"competitor": set(), "supplier": set(), "customer": set()} for oid in orgs}
    for sym, e in data.get("ecosystem", {}).items():
        a = by_symbol.get(sym)
        if not a:
            continue
        for b in e.get("competitors", []):
            rel[a]["competitor"].add(b); rel[b]["competitor"].add(a)
        for b in e.get("suppliers", []):
            rel[a]["supplier"].add(b); rel[b]["customer"].add(a)
        for b in e.get("customers", []):
            rel[a]["customer"].add(b); rel[b]["supplier"].add(a)
    return {"by_symbol": by_symbol, "aliases": aliases, "rel": rel}


def _idx() -> dict:
    _raw()
    return _cache["index"]


def _state() -> dict:
    return store.get("network", "state") or {"forgotten": [], "contact_log": {}}


def log_contact(pid: str) -> dict:
    s = _state()
    s["contact_log"][pid] = date.today().isoformat()
    return store.put("network", "state", s)


def forget(pid: str) -> dict:
    """Erase a contact from every view. In the prototype this hides the seed row;
    in a real deployment it deletes the row and its derived edges."""
    s = _state()
    if pid not in s["forgotten"]:
        s["forgotten"].append(pid)
    s["contact_log"].pop(pid, None)
    return store.put("network", "state", s)


def restore_all() -> dict:
    return store.put("network", "state", {"forgotten": [], "contact_log": {}})


def people() -> list[dict]:
    s = _state()
    out = []
    for p in _raw()["people"]:
        if p["id"] in s["forgotten"]:
            continue
        p = dict(p)
        p["last_contact"] = max(p["last_contact"], s["contact_log"].get(p["id"], ""))
        out.append(p)
    return out


def investor() -> dict:
    return _raw()["investor"]


# ------------------------------------------------------------------ helpers

def _org(oid: str | None) -> dict:
    return _raw()["orgs"].get(oid or "", {})


def _org_name(entry: dict) -> str:
    return entry.get("org_name") or _org(entry.get("org")).get("name") or "Independent"


def _days_since(iso: str) -> int:
    return (date.today() - date.fromisoformat(iso)).days


def _ago(days: int) -> str:
    if days < 14:
        return "this fortnight"
    if days < 60:
        return f"{days // 7} weeks ago"
    if days < 365:
        return f"{round(days / 30)} months ago"
    return f"{days / 365:.1f} years ago".replace(".0", "")


def _span(e: dict) -> str:
    return f"{e['from']}–{e['to'] or 'now'}"


def _now_entry(p: dict) -> dict:
    cur = [e for e in p["career"] if e["to"] is None]
    return cur[0] if cur else p["career"][0]


def card(p: dict) -> dict:
    """The small, safe-to-render view of a contact."""
    now = _now_entry(p)
    d = _days_since(p["last_contact"])
    return {
        "id": p["id"], "name": p["name"], "now": f"{now['role']}, {_org_name(now)}", "city": p.get("city"),
        "how": p["how"], "source": p["source"], "strength": p["strength"],
        "last_contact": p["last_contact"], "days_since": d, "ago": _ago(d), "cold": d >= COLD_DAYS,
    }


def _alias_re(alias: str) -> re.Pattern:
    flags = 0 if (len(alias) <= 5 or " " not in alias and alias.isupper()) else re.I
    return re.compile(r"(?<![A-Za-z0-9])" + re.escape(alias) + r"(?![A-Za-z0-9])", flags)


def find_orgs(text: str) -> list[dict]:
    """Organisations named in free text, with any years stated next to them."""
    if not text:
        return []
    hits: list[dict] = []
    taken: list[tuple[int, int]] = []
    for alias, oid in _idx()["aliases"]:
        for m in _alias_re(alias).finditer(text):
            if any(m.start() < b and m.end() > a for a, b in taken):
                continue
            taken.append((m.start(), m.end()))
            hits.append({"org": oid, "start": m.start(), "end": m.end(), "alias": m.group(0)})
    hits.sort(key=lambda h: h["start"])
    year = date.today().year
    for i, h in enumerate(hits):
        nxt = hits[i + 1]["start"] if i + 1 < len(hits) else len(text)
        stop = re.search(r"[.;]\s|\n", text[h["end"]:nxt])
        after = text[h["end"]:h["end"] + stop.start() if stop else nxt][:70]
        prev_end = hits[i - 1]["end"] if i else 0
        before = re.split(r"[.;]\s", text[max(prev_end, h["start"] - 45):h["start"]])[-1]
        frm = to = None
        m = re.search(r"((?:19|20)\d{2})\s*(?:-|–|—|to|till|until)\s*((?:19|20)\d{2}|present|date|now)", after, re.I)
        if m:
            frm = int(m.group(1)); to = int(m.group(2)) if m.group(2).isdigit() else year
        elif (m := re.search(r"(?:since|from|joined(?: in)?)\s+((?:19|20)\d{2})", after, re.I)):
            frm, to = int(m.group(1)), year
        elif (m := re.search(r"(\d{1,2})\s*\+?\s*years", before + " " + after[:25], re.I)):
            frm, to = year - int(m.group(1)), year
        elif (m := re.search(r"\(?((?:19|20)\d{2})\)?", after[:22])):
            frm = to = int(m.group(1))
        elif re.search(r"current|present", before, re.I):
            to = year
        h.update({"from": frm, "to": to})
    return hits


def _norm_name(n: str) -> str:
    n = re.sub(r"\b(mr|mrs|ms|dr|shri|smt|prof|ca|cs)\b\.?", " ", n.lower())
    return re.sub(r"[^a-z ]", "", n).strip()


def _same_person(a: str, b: str) -> bool:
    a, b = _norm_name(a), _norm_name(b)
    return bool(a and b) and (a == b or SequenceMatcher(None, a, b).ratio() > 0.92)


# ------------------------------------------------------------------ company context

def context_for(symbol: str | None = None, org_id: str | None = None, text: str = "") -> dict:
    """Resolve a company to its place in the ecosystem. Works for any ticker:
    known ones get curated edges, unknown ones get themes from their description."""
    idx = _idx()
    if symbol and not org_id:
        org_id = idx["by_symbol"].get(symbol.upper())
    themes = set(_org(org_id).get("themes", []))
    meta = (PORTFOLIO.get(symbol or "") or RESEARCH_SET.get(symbol or "") or ("", "", ""))
    blob = f" {text} {meta[1]} ".lower()
    if not themes or text:
        for theme, words in THEME_WORDS.items():
            if any(w in blob for w in words):
                themes.add(theme)
    rel = idx["rel"].get(org_id or "", {"competitor": set(), "supplier": set(), "customer": set()})
    name = _org(org_id).get("name") or (company_name(symbol) if symbol else "")
    return {"org": org_id, "symbol": symbol, "name": name, "themes": themes, "rel": rel}


def who_to_call(symbol: str | None = None, org_id: str | None = None, text: str = "",
                limit: int = 12, include_sector: bool = True) -> list[dict]:
    ctx = context_for(symbol, org_id, text)
    year = date.today().year
    out = []
    for p in people():
        best = None
        for e in p["career"]:
            oid = e.get("org")
            parent = _org(oid).get("parent")
            rel = None
            if ctx["org"] and (oid == ctx["org"] or parent == ctx["org"]):
                rel = "inside" if e["to"] is None else "alumni"
            elif oid:
                for kind in ("competitor", "supplier", "customer"):
                    if oid in ctx["rel"][kind]:
                        rel = kind
                        break
            if not rel:
                continue
            left = 0 if e["to"] is None else year - e["to"]
            yrs = (e["to"] or year) - e["from"]
            base = {"inside": 92, "alumni": 90, "competitor": 62, "supplier": 60, "customer": 60}[rel]
            score = base - 2.5 * left + 2 * e["level"] + min(yrs, 10) + 3 * p["strength"]
            if parent == ctx["org"] and oid != ctx["org"]:
                score -= 18  # a group company, not the listed entity itself
            if best is None or score > best[0]:
                best = (score, rel, e, left, yrs)
        if best is None and include_sector:
            shared = ctx["themes"] & set(p.get("themes", []))
            if shared:
                e = _now_entry(p)
                best = (30 + 3 * p["strength"] + 2 * e["level"] + 4 * len(shared), "sector", e, 0, 0)
                theme = sorted(shared)[0]
        if best is None:
            continue
        score, rel, e, left, yrs = best
        co = ctx["name"] or "the company"
        if rel == "inside":
            why = f"{e['role']} at {_org_name(e)} since {e['from']}."
        elif rel == "alumni":
            why = f"{e['role']} at {_org_name(e)}, {_span(e)}: {yrs} years inside, left {left} year{'s' if left != 1 else ''} ago."
        elif rel == "sector":
            why = f"Go-to on {theme}: {e['role']}, {_org_name(e)}."
        else:
            tense = "Now" if e["to"] is None else f"{_span(e)}:"
            side = {"competitor": f"competes with {co}", "supplier": f"sells to {co}", "customer": f"buys from {co}"}[rel]
            why = f"{tense} {e['role']} at {_org_name(e)}, which {side}."
        out.append({**card(p), "relation": rel, "label": REL_LABEL[rel], "why": why,
                    "knows": e.get("knows") or "", "fn": e.get("fn"), "score": round(score, 1),
                    "via_org": e.get("org"), "caution": UPSI if rel == "inside" else None})
    out.sort(key=lambda x: -x["score"])
    return out[:limit]


def for_event(item: dict, kind: str | None = None) -> dict | None:
    """The one person best placed to give context on a filing, and what to ask.
    Returns None unless someone has a real link to the company: a quiet layer
    says nothing when it has nothing."""
    cat = kind or item.get("category")
    text = f"{item.get('subject') or ''} {item.get('headline') or item.get('title') or ''}"
    cands = who_to_call(item["symbol"], include_sector=False)
    if not cands:
        return None
    named = {h["alias"].lower() for h in find_orgs(text)}
    by_id = {p["id"]: p for p in people()}
    for c in cands:
        bonus = 8 if c["fn"] in EVENT_FN.get(cat, set()) else 0
        bonus += 10 if c["relation"] in ("inside", "alumni") else 0
        # a business unit named in the filing itself (e.g. "Novelis") that this person worked in
        for e in by_id[c["id"]]["career"]:
            if not e.get("org_name") or e.get("org") != c["via_org"]:
                continue
            nm = e["org_name"].lower()
            if any(a in nm for a in named if len(a) > 3):
                bonus += 16
                c["specific"] = True
                c["why"] = f"{e['role']} at {e['org_name']}, {_span(e)}: the unit this filing is about."
                c["knows"] = e.get("knows") or c["knows"]
                break
        c["event_score"] = c["score"] + bonus
    cands.sort(key=lambda x: -x["event_score"])
    lead = cands[0]
    co = company_name(item["symbol"])
    ask = EVENT_ASK.get(cat, EVENT_ASK["results"]).format(co=co)
    if cat == "results" and (item.get("results") or {}).get("why"):
        # the numbers themselves make a sharper question than any template
        ask = f"{item['results']['why']} What is behind that which the release does not say?"
    return {"lead": lead, "more": len(cands) - 1, "others": [c["name"] for c in cands[1:3]], "ask": ask}


# ------------------------------------------------------------------ people in filings

def link_person(name: str, background: str, symbol: str | None = None, event: str | None = None) -> dict:
    """Routes from the investor to a person named in a filing.

    The appointee's career is read out of the filing's own text (their Reg-30
    profile), then compared with every contact's career year by year."""
    year = date.today().year
    for p in people():
        if _same_person(name, p["name"]):
            return {"person": name, "direct": card(p), "links": [], "note": f"You know {p['name'].split()[0]} directly."}
    bio = find_orgs(background or "")
    home = _idx()["by_symbol"].get((symbol or "").upper())
    if home and event in ("resigned", "retired", "ceased") and not any(b["org"] == home for b in bio):
        bio.append({"org": home, "from": None, "to": None, "alias": _org(home).get("name")})
    bio.sort(key=lambda b: 0 if "group" in (b.get("alias") or "").lower() else 1)
    links: dict[str, dict] = {}

    def consider(pid, link):
        if pid not in links or link["evidence"] >= links[pid]["evidence"]:
            links[pid] = link

    me = investor()
    for b in bio:
        o = _org(b["org"])
        school = o.get("kind") == "school"
        for who in [{"id": "you", "name": "You", "career": me["career"], "education": me["education"], "strength": 5}] + people():
            if school:
                for ed in who.get("education", []):
                    if ed["inst"] != b["org"]:
                        continue
                    if b["from"] and abs(ed["year"] - b["from"]) <= 2:
                        consider(who["id"], {"via": "Studied together", "evidence": 3, "confirmed": True,
                                             "detail": f"{o['name']}, {ed['degree']} {ed['year']}; the filing puts {name.split()[-1]} there in {b['from']}."})
                    else:
                        consider(who["id"], {"via": "Same alma mater", "evidence": 1, "confirmed": False,
                                             "detail": f"{o['name']} ({ed['degree']} {ed['year']})" + (f"; {b['from']} for {name.split()[-1]}, so not the same years." if b["from"] else "; the filing gives no year.")})
                continue
            for e in who["career"]:
                if e.get("org") != b["org"] and _org(e.get("org")).get("parent") != b["org"]:
                    continue
                e_to = e["to"] or year
                if b["from"] is None:
                    consider(who["id"], {"via": "Same employer", "evidence": 2, "confirmed": False,
                                         "detail": f"{e['role']} at {_org_name(e)}, {_span(e)}. No dates in the filing for {name.split()[-1]}."})
                    continue
                lo, hi = max(e["from"], b["from"]), min(e_to, b["to"] or year)
                if hi - lo >= 1:
                    consider(who["id"], {"via": "Worked in the same firm", "evidence": 4 if hi - lo >= 3 else 3, "confirmed": True,
                                         "detail": f"Both at {o['name']} {lo}–{hi if hi != year else 'now'} ({hi - lo} yr{'s' if hi - lo != 1 else ''}). {who['name'].split()[0] if who['id'] != 'you' else 'You'} {'were' if who['id'] == 'you' else 'was'} {e['role']}."})
                else:
                    consider(who["id"], {"via": "Same employer, different years", "evidence": 1, "confirmed": False,
                                         "detail": f"{e['role']} at {_org_name(e)}, {_span(e)}; no overlap with the dates in the filing."})
    by_id = {p["id"]: p for p in people()}
    out = []
    you = links.pop("you", None)
    for pid, l in links.items():
        p = by_id[pid]
        # a chain is as strong as its weaker half: how well you know the contact, how well they know the target
        out.append({**l, **card(p), "strength": min(p["strength"], l["evidence"] + 1), "tie": p["strength"]})
    out.sort(key=lambda x: (-x["evidence"], -x["strength"]))
    # "same college, year unknown" and "same employer, different decade" are not routes: a quiet layer drops them
    out = [x for x in out if x["evidence"] >= 2]
    note = None
    if not out and not you:
        note = ("No one in your network overlaps with the career in this filing." if bio
                else "The filing names no prior employers, so there is nothing to match against.")
    return {"person": name, "direct": None, "links": out[:3], "you": you, "note": note,
            "orgs": sorted({_org(b["org"]).get("name") for b in bio if _org(b["org"]).get("name")})}


# ------------------------------------------------------------------ themes

def themes() -> list[dict]:
    count: dict[str, int] = {}
    for p in people():
        for t in p.get("themes", []):
            count[t] = count.get(t, 0) + 1
    return sorted(({"theme": t, "count": n} for t, n in count.items()), key=lambda x: (-x["count"], x["theme"]))


def expertise(query: str, limit: int = 8) -> dict:
    """Who are my go-to people for a theme."""
    q = query.lower()
    words = [w for w in re.findall(r"[a-z&]{3,}", q) if w not in STOP]
    all_themes = {t["theme"] for t in themes()} | set(THEME_WORDS)
    exact = [t for t in all_themes if t.lower() in q]
    matched = exact or [t for t in all_themes if any(w in t.lower().split() or t.lower().startswith(w) for w in words)]
    if not exact:
        for t, ws in THEME_WORDS.items():
            if any(w.strip() in q for w in ws if len(w.strip()) > 3) and t not in matched:
                matched.append(t)
    year = date.today().year
    out = []
    for p in people():
        hit = [t for t in p.get("themes", []) if t in matched]
        org_hit = any(set(_org(e.get("org")).get("themes", [])) & set(matched) for e in p["career"])
        text_hit = [] if exact else [e for e in p["career"] if any(w in f"{e['role']} {e.get('knows', '')} {_org_name(e)}".lower() for w in words)]
        if not hit and not text_hit and not (exact and org_hit):
            continue
        yrs = sum((e["to"] or year) - e["from"] for e in p["career"]
                  if set(_org(e.get("org")).get("themes", [])) & set(matched)) if matched else 0
        e = (text_hit or [_now_entry(p)])[0]
        score = 10 * len(hit) + min(yrs, 15) + 2 * max(x["level"] for x in p["career"]) + 2 * p["strength"] + 4 * len(text_hit)
        why = (f"{yrs} years across {', '.join(sorted({_org_name(x) for x in p['career'] if set(_org(x.get('org')).get('themes', [])) & set(matched)}))}."
               if yrs else f"{e['role']}, {_org_name(e)}.")
        out.append({**card(p), "relation": "sector", "label": ", ".join(hit[:2]) or "Related experience",
                    "why": why, "knows": e.get("knows") or _now_entry(p).get("knows") or "", "score": score})
    out.sort(key=lambda x: -x["score"])
    return {"themes": sorted(matched), "people": out[:limit]}


STOP = {"who", "whom", "the", "for", "and", "are", "can", "could", "should", "would", "about", "with", "know", "knows",
        "people", "person", "network", "call", "speak", "talk", "anyone", "someone", "help", "understand", "have", "has",
        "does", "what", "which", "theme", "sector", "expert", "experts", "from", "into", "that", "this", "there", "any",
        "you", "your", "mine", "tell", "show", "find", "get", "give", "best", "placed", "ask", "contact", "contacts", "say"}


# ------------------------------------------------------------------ keeping it warm

def _events_by_org(items: list[dict]) -> dict[str, list[dict]]:
    by: dict[str, list[dict]] = {}
    idx = _idx()["by_symbol"]
    for it in items or []:
        if it.get("tier") == "routine" or it.get("category") not in MATERIAL or it.get("score", 0) < 50:
            continue
        oid = idx.get(it["symbol"])
        if oid:
            by.setdefault(oid, []).append(it)
    for v in by.values():
        v.sort(key=lambda x: (-x.get("score", 0), x["time"]))
    return by


def _opener(p: dict, e: dict, it: dict, reconnect: bool) -> str:
    first = p["name"].split()[0]
    co = _org(e.get("org")).get("name") or _org_name(e)
    what = (it.get("headline") or "").rstrip(".")
    tail = ("It has been too long. Coffee or a call next week?" if reconnect
            else "You know that business better than anyone I can ask. Fifteen minutes this week?")
    return f"Hi {first}, saw the news from {co}: {what[:110]}. {tail}"


def warm(items: list[dict], limit: int = 6) -> list[dict]:
    """Contacts going cold whose current or former employer just did something.
    A filing is a natural, non-awkward reason to pick up the phone."""
    by = _events_by_org(items)
    out = []
    for p in people():
        d = _days_since(p["last_contact"])
        if d < COLD_DAYS:
            continue
        best = None
        for e in p["career"]:
            for it in by.get(e.get("org") or "", [])[:1]:
                s = it.get("score", 0) + 4 * p["strength"] + min(d, 600) / 30 + (6 if e["to"] is None else 0) + _event_weight(it)
                if best is None or s > best[0]:
                    best = (s, e, it)
        if best:
            s, e, it = best
            tie = "current" if e["to"] is None else "former"
            out.append({**card(p), "score": round(s, 1), "kind": "reconnect", "symbol": it["symbol"], "item_id": it["id"],
                        "headline": it.get("headline"), "category": it.get("category"),
                        "why": f"Last spoke {_ago(d)}. Their {tie} employer just filed.",
                        "knows": e.get("knows") or "", "opener": _opener(p, e, it, True)})
    out.sort(key=lambda x: -x["score"])
    return out[:limit]


def _event_weight(it: dict) -> float:
    """A deal, a departure or a lawsuit is a better reason to call than a scheduled print;
    results earn a call when the numbers moved."""
    if it.get("category") != "results":
        return 18
    pat = next((r for r in (it.get("results") or {}).get("rows", []) if r["metric"] == "PAT"), {})
    return min(abs(pat.get("yoy_pct") or 0), 40) / 2.5


def call_sheet(items: list[dict], limit: int = 4) -> list[dict]:
    """Today's filings, turned into the few phone calls worth making."""
    picks: dict[str, dict] = {}
    by_id = {p["id"]: p for p in people()}
    for it in sorted(items or [], key=lambda x: -x.get("score", 0)):
        if it.get("tier") != "attention" or it.get("category") not in MATERIAL:
            continue
        ev = it.get("network")
        if not ev:
            continue
        lead = ev["lead"]
        if lead["relation"] not in ("inside", "alumni") or lead["id"] in picks:
            continue
        p = by_id[lead["id"]]
        e = next((x for x in p["career"] if x.get("org") == lead["via_org"]), _now_entry(p))
        picks[lead["id"]] = {**lead, "kind": "context", "symbol": it["symbol"], "item_id": it["id"],
                             "headline": it.get("headline"), "category": it.get("category"), "ask": ev["ask"],
                             "opener": _opener(p, e, it, False),
                             "rank": it.get("score", 0) + lead["score"] / 4 + _event_weight(it)}
    for w in warm(items):
        if w["id"] in picks:
            picks[w["id"]]["kind"] = "both"
            picks[w["id"]]["why"] += f" Last spoke {w['ago']}."
        else:
            picks[w["id"]] = {**w, "rank": w["score"] + 12, "ask": None}
    out = sorted(picks.values(), key=lambda x: -x["rank"])
    # one call per company keeps the sheet short and varied
    seen, sheet = set(), []
    for c in out:
        if c["symbol"] in seen:
            continue
        seen.add(c["symbol"])
        sheet.append(c)
    return sheet[:limit]


# ------------------------------------------------------------------ digest hook (Push)

def annotate_digest(d: dict) -> dict:
    """Weave the network into an assembled digest. Pure function of the digest
    and the network tables, so it runs on every request in a few milliseconds."""
    seen: dict[str, list] = {}
    for it in d.get("items", []):
        if it.get("tier") == "routine":
            continue
        if it.get("people"):
            for c in it["people"].get("changes", []):
                if c.get("person"):
                    c["network"] = link_person(c["person"], f"{c.get('background') or ''}", it["symbol"], c.get("event"))
                    seen.setdefault(it["symbol"], []).append(
                        {"person": c["person"], "role": c.get("role"), "event": c.get("event"),
                         "background": c.get("background"), "time": it["time"], "item_id": it["id"]})
        if it.get("category") in MATERIAL:
            ev = for_event(it)
            # attention-tier filings earn a person; a lesser filing earns one only when a
            # contact worked in the very unit it names - the thing the investor would not notice
            if ev and (it.get("tier") == "attention" or ev["lead"].get("specific")):
                it["network"] = ev
    for a in d.get("alerts", []):
        if a["kind"] in ("price", "volume"):
            ev = for_event({"symbol": a["symbol"], "title": a["title"]}, kind="price")
            if ev and ev["lead"]["relation"] in ("inside", "alumni", "supplier", "customer"):
                a["network"] = ev
    for sym, ppl in seen.items():
        cur = store.get("people_seen", sym) or []
        have = {(x["person"], x.get("item_id")) for x in cur}
        add = [x for x in ppl if (x["person"], x["item_id"]) not in have]
        if add:
            store.put("people_seen", sym, (add + cur)[:30])
    d["call_sheet"] = call_sheet(d.get("items", []))
    return d


def index_people_from_cache() -> int:
    """Rebuild the index of people named in filings from all cached digests."""
    from ..config import CACHE_DIR
    n = 0
    found: dict[str, dict] = {}
    for f in (CACHE_DIR / "digest").glob("*.json"):
        try:
            d = json.loads(f.read_text())
        except Exception:
            continue
        for it in d.get("items", []):
            for c in (it.get("people") or {}).get("changes", []):
                if c.get("person"):
                    found.setdefault(it["symbol"], {})[(c["person"], it["id"])] = {
                        "person": c["person"], "role": c.get("role"), "event": c.get("event"),
                        "background": c.get("background"), "time": it["time"], "item_id": it["id"]}
    for sym, rows in found.items():
        cur = store.get("people_seen", sym) or []
        have = {(x["person"], x.get("item_id")) for x in cur}
        add = [v for k, v in rows.items() if k not in have]
        if add:
            merged = sorted(add + cur, key=lambda x: x["time"], reverse=True)[:30]
            store.put("people_seen", sym, merged)
            n += len(add)
    return n


def seen_people(symbol: str) -> list[dict]:
    """People named in this company's filings, one row each, fullest profile first."""
    best: dict[str, dict] = {}
    for x in store.get("people_seen", symbol.upper()) or []:
        k = _norm_name(x["person"])
        if k not in best or len(x.get("background") or "") > len(best[k].get("background") or ""):
            best[k] = {**x, "event": (best.get(k) or x).get("event") or x.get("event")}
    return sorted(best.values(), key=lambda x: x["time"], reverse=True)


# ------------------------------------------------------------------ views

def company_view(symbol: str, about: str = "", questions: list[str] | None = None) -> dict:
    """Who to call about a company (Pull). Groups by how they are connected."""
    symbol = symbol.upper()
    ppl = who_to_call(symbol, text=about, limit=14)
    groups = []
    for key, label in (("inside", "Inside the company"), ("alumni", "Used to work there"), ("competitor", "Competitors"),
                       ("supplier", "Suppliers"), ("customer", "Customers"), ("sector", "Know the sector")):
        g = [p for p in ppl if p["relation"] == key]
        if g:
            groups.append({"key": key, "label": label, "people": g[:4]})
    # pair open research questions with the first people worth asking
    qs = list(questions or [])
    direct = [p for p in ppl if p["relation"] in ("alumni", "inside")] or ppl
    for i, p in enumerate(direct[:len(qs)]):
        p["ask"] = qs[i]
    filings = [{**x, "network": link_person(x["person"], x.get("background") or "", symbol, x.get("event"))}
               for x in seen_people(symbol)]
    ctx = context_for(symbol, text=about)
    return {"symbol": symbol, "name": ctx["name"], "themes": sorted(ctx["themes"]), "count": len(ppl),
            "groups": groups, "filing_people": filings[:6]}


def person_view(pid: str, items: list[dict] | None = None) -> dict | None:
    p = next((x for x in people() if x["id"] == pid), None)
    if not p:
        return None
    year = date.today().year
    by = _events_by_org(items or [])
    career = []
    live = []
    for e in p["career"]:
        o = _org(e.get("org"))
        career.append({"org": _org_name(e), "symbol": o.get("symbol"), "role": e["role"], "from": e["from"], "to": e["to"],
                       "knows": e.get("knows") or "", "in_book": o.get("symbol") in PORTFOLIO or o.get("symbol") in RESEARCH_SET})
        for it in by.get(e.get("org") or "", [])[:2]:
            if any(x["item_id"] == it["id"] for x in live):
                continue
            live.append({"symbol": it["symbol"], "headline": it.get("headline"), "category": it.get("category"),
                         "time": it["time"], "item_id": it["id"], "tie": "current" if e["to"] is None else "former",
                         "opener": _opener(p, e, it, _days_since(p["last_contact"]) >= COLD_DAYS)})
    me = investor()
    shared = []
    for ed in p.get("education", []):
        for mine in me["education"]:
            if ed["inst"] == mine["inst"]:
                gap = abs(ed["year"] - mine["year"])
                shared.append(f"{_org(ed['inst'])['name']}: {'same class' if gap == 0 else f'{gap} year' + ('s' if gap > 1 else '') + ' apart'}")
    for e in p["career"]:
        for mine in me["career"]:
            if e.get("org") == mine["org"] and min(e["to"] or year, mine["to"]) - max(e["from"], mine["from"]) >= 1:
                shared.append(f"{_org_name(e)}: overlapped {max(e['from'], mine['from'])}–{min(e['to'] or year, mine['to'])}")
    # who else in the network has worked alongside this person
    mutual = []
    for q in people():
        if q["id"] == pid:
            continue
        for e in p["career"]:
            for f in q["career"]:
                if e.get("org") and e.get("org") == f.get("org"):
                    lo, hi = max(e["from"], f["from"]), min(e["to"] or year, f["to"] or year)
                    if hi - lo >= 1:
                        mutual.append({"id": q["id"], "name": q["name"], "detail": f"both at {_org_name(e)} {lo}–{hi if hi != year else 'now'}"})
    seen, uniq = set(), []
    for m in mutual:
        if m["id"] not in seen:
            seen.add(m["id"]); uniq.append(m)
    return {**card(p), "career": career,
            "education": [{"inst": _org(ed["inst"]).get("name", ed["inst"]), "degree": ed["degree"], "year": ed["year"]} for ed in p.get("education", [])],
            "themes": p.get("themes", []), "shared": shared, "mutual": uniq[:4], "live": live[:3],
            "caution": UPSI if any(c["to"] is None and c["in_book"] for c in career) else None,
            "provenance": "Synthetic profile."}


def overview(items: list[dict] | None = None) -> dict:
    """Everything the Network screen needs in one call."""
    by = _events_by_org(items or [])
    ppl = []
    for p in people():
        c = card(p)
        orgs = {e.get("org") for e in p["career"] if e.get("org")}
        live = [it for o in orgs for it in by.get(o, [])[:1]]
        now = _now_entry(p)
        ppl.append({**c, "theme": (p.get("themes") or ["other"])[0], "themes": p.get("themes", []),
                    "level": max(e["level"] for e in p["career"]),
                    "symbols": sorted({_org(o).get("symbol") for o in orgs if _org(o).get("symbol") in PORTFOLIO or _org(o).get("symbol") in RESEARCH_SET}),
                    "live": len(live), "live_headline": live[0].get("headline") if live else None,
                    "live_symbol": live[0]["symbol"] if live else None, "org_now": _org_name(now)})
    cold = sorted((p for p in ppl if p["cold"] and p["strength"] >= 3), key=lambda x: (-x["strength"], -x["days_since"]))
    covered = {s for p in ppl for s in p["symbols"]}
    book = list(PORTFOLIO) + list(RESEARCH_SET)
    return {"investor": investor(), "people": ppl, "themes": themes(), "cold": cold[:5],
            "reconnect": warm(items or []),
            "stats": {"people": len(ppl), "lit": sum(1 for p in ppl if p["live"]),
                      "covered": len(covered & set(book)), "book": len(book),
                      "uncovered": [s for s in book if s not in covered]},
            "forgotten": len(_state()["forgotten"]),
            "synthetic": True}


# ------------------------------------------------------------------ direct questions

NETWORK_Q = re.compile(
    r"who (should|can|could|do|would|might|else) (i|we)\b|who .*\b(my network|i know)\b|\bwhom\b|anyone .*(i know|network)|"
    r"\bmy network\b|\bintroduc|\breconnect|\bgo-?to (people|person)|\bexperts? (on|in|for)\b|\bwho knows\b|"
    r"\bdo i know\b|\bhow (do|can) i (reach|get to)\b|\bpath to\b|\bcatch up with\b|\bgoing cold\b|lost touch|\bwho to call\b", re.I)


def is_network_question(q: str) -> bool:
    return bool(NETWORK_Q.search(q or ""))


def _plan_with_model(question: str) -> dict | None:
    """Free-form fallback: a cheap model maps the question to one tool call.
    It sees the question, theme names and company names. No contact data."""
    llm = get_llm()
    if not llm.available():
        return None
    orgs = [o["name"] for o in _raw()["orgs"].values() if o.get("kind") not in ("school", "firm")]
    prompt = f"""An investor asked their contact-network assistant: "{question}"
Pick ONE tool. Tools:
- company(name): who they know connected to a company. name must be one of: {orgs}
- theme(name): their go-to people on a topic. name must be one of: {[t['theme'] for t in themes()]}
- reconnect(): people they have not spoken to who are worth calling now
- none(): not a question about their network
Return JSON only: {{"tool": "company|theme|reconnect|none", "name": "..."}}"""
    try:
        return llm.json(prompt, tier="fast", purpose="network_plan", max_tokens=100)
    except Exception:
        return None


def ask(question: str, symbol: str | None = None, items: list[dict] | None = None) -> dict:
    q = question.strip()
    ql = q.lower()
    if re.search(r"reconnect|catch up|going cold|lost touch|haven'?t (spoken|talked)|keep.*warm|not spoken", ql):
        w = warm(items or [])
        cold = overview(items)["cold"]
        ppl = w or cold
        return {"kind": "network", "tool": "reconnect",
                "answer": (f"{len(w)} people going cold whose employer filed this week."
                           if w else "No filing to use as an excuse this week. Your strongest ties going cold:"),
                "people": ppl}
    # a person named in a recent filing, or one of your own contacts
    for p in people():
        if _norm_name(p["name"]) in _norm_name(q) or (len(p["name"].split()[0]) > 3 and re.search(rf"\b{re.escape(p['name'].lower())}\b", ql)):
            return {"kind": "network", "tool": "person", "answer": f"{p['name']}: {p['how']}. Last spoke {_ago(_days_since(p['last_contact']))}.",
                    "people": [{**card(p), "why": card(p)["now"], "knows": _now_entry(p).get("knows", ""), "label": "In your network"}]}
    for sym in list(PORTFOLIO) + list(RESEARCH_SET):
        for x in seen_people(sym):
            last = _norm_name(x["person"]).split()[-1] if _norm_name(x["person"]) else ""
            if _norm_name(x["person"]) in _norm_name(q) or (len(last) > 4 and re.search(rf"\b{last}\b", ql)):
                link = link_person(x["person"], x.get("background") or "", sym, x.get("event"))
                n = len(link["links"])
                strong = [l for l in link["links"] if l["confirmed"]]
                who = _norm_name(x["person"]).title()
                return {"kind": "network", "tool": "path", "link": link, "symbol": sym,
                        "answer": (f"You do not know {who} directly. {n} route{'s' if n != 1 else ''} in, {len(strong)} with dates that overlap."
                                   if n else f"You do not know {who}, and nobody in your network overlaps with the career in the filing."),
                        "people": []}
    hits = [h for h in find_orgs(q) if _org(h["org"]).get("kind") not in ("school",)]
    m = re.search(r"(?:reach|introduc\w*(?: me)? to|path to|get to|know)\s+((?:[A-Z][a-z'’]+\s?){2,3})", q)
    if m and not hits:
        return {"kind": "network", "tool": "path", "people": [],
                "answer": f"{m.group(1).strip()} is not in your network and has not appeared in a filing FINN has read, so there is no career to match against."}
    target_sym = None
    m = re.search(r"\b([A-Z][A-Z&]{2,11})\b", q)
    if m and m.group(1) not in ("NSE", "BSE", "CEO", "CFO", "USFDA", "EPC", "NBFC", "FMCG", "PSU"):
        target_sym = m.group(1)
    if hits or target_sym or (symbol and re.search(r"\b(this|here|it|them|the company)\b|^who (should|can|do) i (call|speak|talk|ask)", ql)):
        if hits:
            oid = hits[0]["org"]
            ppl = who_to_call(_org(oid).get("symbol"), org_id=oid)
            name = _org(oid)["name"]
        else:
            sym = target_sym or symbol
            ppl = who_to_call(sym)
            name = company_name(sym)
        direct = [p for p in ppl if p["relation"] in ("inside", "alumni")]
        ans = (f"{len(direct)} worked at {name}, {len(ppl) - len(direct)} around it." if ppl
               else f"Nobody in your network is connected to {name}.")
        return {"kind": "network", "tool": "company", "answer": ans, "people": ppl[:6]}
    ex = expertise(q)
    if ex["people"] and ex["themes"]:
        return {"kind": "network", "tool": "theme", "themes": ex["themes"],
                "answer": f"Your go-to people on {', '.join(ex['themes'][:2])}: {len(ex['people'])} in the network.", "people": ex["people"][:6]}
    plan = _plan_with_model(q)
    if plan and plan.get("tool") == "company" and plan.get("name"):
        for h in find_orgs(plan["name"]):
            ppl = who_to_call(_org(h["org"]).get("symbol"), org_id=h["org"])
            return {"kind": "network", "tool": "company", "planned": True,
                    "answer": f"{len(ppl)} people connected to {_org(h['org'])['name']}.", "people": ppl[:6]}
    if plan and plan.get("tool") == "theme" and plan.get("name"):
        ex = expertise(plan["name"])
        return {"kind": "network", "tool": "theme", "themes": ex["themes"], "planned": True,
                "answer": f"Closest theme in your network: {plan['name']}.", "people": ex["people"][:6]}
    if plan and plan.get("tool") == "reconnect":
        return ask("reconnect", symbol, items)
    if ex["people"]:
        return {"kind": "network", "tool": "theme", "answer": "Closest matches by role and experience.", "people": ex["people"][:6]}
    return {"kind": "network", "tool": "none", "people": [],
            "answer": "Nobody in your network matches that. Try a company, a person named in a filing, or a theme such as "
                      + ", ".join(t["theme"] for t in themes()[:4]) + "."}
