# FINN — AI build history

Readable export of the Claude Code session in which FINN was built (30–31 Oct 2026). User prompts, the assistant's narration, and every tool call it made (file writes, shell commands, browser checks). Tool outputs, screenshots and the model's private reasoning are omitted for length; the raw session export (JSONL) is attached to the submission email.

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

## User

<task-notification>
<task-id>b2r4482yx</task-id>
<summary>Monitor event: "per-company results of the research rebuild (Polycab, Infosys, Maruti, TCS, Eternal)"</summary>
<event>POLYCAB: ok 4 transcripts, ledger 8, errors [] (117s)</event>
</task-notification>

**Claude:** Polycab rebuilt cleanly with all four transcripts. Waiting on the other four.

## User

<task-notification>
<task-id>b2r4482yx</task-id>
<summary>Monitor event: "per-company results of the research rebuild (Polycab, Infosys, Maruti, TCS, Eternal)"</summary>
<event>INFY: ok 4 transcripts, ledger 8, errors [] (174s)</event>
</task-notification>

**Claude:** Infosys is clean too, four transcripts. Maruti is next, which exercises the new NSE fallback.

## User

<task-notification>
<task-id>b2r4482yx</task-id>
<summary>Monitor event: "per-company results of the research rebuild (Polycab, Infosys, Maruti, TCS, Eternal)"</summary>
<event>MARUTI: ok 3 transcripts, ledger 7, errors ['transcript Aug 2025: not a PDF: https://marutistoragenew.blob.core.windows.net/msilintiwebpdf/Transcript_earnings_call_Ma'] (73s)</event>
</task-notification>

**Claude:** Maruti went from one transcript to three via the NSE copies. The August 2025 call has no NSE copy within the 15-month lookback, so it stays skipped and is listed in the sources footer. TCS and Eternal remain.

## User

<task-notification>
<task-id>b2r4482yx</task-id>
<summary>Monitor event: "per-company results of the research rebuild (Polycab, Infosys, Maruti, TCS, Eternal)"</summary>
<event>TCS: ok 4 transcripts, ledger 8, errors [] (169s)</event>
</task-notification>

**Claude:** TCS is clean with four transcripts now that the blocked tcs.com duplicate is dropped in favour of the exchange copy. Eternal is last.

## User

<task-notification>
<task-id>b2r4482yx</task-id>
<summary>Monitor event: "per-company results of the research rebuild (Polycab, Infosys, Maruti, TCS, Eternal)"</summary>
<event>[Monitor expired after 30m with 4 events delivered. Re-arm it if you still need the watch.]</event>
</task-notification>

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
*12 user turns · 147 tool calls.*