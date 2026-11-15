"""FINN API + static frontend.

    uvicorn backend.app:app --reload --port 8000

Endpoints
  GET  /api/settings            PUT /api/settings
  GET  /api/digest?hours=24 | ?from=YYYY-MM-DD&to=YYYY-MM-DD
  GET  /api/companies
  GET  /api/research/{symbol}   POST /api/research/{symbol}/build
  POST /api/ask                 {symbol, question, history?, context?}
  GET  /api/usage
  GET  /api/network             the investor's network + what today's filings light up
  GET  /api/network/company/{symbol}   GET /api/network/person/{id}
  POST /api/network/ask         {question, symbol?}
  POST /api/network/person/{id}/log    DELETE /api/network/person/{id}
"""
from __future__ import annotations

import threading
from datetime import date
from pathlib import Path

from fastapi import BackgroundTasks, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import llm as llm_mod
from . import store
from .config import PORTFOLIO, RESEARCH_SET, ROOT
from .engine import digest, network, research
from .sources import prices

app = FastAPI(title="FINN", version="0.1")


def _warm_loop():
    """Keep the default digest fresh so the first open of the day is instant."""
    import os, time
    if os.getenv("FINN_NO_WARM"):
        return
    while True:
        try:
            s = store.load_settings()
            for h in (24, 72, 168):
                digest.build_digest(s, hours=h)
            network.index_people_from_cache()
        except Exception:
            pass
        time.sleep(15 * 60)


@app.on_event("startup")
def _startup():
    store.seed()
    try:
        network.index_people_from_cache()
    except Exception:
        pass
    threading.Thread(target=_warm_loop, daemon=True).start()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


@app.get("/api/settings")
def get_settings():
    return store.load_settings()


@app.put("/api/settings")
def put_settings(body: dict):
    cur = store.load_settings()
    for k in ("window_hours", "alert_categories", "muted_categories", "portfolio"):
        if k in body:
            cur[k] = body[k]
    if "thresholds" in body:
        cur["thresholds"].update({k: float(v) for k, v in body["thresholds"].items()})
    return store.save_settings(cur)


@app.get("/api/digest")
def get_digest(hours: int | None = None, from_: str | None = Query(None, alias="from"),
               to: str | None = None, deep: bool = True):
    settings = store.load_settings()
    try:
        if from_:
            d = digest.build_digest(settings, start=date.fromisoformat(from_),
                                    end=date.fromisoformat(to) if to else date.today(), deep=deep)
        else:
            d = digest.build_digest(settings, hours=hours, deep=deep)
    except Exception as e:
        raise HTTPException(502, f"digest failed: {e}")
    # the Network is layered on at read time: it is deterministic, takes
    # milliseconds, and must reflect a contact logged or forgotten a second ago
    d = network.annotate_digest(d)
    if (d["window"].get("hours") or 0) < 168 and not from_:
        # a call is not a same-day reflex: the call sheet always looks back a week
        week = _recent_items(168)
        if week:
            d["call_sheet"] = network.call_sheet(week)
            d["call_sheet_window"] = "this week"
    return d


@app.get("/api/companies")
def companies():
    settings = store.load_settings()
    thresholds = settings["thresholds"]
    syms = list(dict.fromkeys(settings["portfolio"] + list(RESEARCH_SET.keys())))
    tape = {t["symbol"]: t for t in prices.market_tape(syms, thresholds)} if syms else {}
    out = []
    for s in syms:
        meta = PORTFOLIO.get(s) or RESEARCH_SET.get(s) or (s, "", "")
        out.append({"symbol": s, "name": meta[0], "sector": meta[1], "size": meta[2],
                    "in_portfolio": s in settings["portfolio"],
                    "research_ready": research.get_cached(s) is not None,
                    "tape": tape.get(s)})
    return out


@app.get("/api/research/{symbol}")
def get_research(symbol: str):
    symbol = symbol.upper()
    r = research.get_cached(symbol)
    st = research.status(symbol)
    return {"status": "ready" if r else st.get("state", "idle"), "progress": st, "data": r}


@app.post("/api/research/{symbol}/build")
def build_research(symbol: str, bg: BackgroundTasks, force: bool = False):
    symbol = symbol.upper()
    if not force and research.get_cached(symbol):
        return {"status": "ready"}
    st = research.status(symbol)
    if st.get("state") == "building":
        return {"status": "building", "progress": st}
    threading.Thread(target=lambda: _safe_build(symbol, force), daemon=True).start()
    return {"status": "building", "progress": research.status(symbol)}


def _safe_build(symbol: str, force: bool):
    try:
        research.build(symbol, force=force)
    except Exception:
        pass


class AskBody(BaseModel):
    symbol: str | None = None
    question: str
    history: list[dict] | None = None
    context: str | None = None


@app.post("/api/ask")
def post_ask(body: AskBody):
    """One box, two brains: questions about people go to the Network (graph
    lookups, no model), questions about the business go to the research."""
    sym = body.symbol.upper() if body.symbol else None
    if network.is_network_question(body.question) or not sym:
        return network.ask(body.question, sym, _recent_items())
    try:
        return research.ask(sym, body.question, body.history, body.context)
    except LookupError:
        raise HTTPException(409, "Build research for this company first")
    except Exception as e:
        raise HTTPException(502, str(e)[:300])


# ------------------------------------------------------------ network
def _recent_items(hours: int = 168) -> list[dict]:
    """Filings the Network reasons over: the last week, from cache when warm."""
    try:
        d = digest.build_digest(store.load_settings(), hours=hours, deep=False)
        return network.annotate_digest(d)["items"]
    except Exception:
        return []


@app.get("/api/network")
def get_network(hours: int = 168):
    return network.overview(_recent_items(hours))


@app.get("/api/network/company/{symbol}")
def network_company(symbol: str):
    symbol = symbol.upper()
    r = research.get_cached(symbol) or {}
    _recent_items()  # refreshes the index of people named in filings
    return network.company_view(symbol, about=r.get("about") or "",
                                questions=(r.get("sections") or {}).get("questions"))


@app.get("/api/network/person/{pid}")
def network_person(pid: str):
    p = network.person_view(pid, _recent_items())
    if not p:
        raise HTTPException(404, "not in your network")
    return p


class NetAsk(BaseModel):
    question: str
    symbol: str | None = None


@app.post("/api/network/ask")
def network_ask(body: NetAsk):
    return network.ask(body.question, body.symbol.upper() if body.symbol else None, _recent_items())


@app.post("/api/network/person/{pid}/log")
def network_log(pid: str):
    network.log_contact(pid)
    return network.person_view(pid, _recent_items())


@app.delete("/api/network/person/{pid}")
def network_forget(pid: str):
    network.forget(pid)
    return {"ok": True}


@app.post("/api/network/restore")
def network_restore():
    network.restore_all()
    return {"ok": True}


@app.get("/api/usage")
def usage():
    return llm_mod.usage_summary()


# ------------------------------------------------------------ frontend
WEB_DIST = ROOT / "web" / "dist"
if WEB_DIST.exists():
    app.mount("/assets", StaticFiles(directory=WEB_DIST / "assets"), name="assets")

    @app.get("/{path:path}")
    def spa(path: str):
        f = WEB_DIST / path
        if path and f.is_file():
            return FileResponse(f)
        return FileResponse(WEB_DIST / "index.html")
