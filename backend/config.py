"""Static configuration: the demo portfolio, the ad-hoc research set, defaults.

Nothing in the engine is hard-wired to these lists. They only seed the UI; any
NSE symbol can be researched on demand (see /api/research/{symbol}).
"""
from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.getenv("FINN_DATA_DIR", ROOT / "data"))
CACHE_DIR = DATA_DIR / "cache"
SETTINGS_FILE = DATA_DIR / "settings.json"
# A snapshot of warmed caches shipped with the repo/image (see scripts/make_seed.py).
# Copied into CACHE_DIR on first start so a fresh deploy is populated at once.
SEED_DIR = Path(os.getenv("FINN_SEED_DIR", ROOT / "seed" / "cache"))
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# symbol -> (display name, sector, size bucket)
PORTFOLIO: dict[str, tuple[str, str, str]] = {
    "RELIANCE": ("Reliance Industries", "Energy / Conglomerate", "Mega"),
    "TCS": ("Tata Consultancy Services", "IT Services", "Mega"),
    "INFY": ("Infosys", "IT Services", "Large"),
    "HDFCBANK": ("HDFC Bank", "Banking", "Mega"),
    "ICICIBANK": ("ICICI Bank", "Banking", "Large"),
    "BAJFINANCE": ("Bajaj Finance", "NBFC", "Large"),
    "HINDUNILVR": ("Hindustan Unilever", "FMCG", "Large"),
    "ITC": ("ITC", "FMCG / Conglomerate", "Large"),
    "MARUTI": ("Maruti Suzuki", "Autos", "Large"),
    "SUNPHARMA": ("Sun Pharma", "Pharma", "Large"),
    "LT": ("Larsen & Toubro", "Infra / Capital Goods", "Large"),
    "TATASTEEL": ("Tata Steel", "Metals", "Large"),
    "HINDALCO": ("Hindalco", "Metals", "Large"),
    "DLF": ("DLF", "Real Estate", "Large"),
    "ETERNAL": ("Eternal (Zomato)", "Consumer Internet", "Large"),
    "DIXON": ("Dixon Technologies", "Electronics Mfg", "Mid"),
    "KPITTECH": ("KPIT Technologies", "Auto Software", "Mid"),
    "IRCTC": ("IRCTC", "Travel / PSU", "Mid"),
    "PIIND": ("PI Industries", "Agrochemicals", "Mid"),
    "VBL": ("Varun Beverages", "Beverages", "Large"),
}

# Companies outside the portfolio used to demo on-demand research.
RESEARCH_SET: dict[str, tuple[str, str, str]] = {
    "ASIANPAINT": ("Asian Paints", "Paints", "Large"),
    "POLYCAB": ("Polycab India", "Cables & Wires", "Mid"),
    "TITAN": ("Titan Company", "Jewellery / Retail", "Large"),
    "JIOFIN": ("Jio Financial Services", "Financial Services", "Large"),
    "NYKAA": ("Nykaa (FSN E-Commerce)", "Beauty E-commerce", "Mid"),
}

DEFAULT_SETTINGS = {
    "portfolio": list(PORTFOLIO.keys()),
    "window_hours": 24,
    "thresholds": {
        "volume_multiple": 2.0,   # alert when volume > N x trailing average
        "price_move_pct": 4.0,    # alert when |close-to-close move| > X %
        "lookback_days": 20,      # trailing window for the volume average
    },
    # categories that should trigger an alert the moment they appear
    "alert_categories": [
        "results", "M&A", "management_change", "fund_raise",
        "litigation", "credit_rating", "pledging",
    ],
    # categories the digest collapses by default
    "muted_categories": ["unclassified", "investor_meetings", "postal_ballot"],
}

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/130.0 Safari/537.36"
)


def company_name(symbol: str) -> str:
    sym = symbol.upper()
    if sym in PORTFOLIO:
        return PORTFOLIO[sym][0]
    if sym in RESEARCH_SET:
        return RESEARCH_SET[sym][0]
    return sym
