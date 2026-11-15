"""Turn a Claude Code session log (JSONL) into a readable build-history transcript.

    python scripts/export_history.py <session.jsonl> build-history/<name>.md "Title"

Keeps what a reviewer needs to see how the tool was used: every prompt the
user typed, the assistant's narration, and one line per tool call (what it
did, which file). Tool output, screenshots, injected reference material and
the model's private reasoning are left out for length; the raw JSONL is the
complete record.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path


def clean_user(text: str) -> str:
    text = re.sub(r"<system-reminder>.*?</system-reminder>", "", text, flags=re.S)
    text = re.sub(r"<local-command-caveat>.*?</local-command-caveat>", "", text, flags=re.S)
    text = re.sub(r"<command-(name|message|args)>.*?</command-\1>", "", text, flags=re.S)
    text = re.sub(r"<local-command-stdout>.*?</local-command-stdout>", "", text, flags=re.S)
    return text.strip()


def tool_line(b: dict) -> str:
    name = b.get("name", "tool").split("__")[-1]
    inp = b.get("input") or {}
    what = inp.get("description") or inp.get("file_path") or inp.get("url") or inp.get("query") or ""
    if not what and isinstance(inp.get("actions"), list):
        what = ", ".join(a.get("name", "") for a in inp["actions"][:6])
    what = str(what).replace(str(Path.home()), "~")
    return f"- `{name}`" + (f" — {what[:160]}" if what else "")


def main(src: str, dst: str, title: str) -> None:
    out = [f"# {title}", "",
           "Readable export of a Claude Code session. User prompts, the assistant's narration, and one line per tool call "
           "(file writes, shell commands, browser checks). Tool outputs, screenshots, injected reference material and the "
           "model's private reasoning are omitted for length; the raw session export is the complete record.", ""]
    last_role = None
    for line in Path(src).read_text().splitlines():
        try:
            o = json.loads(line)
        except Exception:
            continue
        if o.get("type") not in ("user", "assistant") or o.get("isSidechain") or o.get("isMeta"):
            continue
        content = (o.get("message") or {}).get("content")
        if o["type"] == "user":
            if isinstance(content, list):
                content = "\n".join(b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text")
            text = clean_user(content or "")
            if text and not text.startswith("[Request interrupted"):
                out += ["", "## User", "", text, ""]
                last_role = "user"
            continue
        for b in content if isinstance(content, list) else []:
            if b.get("type") == "text" and b.get("text", "").strip():
                out += ["", f"**Claude:** {b['text'].strip()}", ""]
                last_role = "text"
            elif b.get("type") == "tool_use":
                if b.get("name", "").endswith(("update_plan", "wrap_up", "ToolSearch", "mark_chapter")):
                    continue
                out.append(tool_line(b))
                last_role = "tool"
    Path(dst).parent.mkdir(parents=True, exist_ok=True)
    Path(dst).write_text(re.sub(r"\n{3,}", "\n\n", "\n".join(out)) + "\n")
    print(f"{dst}: {len(out)} lines")


if __name__ == "__main__":
    if len(sys.argv) < 4:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2], sys.argv[3])
