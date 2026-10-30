"""Pre-build everything the demo touches: digests for the standard windows and
research for the portfolio + research set. Safe to re-run; everything is cached.

    .venv/bin/python scripts/warm.py            # digests + all research
    .venv/bin/python scripts/warm.py DIXON VBL  # just these companies
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend import store  # noqa: E402
from backend.config import PORTFOLIO, RESEARCH_SET  # noqa: E402
from backend.engine import digest, research  # noqa: E402

args = sys.argv[1:]
if not args:
    s = store.load_settings()
    for h in (24, 72, 168):
        t = time.time()
        d = digest.build_digest(s, hours=h, deep=False)
        print(f"digest {h}h: {d['counts']} pending={d['pending']} ({time.time() - t:.0f}s)")
    # run the enrichment synchronously here (the server does it in a thread)
    for h in (24, 72, 168):
        d = digest.build_digest(s, hours=h, deep=True)
        while not d["complete"]:
            time.sleep(5)
            d = digest.build_digest(s, hours=h, deep=False)
        print(f"digest {h}h complete")
symbols = [a.upper() for a in args] or list(PORTFOLIO) + list(RESEARCH_SET)
for sym in symbols:
    t = time.time()
    try:
        r = research.build(sym)
        print(f"{sym}: ok, {len(r['transcripts'])} transcripts, ledger {len(r['sections'].get('ledger', []))} rows ({time.time() - t:.0f}s)")
    except Exception as e:
        print(f"{sym}: FAILED {e}")
