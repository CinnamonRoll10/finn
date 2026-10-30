# FINN — covering note

**Links:** repository (this folder), prototype (run locally or via the Dockerfile; see README), AI build history (the Claude Code session transcript, exported alongside).

## What I built

FINN is a phone-first app with four screens and one point of view: *an investor's attention is the scarce resource, so every screen either saves it or spends it deliberately.*

* **Today** — a windowed digest (24h / 3d / 7d / 30d / custom) of every NSE filing across a 20-stock portfolio, triaged into *needs attention*, *worth a glance* and *routine* (hidden behind a count). Results filings get the four headline numbers with QoQ and YoY read from the actual PDF; management changes get the appointee's background read from the Reg-30 annexure; everything else gets a one-line "why it matters" or just the filing at the right priority. A market tape shows end-of-day moves with anomaly flags.
* **Alerts** — the user defines "unusual": price move ±X %, volume > N× the trailing average, and which filing categories alert immediately. Triggered alerts carry sparklines and the same *Ask FINN* door.
* **Research** — on-demand analysis of any NSE symbol from primary sources only (annual report + last four concall transcripts + standardised financials): snapshot, trajectory, balance sheet & cash, guidance, bull/bear, and the centrepiece, a **promised-vs-delivered ledger** that pairs each explicit guidance statement with what the next quarter actually printed and a verdict. Bullets carry source tags like `[Q1FY27 call]` or `[Numbers]`.
* **Ask** — grounded Q&A over that research. Tapping *Ask FINN* on any pushed filing jumps here with a question pre-loaded about *that* filing against the fundamentals, so push and pull are one workflow rather than two features.

## Key decisions and trade-offs

1. **Rules before models.** NSE already labels every filing by type. Regexes over type + subject classify ~95 % of filings for free, decide what is routine, and set a base priority; only survivors get a model call, batched twelve per request. A model never sees an ESOP allotment.
2. **Two model tiers, routed by job.** Cheap tier (Haiku / Gemini Flash) does all document reading: transcript extraction, annual-report extraction, results PDFs, bios, one-liners. The strong tier (Opus) runs exactly once per company, on compact extractions plus a numbers block, and for Q&A. Every call is cached on its input hash, so a transcript is read once, ever. Building full research for one company cost about $0.07 in API terms; a day's digest costs a few cents. `/api/usage` shows the ledger.
3. **Numbers are computed, not generated.** CAGRs, leverage, cash conversion, QoQ/YoY, the quarterly table — all Python over screener's tables. The strong model is told it may not do arithmetic or use outside knowledge, and must tag every bullet with its source. This is what makes the ledger trustworthy enough to show.
4. **Instant digest, background detail.** The digest endpoint returns triage in milliseconds and enriches in a thread; the UI polls until complete. A 15-minute warm loop keeps the default windows fresh. The first open of the day should never show a spinner.
5. **Bios from the filing, not LinkedIn.** SEBI's Reg-30 format requires a brief profile of the appointee. It is primary, it is reliable, and it is already in the PDF being surfaced.
6. **Web, not native.** A responsive React app served by the same FastAPI process, one Docker image, no app-store friction for a reviewer with a phone.

## What I deliberately left out

* Intraday prices and real push notifications (web push / Telegram). Alerts are computed at end of day and surfaced in-app with a badge; the hook for a notifier is one function.
* BSE filings (their API blocks non-browser clients) and investor-presentation parsing.
* Peer comparison, valuation models, and anything from news or broker research — the brief's discipline on primary sources is, I think, the right one.
* Authentication, multi-user portfolios, and a database; settings and caches are JSON on disk.

## Where I'd take it next

* **Guidance tracking as a first-class object:** persist each guidance statement with its quarter, auto-grade it when the next results filing lands, and push "promise missed" as its own alert type.
* **Results-day flow:** when a results PDF and the concall transcript arrive the same week, diff "what they said last quarter" against "what they said this quarter" automatically.
* **Cheaper still:** move transcript extraction to the Batch API (50 % off) and warm research for the whole portfolio overnight.
* **Voice on the move:** the Ask screen is already a grounded Q&A; a voice front-end for the commute is a small step.
