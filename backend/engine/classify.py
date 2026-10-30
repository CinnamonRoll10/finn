"""Rule-based classification + priority scoring of NSE announcements.

NSE already labels every filing with a type ("desc"). Rules on that label plus
the subject line cover ~95% of filings deterministically and for free; only
the items that survive triage get a model call (see enrich.py), and the model
may refine the category and materiality.

Categories follow the companion reference document.
"""
from __future__ import annotations

import re

CATEGORIES = [
    "results", "M&A", "fund_raise", "management_change", "litigation",
    "insider_trading", "earnings_call", "investor_meetings", "credit_rating",
    "dividend", "bonus_split", "capex", "press_release", "postal_ballot",
    "agm_egm", "pledging", "unclassified",
]

# base priority 0-100 per category
BASE = {
    "results": 90, "M&A": 85, "management_change": 82, "fund_raise": 72,
    "litigation": 78, "credit_rating": 65, "pledging": 62, "capex": 60,
    "dividend": 55, "bonus_split": 55, "insider_trading": 50,
    "earnings_call": 42, "press_release": 40, "agm_egm": 25,
    "investor_meetings": 18, "postal_ballot": 18, "unclassified": 8,
}

RESULTS_RE = re.compile(r"financial results|results for the (quarter|year|half)|(un)?audited .{0,40}results", re.I)
BOARD_SCHEDULED_RE = re.compile(r"(meeting of (the )?board|board meeting|board of directors).{0,120}(scheduled|will be held|to be held|is being held|to consider)", re.I)
CALL_RE = re.compile(r"transcript|earnings call|conference call|concall|audio recording|video recording", re.I)
ORDER_RE = re.compile(r"\border(s)?\b.{0,60}(worth|valued|aggregat|rs\.?|₹|crore|cr\b|million|billion)|bagging|contract", re.I)
CLARIF_RE = re.compile(r"clarification|rumou?r|news (item|article|report)", re.I)
AD_RE = re.compile(r"newspaper|advertisement|publication of", re.I)
WINDUP_RE = re.compile(r"strike.?off|struck off|dissol|liquidat|wound up|winding up|closure of (a )?(wholly|subsidiary|step)", re.I)
RESIGN_RE = re.compile(r"resign|cessation|steps? down|retire|demise|vacat", re.I)
APPOINT_RE = re.compile(r"appoint|elevat|re-?designat|new (ceo|cfo|md|chairman)", re.I)
KMP_RE = re.compile(r"\b(ceo|cfo|md|managing director|chief (executive|financial|operating)|chairman|whole.?time director|company secretary|executive director)\b", re.I)
INDEP_RE = re.compile(r"independent director|non-executive", re.I)

TYPE_RULES: list[tuple[re.Pattern, str]] = [
    (re.compile(r"financial results", re.I), "results"),
    (re.compile(r"investor presentation", re.I), "results"),
    (re.compile(r"acquisition|amalgamation|merger|demerger|scheme of arrangement|joint venture|restructuring|sale or disposal|disposal|divest|incorporation|investment in", re.I), "M&A"),
    (re.compile(r"change in management|appointment|resignation|cessation|change in director|key managerial|kmp", re.I), "management_change"),
    (re.compile(r"litigation|penalt|order passed|action.? initiated|show cause|legal|insolvenc|arbitration|regulatory", re.I), "litigation"),
    (re.compile(r"insider trading|sast|substantial acquisition", re.I), "insider_trading"),
    (re.compile(r"credit rating- others", re.I), "unclassified"),
    (re.compile(r"credit rating", re.I), "credit_rating"),
    (re.compile(r"dividend", re.I), "dividend"),
    (re.compile(r"bonus|split|sub-?division", re.I), "bonus_split"),
    (re.compile(r"capacity|expansion|capex|new (plant|facility|unit)|commissioning", re.I), "capex"),
    (re.compile(r"pledge|encumbr", re.I), "pledging"),
    (re.compile(r"postal ballot", re.I), "postal_ballot"),
    (re.compile(r"shareholders? meeting|general meeting|agm|egm", re.I), "agm_egm"),
    (re.compile(r"esop|esos|espx|esps|employee stock", re.I), "unclassified"),
    (re.compile(r"issue of securities|allotment of securities|rights issue|qip|qualified institution|preferential|buy ?back|commercial paper|fund rais|raising of fund|debenture|ncd|bond", re.I), "fund_raise"),
    (re.compile(r"analyst|investor meet|con\.? call", re.I), "investor_meetings"),
    (re.compile(r"bagging|order|contract|press release|updates?$|general updates|clarification|rumou?r|media", re.I), "press_release"),
    (re.compile(r"record date", re.I), "dividend"),
    (re.compile(r"newspaper|certificate|compliance|trading window|monitoring agency|annual report|business responsibility|reg\.? ?\d|loss of share|duplicate|reconciliation|deviation|guarantee|indemnity|surety|letter of comfort", re.I), "unclassified"),
]


def classify(item: dict) -> dict:
    """Attach category, sub-type, base score to an announcement (in place)."""
    t = item.get("nse_type") or ""
    subj = item.get("subject") or ""
    both = f"{t} {subj}"
    cat, sub = "unclassified", None

    if RESULTS_RE.search(subj) and not re.search(r"investor presentation|press release|newspaper", t, re.I):
        cat = "results"
        sub = "scheduled" if BOARD_SCHEDULED_RE.search(subj) and not re.search(r"approved|submitted|outcome", subj, re.I) else "filed"
    elif CALL_RE.search(subj):
        cat, sub = "earnings_call", "transcript" if re.search(r"transcript", subj, re.I) else "recording"
    else:
        for pat, c in TYPE_RULES:
            if pat.search(t):
                cat = c
                break
        if cat == "unclassified":
            for pat, c in TYPE_RULES:
                if pat.search(subj):
                    cat = c
                    break
    if re.search(r"investor presentation", t, re.I):
        cat, sub = "results", "deck"
    if cat == "results" and AD_RE.search(subj):
        sub = "ad"
    if cat == "M&A" and WINDUP_RE.search(subj):
        sub = "windup"
    if cat == "dividend" and re.search(r"record date", t, re.I) and not re.search(r"dividend", subj, re.I):
        cat = "unclassified"
    if cat == "press_release":
        if ORDER_RE.search(subj):
            sub = "order_win"
        elif CLARIF_RE.search(subj):
            sub = "clarification"
    if cat == "management_change":
        sub = "kmp" if KMP_RE.search(subj) and not INDEP_RE.search(subj) else "board"
    if cat == "fund_raise" and re.search(r"allotment|commercial paper|debenture|ncd", both, re.I) and not re.search(r"qip|rights|preferential|buy ?back", both, re.I):
        sub = "routine_debt"

    score = BASE[cat]
    if cat == "results" and sub == "scheduled":
        score = 30
    elif cat == "results" and sub == "ad":
        score = 15
    elif cat == "M&A" and sub == "windup":
        score = 42
    elif cat == "results" and sub == "deck":
        score = 50
    elif cat == "press_release" and sub == "order_win":
        score = 58
    elif cat == "press_release" and sub == "clarification":
        score = 48
    elif cat == "management_change" and sub == "kmp":
        score = 88
    elif cat == "management_change" and RESIGN_RE.search(subj) and sub == "board":
        score = 70
    elif cat == "fund_raise" and sub == "routine_debt":
        score = 35
    elif cat == "M&A" and re.search(r"wholly owned subsidiary|incorporation", subj, re.I):
        score = 55
    item.update({"category": cat, "subtype": sub, "rule_score": score})
    return item


def tier_for(score: float) -> str:
    if score >= 70:
        return "attention"
    if score >= 40:
        return "glance"
    return "routine"
