"""Snapshot the warmed caches into seed/cache so a fresh deploy starts populated.

Run after `scripts/warm.py`. Ships only the small, provider-independent
namespaces; raw PDFs (hundreds of MB) and time-boxed caches (announcement
windows, prices, assembled digests) are left out and refetched on demand.

    .venv/bin/python scripts/make_seed.py
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from backend.config import CACHE_DIR, ROOT  # noqa: E402

NAMESPACES = ["research", "extract", "item_summary", "item_enrich", "llm", "screener", "pdf_text"]
SEED = ROOT / "seed" / "cache"


def main() -> None:
    if SEED.exists():
        shutil.rmtree(SEED)
    total = 0
    for ns in NAMESPACES:
        src = CACHE_DIR / ns
        if not src.is_dir():
            continue
        files = [f for f in src.iterdir() if f.suffix == ".json"]
        dst = SEED / ns
        dst.mkdir(parents=True)
        for f in files:
            shutil.copyfile(f, dst / f.name)
        size = sum(f.stat().st_size for f in files) / 1e6
        print(f"{ns:14s} {len(files):4d} files {size:6.1f} MB")
        total += size
    print(f"seed/cache: {total:.1f} MB")


if __name__ == "__main__":
    main()
