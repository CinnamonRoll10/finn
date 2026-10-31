**To:** assessment@enam.com
**Subject:** ENAM - IIT screening - 2027

Hi ENAM team,

Please find my submission for the AI Engineer Build Challenge: **FINN**, a mobile-first financial investment agent for NSE equities.

**Links**
- Repository: https://github.com/CinnamonRoll10/finn
- Prototype: <DEMO URL — see "Deploy or demo" in the repo README; paste the public URL here>
- AI build history: attached (`session-export-*.zip`, the full Claude Code session) and summarised in `build-history/transcript.md` in the repo.
- Covering note: `COVERING_NOTE.md` in the repo (also pasted below).

**What I built**
FINN works in two modes. *Push*: a windowed digest of every exchange filing across a 20-stock portfolio, triaged so results, M&A, management changes and litigation surface first and routine paperwork is hidden, with headline numbers (Revenue, EBITDA, PBT, PAT, QoQ and YoY) read from the results PDF and appointee bios read from the Reg-30 filing; plus end-of-day price and volume alerts against thresholds the user sets. *Pull*: on-demand research on any NSE symbol from primary sources only (annual report + last four concall transcripts + standardised financials), centred on a promised-vs-delivered ledger that grades each guidance statement against the quarter it applied to, and a grounded Q&A that cites its source for every claim.

**Key decisions**
- Rules before models: NSE's own filing types plus regexes classify ~95% of filings for free; only survivors get a model call.
- Two model tiers routed by job: a cheap model reads every document once (cached forever on content), a strong model synthesises once per company and answers questions. A full research build costs about $0.07 in API terms; the app exposes its own usage ledger.
- Numbers are computed in Python, never generated; the strong model is told it may not do arithmetic or use outside knowledge, and must tag every bullet with its source.
- Instant digest, background detail: triage returns in milliseconds and enriches while you read.

**Deliberately left out**: intraday prices and native push notifications, BSE filings (their API blocks scripts), news and broker research, auth and multi-user. **Next**: guidance as a first-class tracked object with "promise missed" alerts, a results-day diff of this call vs last call, batch-API warming, and a voice front-end over the grounded Q&A.

Thank you for the brief; it was a genuinely enjoyable problem.

Best regards,
<Your name>
<Phone> · <Institute / programme>
