"""Primary documents: download PDFs (cached as bytes) and extract text.

Transcripts are 15-40 pages: we take the whole thing. Annual reports are
300-600 pages: we take the opening pages (business overview) and the
Management Discussion & Analysis section, which is where strategy, segment
commentary and guidance live - enough for extraction without feeding 500
pages to a model.
"""
from __future__ import annotations

import io
import os
import re

import requests
from pypdf import PdfReader

from .. import store
from ..config import USER_AGENT

HEADERS = {"User-Agent": USER_AGENT, "Referer": "https://www.bseindia.com/"}


def download(url: str) -> bytes:
    hit = store.get_bytes("pdf", url)
    if hit is not None:
        return hit
    last = None
    for attempt in range(3):  # exchange servers sometimes cut large files short
        r = requests.get(url, headers=HEADERS, timeout=180)
        r.raise_for_status()
        if not r.content.startswith(b"%PDF"):
            raise ValueError(f"not a PDF: {url}")
        declared = r.headers.get("Content-Length")
        if declared and int(declared) != len(r.content):
            last = f"truncated download {len(r.content)}/{declared}"
            continue
        return store.put_bytes("pdf", url, r.content)
    raise IOError(last or "download failed")


def pages(url: str, max_pages: int | None = None) -> list[str]:
    key = f"{url}|{max_pages}"
    hit = store.get("pdf_text", key)
    if hit is not None:
        return hit
    data = download(url)
    try:
        reader = PdfReader(io.BytesIO(data))
        n = len(reader.pages) if max_pages is None else min(max_pages, len(reader.pages))
        out = []
        for i in range(n):
            try:
                out.append(_clean(reader.pages[i].extract_text() or ""))
            except Exception:
                out.append("")
    except Exception:
        out = _poppler_pages(data, max_pages)  # pypdf chokes on some exchange PDFs
    store.put("pdf_text", key, out)
    return out


def _poppler_pages(data: bytes, max_pages: int | None) -> list[str]:
    """Fallback text extraction with poppler's pdftotext, if installed."""
    import shutil
    import subprocess
    import tempfile

    if not shutil.which("pdftotext"):
        return []
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        f.write(data)
        path = f.name
    try:
        cmd = ["pdftotext", "-layout"] + (["-l", str(max_pages)] if max_pages else []) + [path, "-"]
        txt = subprocess.run(cmd, capture_output=True, text=True, timeout=120).stdout
    finally:
        os.unlink(path)
    return [_clean(p) for p in txt.split("\f") if p.strip()]


def _clean(t: str) -> str:
    t = re.sub(r"[ \t]+", " ", t)
    t = re.sub(r"\n{3,}", "\n\n", t)
    return t.strip()


def transcript_text(url: str, max_chars: int = 120_000) -> str:
    return "\n\n".join(pages(url))[:max_chars]


def filing_text(url: str, max_pages: int = 8, max_chars: int = 16_000) -> str:
    return "\n\n".join(pages(url, max_pages))[:max_chars]


MDA_PAT = re.compile(r"management\s+discussion\s+(and|&)\s+analysis", re.I)


def annual_report_excerpt(url: str, max_chars: int = 60_000) -> dict:
    """Opening pages + the MD&A section of an annual report."""
    key = f"ar|{url}|{max_chars}"
    hit = store.get("pdf_text", key)
    if hit is not None:
        return hit
    reader = PdfReader(io.BytesIO(download(url)))
    n = len(reader.pages)

    def page(i):
        try:
            return _clean(reader.pages[i].extract_text() or "")
        except Exception:
            return ""

    opening = [page(i) for i in range(min(12, n))]
    # find MD&A: the page where the heading appears with substantial text after it
    # (skip table-of-contents hits in the first few pages)
    mda_start = None
    for i in range(3, n):
        t = page(i)
        head = t[:250]
        if MDA_PAT.search(head) and len(t) > 800 and not re.search(r"auditor|annexure|director.?s.? report", head, re.I):
            mda_start = i
            break
    mda = []
    if mda_start is not None:
        for i in range(mda_start, min(mda_start + 25, n)):
            mda.append(page(i))
    result = {
        "pages": n,
        "opening": "\n\n".join(opening)[: max_chars // 3],
        "mda": "\n\n".join(mda)[: max_chars - max_chars // 3],
        "mda_page": (mda_start + 1) if mda_start is not None else None,
    }
    store.put("pdf_text", key, result)
    return result
