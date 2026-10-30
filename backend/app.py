"""FINN API + static frontend.

    uvicorn backend.app:app --reload --port 8000

Endpoints
  GET  /api/settings            PUT /api/settings
  GET  /api/digest?hours=24 | ?from=YYYY-MM-DD&to=YYYY-MM-DD
  GET  /api/companies
  GET  /api/research/{symbol}   POST /api/research/{symbol}/build
  POST /api/ask                 {symbol, question, history?, context?}
  GET  /api/usage
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
from .engine import digest, research
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
            for h in (24, 72):
                digest.build_digest(s, hours=h)
        except Exception:
            pass
        time.sleep(15 * 60)


@app.on_event("startup")
def _startup():
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
            return digest.build_digest(settings, start=date.fromisoformat(from_),
                                       end=date.fromisoformat(to) if to else date.today(), deep=deep)
        return digest.build_digest(settings, hours=hours, deep=deep)
    except Exception as e:
        raise HTTPException(502, f"digest failed: {e}")


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
    symbol: str
    question: str
    history: list[dict] | None = None
    context: str | None = None


@app.post("/api/ask")
def post_ask(body: AskBody):
    try:
        return research.ask(body.symbol.upper(), body.question, body.history, body.context)
    except LookupError:
        raise HTTPException(409, "Build research for this company first")
    except Exception as e:
        raise HTTPException(502, str(e)[:300])


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
