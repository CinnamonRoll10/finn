# FINN — AI build history, session 2: the Network layer (15 Nov 2026)

Readable export of a Claude Code session. User prompts, the assistant's narration, and one line per tool call (file writes, shell commands, browser checks). Tool outputs, screenshots, injected reference material and the model's private reasoning are omitted for length; the raw session export is the complete record.

## User

@"/Users/prakritiprasad/Downloads/1. ENAM_Founding AI Engineer Build Challenge_Main.pdf" @"/Users/prakritiprasad/Downloads/2. ENAM_Build_Challenge_Reference.pdf"
pls look at the criteria in detail and later they also ask for link to ai build history so pls accordingly suggest me what to do and build whatever is asked

- `Read` — ~/Downloads/1. ENAM_Founding AI Engineer Build Challenge_Main.pdf
- `Read` — ~/Downloads/2. ENAM_Build_Challenge_Reference.pdf
- `Read` — ~/.claude/projects/-Users-prakritiprasad/memory/enam-finn-challenge.md
- `Bash` — Read git identity memory and inspect FINN project state
- `Bash` — Read README and list project files
- `Bash` — Read backend config, app, store, and llm modules
- `Bash` — Read digest, enrich, and classify engine modules
- `Bash` — Read frontend source files
- `Bash` — Read research view, research engine tail, and submission docs
- `Read` — ~/.claude/projects/-Users-prakritiprasad-Desktop-self-proj/50dc6dc7-cd30-46c0-9a5a-4d36418f4648/tool-results/bd6a9r08q.txt

## User

i think build from scratch i dont think that previous assignment is related or is it?

- `Bash` — Inspect cached data and management-change bios already extracted
- `Bash` — Start the FINN server and fetch a 30-day digest
- `Bash` — Check research dossier shape, digest item fields, and warm script
- `Write` — ~/Desktop/self proj/finn/seed/network.json
- `Write` — ~/Desktop/self proj/finn/backend/engine/network.py

**Claude:** Network engine is written; now wiring it into the API and testing it against the live 30-day digest before touching the UI.

- `Bash` — Wire network endpoints into the API and test the engine on live filings
- `Bash` — Tune ranking rules and test linking against real filing bios

**Claude:** Linking against real filing bios works (e.g. the incoming HDFC Bank MD's ICICI years matched to two contacts with overlapping dates). Fixing two date-parsing bugs it exposed, then moving to the UI.

- `Bash` — Fix date parsing, index people named in filings, re-test
- `Bash` — Dedupe filing people and extend the frontend API client
- `Write` — ~/Desktop/self proj/finn/web/src/net.jsx
- `Write` — ~/Desktop/self proj/finn/web/src/Network.jsx

**Claude:** The Network screen, person sheet and call-sheet components are written. Now wiring them into the existing Today, Alerts, Research and Ask screens.

- `Bash` — Wire network components into App, Today, Alerts, and Research
- `Write` — ~/Desktop/self proj/finn/web/src/Ask.jsx
- `Bash` — Add network styles and build the frontend

**Claude:** No response requested.

## User

continue

**Claude:** Frontend is built with the Network wired in. Restarting the server on the new code and checking it in a phone-width browser.

- `Bash` — Restart the server and smoke-test the network endpoints
- `preview_start` — http://localhost:8000
- `browser_batch` — resize_window, javascript_tool, computer, computer, read_console_messages
- `browser_batch` — computer, computer, find
- `browser_batch` — javascript_tool, computer, computer, computer, javascript_tool, computer
- `browser_batch` — javascript_tool, computer
- `Bash` — Polish the map, theme chips, and call-sheet clamp; rebuild
- `browser_batch` — resize_window, navigate, computer, javascript_tool, computer, computer

**Claude:** Person sheet, map and call sheet all render correctly on a phone-width screen. Fixing a duplicate "why now" entry, then checking the Research and Ask integrations.

- `Bash` — Dedupe live events on the person view and restart the server
- `browser_batch` — resize_window, javascript_tool, computer, javascript_tool, computer, javascript_tool
- `browser_batch` — computer, javascript_tool, computer, javascript_tool, computer, computer
- `Bash` — Drop weak alma-mater-only routes and restart
- `browser_batch` — resize_window, javascript_tool, computer, javascript_tool, computer, javascript_tool

**Claude:** Checking the Ask and Research screens once more (the last screenshots were captured mid-render), then on to the write-up and build history.

- `browser_batch` — computer, javascript_tool, computer
- `Bash` — Test ask routing, no-LLM mode, and the 7-day digest state
- `Bash` — Read usage ledger, 24h digest state, and locate session transcripts
- `Bash` — Locate this session's transcript file and inspect its format
- `Bash` — Search for this session's transcript file
- `Bash` — Update the README with the Network layer and architecture sections

**Claude:** README now covers the Network and the four architecture sections. Writing the covering email and the build-history exporter next.

- `Bash` — Write the covering email, the history exporter, and export this session
- `Bash` — Check why some assistant text is missing from the export
- `Bash` — Confirm digests have settled and regenerate the seed snapshot
- `Bash` — Let unit-specific matches surface on glance-tier filings; rebuild and restart
- `browser_batch` — resize_window, javascript_tool, computer, computer, javascript_tool, computer
- `Bash` — Refresh the seed and build-history export, and review what would be committed
- `Write` — ~/.claude/projects/-Users-prakritiprasad/memory/enam-finn-challenge.md

**Claude:** Everything is built and verified locally. Fixing one link in the email (the repo's branch is `master`, not `main`), then wrapping up.

- `Bash` — Fix the build-history link and update the memory index

**Claude:** The Network layer is built on top of your existing FINN and runs locally against live NSE filings, but nothing is committed or pushed yet, so the Render demo still shows the old version. The deadline is today.

## Is it the same assignment?
Yes. The new brief keeps Push, Pull, the data sources and the glossary, and adds a third layer (the Network), four architecture sections in the write-up, and a new subject line. I extended the existing build instead of starting over.

## What I built
- **Mock network:** 38 synthetic contacts in `seed/network.json`, built on real companies so they overlap your 20 portfolio and 5 research companies.
- **On a filing (Push):** the one contact best placed to explain it, why them, and what to ask. Today's Hindalco filing about Novelis China points to the contact who did corporate development at Novelis.
- **On a management change:** routes to the new person, each with its evidence. For HDFC Bank's incoming MD it finds "Both at ICICI Bank 2017–2021" and marks two other links unconfirmed because the filing gives no dates.
- **Call sheet:** the week's filings turned into three or four calls worth making, including contacts going cold, with an opener to copy.
- **In Research (Pull):** a "Who to call" tab grouping contacts as inside, alumni, competitors, suppliers, customers and sector. It also works for tickers outside your demo set.
- **Network screen:** a map with you at the centre that lights up where this week's filings touch your contacts, plus expertise by theme and a person sheet with career, "I spoke to them today" and "Forget".
- **Ask:** one box answers both "Who do I know at Swiggy?" and business questions, with voice input where the browser supports it.

The network matching uses no model at all, only alias lookup and date arithmetic. That is the main privacy point in the write-up: no contact's details go to a model provider.

I checked Today, Network, the person sheet, Research and Ask at phone width with no console errors. I did not test the Docker build, the voice input, or the alert pointer (no alert was triggered today).

## AI build history
The brief wants to see how you worked with the tools, so I kept both sessions in `build-history/`:
- `01-push-and-pull-oct30.md` is the original session.
- `02-network-layer-nov15.md` is this one, generated by `scripts/export_history.py`.

The link in the email is `https://github.com/CinnamonRoll10/finn/tree/master/build-history`, which works once pushed. The export of this session was taken before this final message. It is missing my explanation of why I extended the old build because that reply was not saved in the session log. To capture the rest of the conversation, re-run it after we finish:

```bash
cd "/Users/prakritiprasad/Desktop/self proj/finn" && .venv/bin/python scripts/export_history.py ~/.claude/projects/-Users-prakritiprasad-Desktop-self-proj/50dc6dc7-cd30-46c0-9a5a-4d36418f4648.jsonl build-history/02-network-layer-nov15.md "FINN — AI build history, session 2: the Network layer (15 Nov 2026)"
```

## What you still need to do
1. **Push** (I can do this on your go-ahead), then open https://finn-10sm.onrender.com on your phone and confirm the Network tab appears.
2. **Send the email** to assessment@enam.com with subject `IIT Kanpur – Founding AI Engineer - 2027`. The body is in [EMAIL.txt](finn/EMAIL.txt); fill in your phone number at the bottom.
3. **Attach the raw session exports**, which the email says are attached. `finn-ai-build-history.zip` in the finn folder covers only session 1; this session's raw log is the `.jsonl` file in the command above.

Before you send, check two things in the email:
- **Cost figure:** it quotes about $2.15 for all model usage. That is an estimate from character counts, because the work ran through your Claude subscription rather than an API key.
- **Live demo and API key:** the email does not say whether the demo can answer new questions. If the Render service has no API key set, it serves the pre-built research and the whole Network layer, but cannot answer new business questions or summarise new filings.

The local server is still running at http://localhost:8000 if you want to try it now.

## User

Commit and push

