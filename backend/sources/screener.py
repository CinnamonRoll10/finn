"""screener.in: standardised multi-year financials + links to primary documents.

We scrape the consolidated page (falling back to standalone), keep every table
row verbatim (labels differ for banks/NBFCs), and collect the annual-report and
concall-transcript links. Cached for 24h.
"""
from __future__ import annotations

import re

import requests
from bs4 import BeautifulSoup

from .. import store
from ..config import USER_AGENT

HEADERS = {"User-Agent": USER_AGENT, "Referer": "https://www.screener.in/"}
TABLES = ["quarters", "profit-loss", "balance-sheet", "cash-flow", "ratios"]


class CompanyNotFound(Exception):
    pass


def _num(s: str) -> float | None:
    s = s.replace(",", "").replace("%", "").replace("₹", "").strip()
    if s in ("", "-", "—"):
        return None
    try:
        return float(s)
    except ValueError:
        return None


def _parse_table(section) -> dict | None:
    t = section.select_one("table") if section else None
    if not t:
        return None
    cols = [th.get_text(" ", strip=True) for th in t.select("thead th")][1:]
    rows: dict[str, list[float | None]] = {}
    order: list[str] = []
    for tr in t.select("tbody tr"):
        cells = tr.select("td")
        if not cells:
            continue
        label = re.sub(r"\s*\+\s*$", "", cells[0].get_text(" ", strip=True))
        # screener puts a long tooltip into some labels (e.g. CFO/EBITDA); keep the first words
        label = label.split(" Share of")[0].split(" Ratio of")[0].strip()
        if label.lower().startswith("raw pdf"):
            continue
        vals = [_num(td.get_text(" ", strip=True)) for td in cells[1:]]
        rows[label] = vals
        order.append(label)
    return {"columns": cols, "rows": rows, "order": order}


def _fetch_page(symbol: str, consolidated: bool) -> tuple[str, bool]:
    url = f"https://www.screener.in/company/{symbol}/" + ("consolidated/" if consolidated else "")
    r = requests.get(url, headers=HEADERS, timeout=30)
    if r.status_code == 404:
        raise CompanyNotFound(symbol)
    r.raise_for_status()
    return r.text, consolidated


def _scrape(symbol: str) -> dict:
    html, consolidated = _fetch_page(symbol, True)
    s = BeautifulSoup(html, "lxml")
    q = _parse_table(s.select_one("section#quarters"))
    if not q or not q["columns"]:
        html, consolidated = _fetch_page(symbol, False)
        s = BeautifulSoup(html, "lxml")
    name = (s.select_one("h1") or s.select_one("title")).get_text(" ", strip=True)
    name = re.sub(r"\s+share price.*$", "", name, flags=re.I)
    top = {}
    for li in s.select("#top-ratios li"):
        n, v = li.select_one(".name"), li.select_one(".value")
        if n and v:
            top[n.get_text(strip=True)] = v.get_text(" ", strip=True)
    about_el = s.select_one(".company-profile .about") or s.select_one("div.about")
    about = about_el.get_text(" ", strip=True) if about_el else ""
    pros = [li.get_text(" ", strip=True) for li in s.select(".pros ul li")]
    cons = [li.get_text(" ", strip=True) for li in s.select(".cons ul li")]
    tables = {t: _parse_table(s.select_one(f"section#{t}")) for t in TABLES}

    docs = s.select_one("section#documents")
    annual_reports, concalls = [], []
    if docs:
        for li in docs.select("li"):
            txt = li.get_text(" ", strip=True)
            links = {a.get_text(strip=True): a["href"] for a in li.select("a[href]")}
            m = re.search(r"Annual Report (\d{4})", txt)
            if m:
                url = next((h for h in links.values() if h.lower().endswith(".pdf") or "AnnualReport" in h or "corpfiling" in h), None)
                if url:
                    annual_reports.append({"year": int(m.group(1)), "url": url})
            elif "Transcript" in links:
                label = re.match(r"([A-Z][a-z]{2} \d{4})", txt)
                concalls.append({
                    "label": label.group(1) if label else txt[:8],
                    "transcript": links.get("Transcript"),
                    "ppt": links.get("PPT"),
                })
    annual_reports.sort(key=lambda a: -a["year"])
    # dedupe transcripts by url, keep order (newest first on screener)
    seen, uniq = set(), []
    for c in concalls:
        if c["transcript"] and c["transcript"] not in seen:
            seen.add(c["transcript"])
            uniq.append(c)
    sector = ""
    for a in s.select(".company-links a, .sub a"):
        pass
    return {
        "symbol": symbol,
        "name": name,
        "consolidated": consolidated,
        "about": about,
        "top": top,
        "pros": pros,
        "cons": cons,
        "tables": tables,
        "annual_reports": annual_reports[:3],
        "concalls": uniq[:6],
        "source": f"https://www.screener.in/company/{symbol}/" + ("consolidated/" if consolidated else ""),
    }


def get_company(symbol: str, ttl: float | None = 24 * 3600) -> dict:
    symbol = symbol.upper().strip()
    return store.cached("screener", symbol, ttl, lambda: _scrape(symbol))


# --------------------------------------------------------------- helpers

ROW_ALIASES = {
    "revenue": ["Sales", "Revenue"],
    "ebitda": ["Operating Profit", "Financing Profit"],
    "pbt": ["Profit before tax"],
    "pat": ["Net Profit"],
    "opm": ["OPM %", "Financing Margin %"],
    "other_income": ["Other Income"],
    "interest": ["Interest"],
    "depreciation": ["Depreciation"],
    "eps": ["EPS in Rs"],
}


def row(table: dict | None, key: str) -> list[float | None] | None:
    if not table:
        return None
    for alias in ROW_ALIASES.get(key, [key]):
        if alias in table["rows"]:
            return table["rows"][alias]
    return None
