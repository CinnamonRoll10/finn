# FINN — AI build history

Readable export of the Claude Code session in which FINN was built (30–31 Oct 2026). User prompts, the assistant's narration, and every tool call it made (file writes, shell commands, browser checks). Tool outputs, screenshots, injected reference material and the model's private reasoning are omitted for length; the raw session export (JSONL) is attached to the submission email.

## User

@"/Users/prakritiprasad/Downloads/1. ENAM_AI_Engineer_Build_Challenge_Main.pdf" @"/Users/prakritiprasad/Downloads/2. ENAM_AI_Engineer_Build_Challenge_Reference.pdf"
pls complete it

**Claude:** I'll extract the two challenge PDFs to see what the build challenge asks for, then build it in this project folder.

- `Bash` — Extract text from the main challenge PDF
- `Bash` — Extract text from the reference PDF
- `Bash` — Inspect project folder, git state, and tool availability
- `Bash` — Look for existing API keys, project conventions, and installed Python packages
- `Bash` — Check which LLM env vars are set (names only) and installed packages
- `Bash` — Peek at sibling projects for stack conventions
- `Bash` — Check LLM env var presence, installed Python packages, and CLI tools
- `Bash` — See how the sibling bot invokes Claude CLI and Gemini
- `Bash` — Create venv and install Python dependencies for the project
- `Bash` — Probe BSE, NSE announcement APIs and screener.in reachability
- `Bash` — Test whether the Claude Code CLI can answer non-interactively
- `Bash` — Parse screener.in page structure for tables and document links
- `Bash` — Test NSE PDF download with pypdf and yfinance EOD download
- `Bash` — Inspect screener document list structure and test transcript and annual report PDF downloads
- `Bash` — Fetch two weeks of NSE announcements for a 20-stock portfolio and tally announcement types
- `Skill`
- `Bash` — Create backend package skeleton with config and cache store
- `Bash` — List section headings of the Python SDK reference
- `Bash` — Read basic request, thinking, error handling, and fallback sections of the Python reference
- `Bash` — Check Claude CLI flags for non-interactive, tool-less calls
- `Bash` — Write the LLM router module with tiers, caching, and usage ledger
- `Bash` — Write NSE announcements client and yfinance price/anomaly module
- `Bash` — Write screener.in scraper and PDF document extraction modules
- `Bash` — Switch CLI call to bare mode with a system prompt and smoke-test the router
- `Bash` — Test screener scraping, transcript extraction, and annual report MD&A location
- `Bash` — Debug which CLI flag combination fails
- `Bash` — Inspect where MD&A and overview headings appear in a sample annual report
- `Bash` — Fix CLI flags and MD&A heading detection, then re-test both
- `Bash` — Write classification/scoring rules and model-backed enrichment
- `Bash` — Write the digest builder with triage, enrichment, tape, and alerts
**Claude:** Writing the research pipeline and the API server now, while a first full digest build (3-day window, with model enrichment) runs to test the push side end to end.

- `Bash` — Build a 3-day digest end to end with model enrichment and print the triage
- `Bash` — Write the research pipeline: facts, extraction, synthesis, build, ask
- `Bash` — Write the FastAPI app and requirements file
**Claude:** While the digest builds, I'll kick off a research build for Dixon in the background to test the pull side, and scaffold the Vite frontend.

- `Bash` — Build research for Dixon end to end and print the synthesis
- `Bash` — Scaffold a Vite React frontend and install its dependencies
**Claude:** Now the frontend. I'll write the whole mobile-first React app: shared styles and helpers, the four screens (Today, Alerts, Research, Ask), and the Vite proxy config, in one pass.

- `Bash` — Write Vite config, HTML shell, API client, and formatting helpers
- `Bash` — Write the design system stylesheet
- `Bash` — Write shared UI primitives and the app shell with bottom navigation
- `Bash` — Write the Today (digest) and Alerts screens
- `Bash` — Write the Research and Ask screens
**Claude:** Both backend tests finished. Let me check the outputs.

- `Bash` — Read the digest build output
- `Bash` — Read the Dixon research build output
- `Bash` — Patch classification regex, unit handling, screener fallback checks, and per-item caching
- `Bash` — Rewrite the digest builder with instant assembly and background enrichment
- `Bash` — Add digest polling in the UI, a background warm loop in the server, and a warm script
- `Bash` — Clear stale digest cache and build the frontend
- `Bash` — Create the launch config and verify the app imports
- `Bash` — Fix the syntax error and unit-test the classification and results helpers
- `Skill`
- `browser.preview_start`
- `Bash` — Write the launch config at the session root
- `browser.preview_start`
**Claude:** Starting the API server from my shell instead, and pointing the browser pane at it.

- `Bash` — Start the FastAPI server in the background and check it responds
- `browser.preview_start`
- `Bash` — Request the 3-day digest and time the instant response
- `Bash` — Down-rank results newspaper ads and subsidiary wind-ups in the rules
- `browser.resize_window`
- `browser.computer`
- `browser.read_console_messages`
- `Bash` — Improve results fallback headlines, restart the server, and check the 24h digest
- `Bash` — Start pre-building research for all 24 remaining companies in the background
**Claude:** Summaries are in and the digest returns instantly. Now I'll check the enriched cards and the Research and Ask screens in the browser, and start on the README in parallel.

- `browser.browser_batch`
- `Bash` — Inspect enriched results cards, alerts, and LLM usage ledger
- `Bash` — Debug why the Sun Pharma results filing produced no numbers
- `browser.browser_batch`
- `Bash` — Add a pdftotext fallback for broken PDFs, re-extract Sun Pharma, and restart the server
- `Bash` — Test poppler directly on the Sun Pharma PDF and clear the bad cache entry
- `Bash` — Compare the cached Sun Pharma PDF size against the server's declared length
- `browser.browser_batch`
- `Bash` — Write gitignore, env example, and Dockerfile
- `Bash` — Verify PDF downloads against Content-Length, purge the truncated file, and re-extract Sun Pharma results
- `browser.browser_batch`
- `Bash` — Write the README
**Claude:** Sun Pharma's numbers now extract correctly after the download fix. Now checking the Research screen in the browser, checking the background research warm-up, and drafting the covering note.

- `browser.computer`
- `Bash` — Check research warm-up progress and server log
- `Bash` — Write the covering note draft
- `browser.browser_batch`
- `Bash` — Widen results extraction window and test the grounded Ask endpoint
- `Bash` — Restart the API server with the latest code
- `Bash` — Initialise the git repository and make the initial commit
- `Write` — /Users/prakritiprasad/.claude/projects/-Users-prakritiprasad/memory/enam-finn-challenge.md
- `Bash` — Add the new memory to the index
- `browser.browser_batch`
- `Bash` — Check how many companies the background research warm-up has finished
- `browser.browser_batch`
- `Bash` — Confirm the warm script is still running and counting extractions
- `browser.browser_batch`
- `browser.browser_batch`
- `Bash` — Check the 7-day digest triage and category mix
- `browser.find` — Alerts
- `Bash` — Confirm the working tree is committed and report cache size
**Claude:** Final checks: the Alerts screen in the browser, then resetting the viewport and wrapping up.

- `browser.browser_batch`
- `browser.read_console_messages`
- `browser.resize_window`
- `Bash` — Drop the stale digest cache so Sun Pharma's numbers appear, and confirm
**Claude:** FINN is built and running. The repo is at [finn/](finn/), committed locally, and the app is live at http://localhost:8000 from a server I started in the background.

**What it does**

- **Today**: a windowed digest (24h, 3d, 7d, 30d, custom) of every NSE filing across a 20-stock portfolio, triaged into needs-attention, worth-a-glance, and routine (collapsed). Results cards show Revenue, EBITDA, PBT, PAT with QoQ and YoY read from the actual filing PDF. Management changes show the appointee's background read from the Reg-30 annexure.
- **Alerts**: you set the price-move %, volume multiple, lookback window and which filing types alert immediately. Triggered alerts show sparklines. Today VBL tripped both the price and volume thresholds.
- **Research**: any NSE symbol, built from the annual report MD&A plus the last four concall transcripts plus screener's tables. The centrepiece is a promised-vs-delivered ledger with met/missed verdicts and source tags on every bullet. Dixon's ledger caught the FY27 volume guide being nearly halved.
- **Ask**: grounded Q&A over that research. Every pushed filing has an "Ask FINN" door that pre-loads a question about that filing.

**Architecture choices the graders care about**: rules classify ~95% of filings for free, cheap-tier model (Haiku) reads documents once and caches forever, strong-tier (Opus) runs once per company on compact extractions and never does arithmetic. The usage ledger at `/api/usage` shows a full research build costs about $0.07. The digest returns instantly and enriches in the background.

**Deliverables written**: [README.md](finn/README.md), [COVERING_NOTE.md](finn/COVERING_NOTE.md) (draft of the email writeup), Dockerfile, `.env.example`, `scripts/warm.py`.

**Still running**: `scripts/warm.py` is pre-building research for the other 24 companies in the background. It takes roughly 3 minutes per company through the Claude CLI, so about an hour. Re-run it if it gets interrupted.

**Things only you can do before Sunday**:

1. Push the repo to GitHub.
2. Deploy, or demo from your laptop on the same Wi-Fi via `http://<laptop-ip>:8000`.
3. Export this Claude Code session as the "AI build history".
4. Send the email to <email> with subject "ENAM - IIT screening - 2027", using the covering note.

One caveat: the model provider on this Mac is the Claude Code CLI on your subscription. If you deploy, set `ANTHROPIC_API_KEY` or `GEMINI_API_KEY` in the environment, or ship the pre-warmed `data/` cache with the container.

## User

pls make the ui better its looking very ai generated its not attractive

**Claude:** The current look is generic: the same rounded dark cards, pills and Inter font every AI demo has. I'll redesign it with a point of view, an editorial "morning paper for your portfolio" feel: serif display type, a warm paper background, hairline rules instead of card soup, ledger-style mono numbers, and stamp-like verdicts.

- `Bash` — Rewrite the stylesheet with the editorial type system
- `Bash` — Rewrite shared UI primitives and the Today screen for the new design
- `Bash` — Rewrite the Alerts screen for the new design
- `Bash` — Rewrite the Research and Ask screens for the new design
- `Bash` — Build the redesigned frontend
- `browser.resize_window`
- `browser.resize_window`
- `browser.browser_batch`
**Claude:** The editorial look is working. Now the Today screen and dark mode.

- `browser.find` — Today
- `browser.browser_batch`
- `Bash` — Confirm the digest endpoint is serving and the server is healthy
- `Bash` — Shorten the results table header and rebuild
- `browser.find` — Research
- `browser.browser_batch`
- `browser.browser_batch`
- `browser.browser_batch`
**Claude:** Checking the charts tab and dark mode, then I'll commit.

- `browser.find` — Trajectory
- `browser.resize_window`
- `browser.browser_batch`
- `Bash` — Commit the redesign
- `Bash` — Fix dark-mode bar contrast and stat wrapping, rebuild, commit
- `browser.resize_window`
**Claude:** Redesigned and live at http://localhost:8000. Reload the page to see it.

**What changed**

- **A point of view instead of a template.** It now reads like a morning paper for your portfolio: a "Finn" masthead with the date line, a serif headline ("What changed."), an italic deck summarising the window, and sections ruled with hairlines. No rounded card soup, no pills.
- **Type does the work.** Fraunces (a display serif) for everything you read, IBM Plex Mono for everything you count, Plex Sans for body. Numbers sit in a proper ledger table with rules above and below, right-aligned, tabular.
- **One accent colour.** Warm paper and near-black ink, with a single rust accent for the active tab, the latest bar in charts, and links. Green and red appear only on numbers that moved.
- **Details with character.** Promised-vs-delivered verdicts are rubber-stamp boxes, slightly rotated. Bullets use an em-dash in the accent colour. Your questions in Ask are set in italic serif against a rust rule. The ticker tape is a mono strip with flagged stocks underlined in amber.
- **Dark mode** follows the system theme with the same palette inverted, checked in both.

Verified on a 375px phone viewport: Today with results tables, Alerts with thresholds, Research with the ledger and bar charts, and Ask. Committed as two commits on top of the earlier one.

## User

is the deliverable complete

- `Bash` — Check research warm-up results, server, and repo state
- `Bash` — Spot-check research quality for all companies and restart the server
**Claude:** Mostly, yes. The build is complete; the submission is not.

**Complete**

- Working prototype, four screens, redesigned, running again at http://localhost:8000 (the server had stopped overnight, I restarted it).
- Research pre-built for all 25 companies, so every demo company opens instantly.
- Repo with three commits, README, Dockerfile, `.env.example`, and the covering-note draft in [COVERING_NOTE.md](finn/COVERING_NOTE.md).

**Weak spots I found in the pre-built research**

- Polycab and Infosys each lost one transcript to a malformed model response. A retry would fix it.
- Maruti's transcripts are hosted on its own site and the links did not return a PDF, so its research rests on one call.
- TCS's July transcript link returned 403 from tcs.com.
- Eternal's annual-report extraction was refused by the model, so its research rests on transcripts and numbers.
- ITC has no concall transcripts on screener (it does not hold earnings calls), so its ledger is thinner by nature.

All five still render, with the gap listed in the sources footer.

**Not done, and only you can do them**

1. Push the repo to GitHub.
2. Deploy, or demo from your laptop.
3. Export this Claude Code session as the AI build history.
4. Email <email>, subject "ENAM - IIT screening - 2027", by Sunday.

## User

Yes, fix them

- `Bash` — Diagnose Maruti and TCS transcript links and the Eternal annual report excerpt
- `Bash` — Inspect the HTML wrapper Maruti serves instead of the transcript PDF
- `Bash` — Check text density and MD&A location in the Eternal annual report
- `Bash` — Add JSON retry to the model router and dedupe transcripts per call month
- `Bash` — Add NSE transcript fallback and smarter annual-report page selection, then test on Maruti and Eternal
- `Bash` — Match NSE transcript copies by nearest month, restart the server, and rebuild the five companies in the background
- `ToolSearch` — select:Monitor
**Claude:** The rebuild for the five companies is running in the background. I'll watch its log for each company's result and finish when it reports done.

- `Monitor` — per-company results of the research rebuild (Polycab, Infosys, Maruti, TCS, Eternal)
- `Bash` — Note the new fallbacks in the README limits section
**Claude:** Waiting on the rebuild now. Each company takes two to three minutes through the Claude CLI, so the five should finish in roughly fifteen minutes; I'll report as the results land.

**Claude:** Polycab rebuilt cleanly with all four transcripts. Waiting on the other four.

**Claude:** Infosys is clean too, four transcripts. Maruti is next, which exercises the new NSE fallback.

**Claude:** Maruti went from one transcript to three via the NSE copies. The August 2025 call has no NSE copy within the 15-month lookback, so it stays skipped and is listed in the sources footer. TCS and Eternal remain.

**Claude:** TCS is clean with four transcripts now that the blocked tcs.com duplicate is dropped in favour of the exchange copy. Eternal is last.

- `Bash` — Check the rebuild log for Eternal's result
**Claude:** All five rebuilt. Let me verify the Eternal annual-report extraction landed, re-run the quality check across all 25, and commit.

- `Bash` — Re-run the research quality check and commit the robustness fixes
**Claude:** Fixed and committed.

**What was wrong and what changed**

- **Polycab and Infosys** lost a transcript each to malformed JSON from the cheap model. The router now retries a bad answer with the parse error fed back. Both rebuilt with four transcripts and full ledgers.
- **TCS** had a duplicate July link on tcs.com that returns 403. Transcripts are now deduplicated per call month, preferring the exchange-hosted copy. Four transcripts, clean.
- **Maruti**'s transcript links on screener point at an Azure blob that now redirects to a spam site. When a link is dead, FINN looks for the copy the company filed with NSE and matches it by month. Maruti went from one transcript to three. The August 2025 call has no public copy left, and the footer says so.
- **Eternal**'s annual report has fifty image-only pages up front and no "Management Discussion" heading, so the model got an empty excerpt and refused. The extractor now skips image pages and falls back to the Board's Report. Eternal's research now has a proper business description and all four transcripts.
- **ITC** is unchanged. It holds no earnings calls, so its research rests on the annual report and numbers by design.

The quality check across all 25 companies now flags only those two structural gaps. Server is running on port 8000 with the new code, and the fixes are in a fourth commit.

## User

<pasted_content id="9624">
Not done, and only you can do them

1. Push the repo to GitHub.
2. Deploy, or demo from your laptop.
3. Export this Claude Code session as the AI build history.
4. Email <email>, subject “ENAM - IIT screening - 2027”, by Sunday.
</pasted_content id="9624">

 pls do them

**Claude:** Of the four, I can do the push and the transcript export myself. Deployment and the email depend on which accounts are logged in on this machine, so I'll check what's available first and draft the email either way.

- `Bash` — Check GitHub login and which hosting or tunnel CLIs are installed and logged in
- `ToolSearch` — select:mcp__ccd_session_mgmt__export_transcript

---
*5 user turns · 132 tool calls.*