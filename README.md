# FINN — a financial investment agent for Indian equities

Mobile-first prototype for the ENAM AI Engineer Build Challenge.

FINN watches a portfolio of NSE-listed companies and works in two modes:

* **Push** — it tells you what changed and why you should care: a windowed digest of every exchange filing, triaged into *needs attention / worth a glance / routine (hidden)*, plus threshold alerts on end-of-day price and volume that *you* define.
* **Pull** — on-demand research on any NSE company, grounded only in primary sources (annual report + the last four earnings-call transcripts + standardised financials). Its centrepiece is a **promised-vs-delivered ledger**: what management guided on each call, against what the next quarter actually printed.

Every pushed filing is a doorway into the research: *Ask FINN* on a card pre-loads a question about that filing against the company's fundamentals.

## Run it

```bash
# backend
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
cp .env.example .env          # add ANTHROPIC_API_KEY or GEMINI_API_KEY (optional, see below)
.venv/bin/uvicorn backend.app:app --port 8000

# frontend (dev, with hot reload)   — or `npm run build` once and the API serves web/dist
cd web && npm install && npm run dev
```

Open http://localhost:5173 (dev) or http://localhost:8000 (built). It is laid out for a phone; on a desktop it renders as a phone-width column. To try it on your phone, run it on your laptop and open `http://<laptop-ip>:8000`, or `docker build -t finn . && docker run -p 8000:8000 --env-file .env -v finn-data:/data finn` and deploy the image anywhere (Render, Fly, Railway).

Pre-build everything the demo touches so first open is instant:

```bash
.venv/bin/python scripts/warm.py             # digests + research for all 25 companies
.venv/bin/python scripts/warm.py POLYCAB      # one company
```

### Model providers

`backend/llm.py` picks a provider automatically:

| configured | fast tier (bulk extraction) | smart tier (synthesis / Q&A) |
|---|---|---|
| `ANTHROPIC_API_KEY` | `claude-haiku-5-5` | `claude-opus-5-5` |
| `GEMINI_API_KEY` | `gemini-flash-latest` | `gemini-pro-latest` |
| `claude` CLI logged in | haiku | opus (runs on a Claude subscription, zero API spend) |
| nothing | rule-based triage, numbers-only research |

Every model call is cached on a hash of its input, so a transcript is read once, ever. `/api/usage` reports calls, tokens and cost per model and per purpose.

## How it works

```
                       PUSH                                          PULL
NSE corporate-announcements API ─┐                  screener.in ── tables (quarters, P&L, BS, CF, ratios)
yfinance EOD prices/volumes ─────┤                            └── links: annual report, concall transcripts
                                 ▼                                              │
   classify.py  rules on NSE type + subject → 17 categories, base priority      ▼
   digest.py    window filter, dedupe, mute, tiers            docs.py   PDF → text (pypdf, poppler fallback)
        │  survivors only                                              AR: opening pages + MD&A section only
        ▼                                                                       │
   enrich.summarise   FAST model, 12 filings/call → headline, why, materiality  ▼
   enrich.results_numbers  FAST model reads the results PDF → Rev/EBITDA/PBT/PAT  research.extract_transcript  FAST, per call
                           QoQ & YoY computed in Python; screener fallback        research.extract_annual_report FAST
   enrich.management_change FAST model reads the Reg-30 annexure → bio             research.compute_facts  Python: CAGRs, D/E,
   prices.summarise  volume × trailing avg, |move| vs threshold → alerts                                  CFO/PAT, cash cycle, YoY
                                                                                 research.synthesise  SMART model, once per company
                                                                                        → 8 sections + ledger + bull/bear + questions
                                                                                 research.ask  SMART model over the cached extractions
```

Design choices worth knowing:

* **Rules first, model second.** NSE already types every filing. Regexes on that plus the subject line classify ~95 % of filings for free and decide what is routine. Only survivors get a (cheap) model call, batched twelve at a time.
* **Instant digest, background detail.** `/api/digest` assembles from caches and returns in milliseconds with `complete: false`; model work runs in a thread and the UI polls. A 15-minute warm loop keeps the default windows fresh.
* **Numbers are computed, not generated.** QoQ/YoY, CAGRs, leverage, cash conversion and the quarterly YoY table are all Python over screener's tables. The strong model sees a compact numbers block plus per-document extractions — never a 500-page PDF — and is told not to do arithmetic or use outside knowledge.
* **Management-change bios come from the filing.** SEBI's Reg-30 format mandates a brief profile of the appointee; that is more reliable than scraping LinkedIn and is still primary data.
* **Thresholds are the user's.** Price-move %, volume multiple, lookback window and the filing categories that alert immediately are all editable in the Alerts tab and persist server-side.

## Layout

```
backend/
  app.py            FastAPI: /api/digest /api/research/{sym} /api/ask /api/settings /api/usage; serves web/dist
  config.py         demo portfolio (20) + research set (5), default thresholds
  llm.py            provider router, two tiers, content-addressed cache, usage ledger
  store.py          on-disk JSON/bytes cache + settings
  sources/          nse.py  prices.py  screener.py  docs.py
  engine/           classify.py  enrich.py  digest.py  research.py
web/src/            App.jsx  Today.jsx  Alerts.jsx  Research.jsx  Ask.jsx  ui.jsx  styles.css
scripts/warm.py     pre-build caches
```

The engine is not tied to the demo lists: `/api/research/POLYCAB/build` works for any symbol screener.in knows.

## Limits

* NSE's API needs a cookie handshake and occasionally rate-limits; failures are reported per symbol in the digest and retried on the next refresh. BSE's API blocks non-browser clients, so filings come from NSE only.
* Scanned-image PDFs yield no text; results then fall back to screener's standardised table once it has the quarter.
* Company-hosted transcript links on screener.in are sometimes dead or block scripts; FINN then looks for the copy the company filed with NSE. Companies that hold no earnings calls (e.g. ITC) get research from the annual report and numbers only.
* Malformed model JSON is retried with the parse error fed back; large PDF downloads are verified against Content-Length.
* Prices are end-of-day (yfinance), so price/volume alerts fire after close, not intraday.
* The ledger judges guidance against reported numbers; where guidance is qualitative it judges direction and says so.
