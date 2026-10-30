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
    """Opening pages + the MD&A section of an annual report.

    Design-heavy reports have dozens of image-only pages up front, so the
    "opening" is the first text-bearing pages. If no MD&A heading is found,
    the Board's/Directors' Report (which carries the business review) is used.
    """
    key = f"ar2|{url}|{max_chars}"
    hit = store.get("pdf_text", key)
    if hit is not None:
        return hit
    data = download(url)
    try:
        reader = PdfReader(io.BytesIO(data))
        n = len(reader.pages)

        def page(i):
            try:
                return _clean(reader.pages[i].extract_text() or "")
            except Exception:
                return ""
        texts = [page(i) for i in range(n)]
    except Exception:
        texts = _poppler_pages(data, None)
        n = len(texts)

    text_idx = [i for i, t in enumerate(texts) if len(t) > 400]
    opening = [texts[i] for i in text_idx[:12]]

    def find_start(pattern, skip_tocs=3):
        for i in text_idx:
            if i < skip_tocs:
                continue
            head = texts[i][:250]
            if re.search(pattern, head, re.I) and len(texts[i]) > 800 and not re.search(r"auditor|annexure|contents", head, re.I):
                return i
        return None

    mda_start = find_start(r"management\s+discussion\s+(and|&)\s+analysis")
    section = "mda"
    if mda_start is None:
        mda_start = find_start(r"(board|directors?)['’]?s?\s+report")
        section = "boards_report" if mda_start is not None else None
    mda = []
    if mda_start is not None:
        mda = [texts[i] for i in range(mda_start, min(mda_start + 25, n))]
    elif text_idx:  # last resort: the first substantial text block
        mda = [texts[i] for i in text_idx[12:37]]
        section = "first_text"
    result = {
        "pages": n,
        "opening": "\n\n".join(opening)[: max_chars // 3],
        "mda": "\n\n".join(mda)[: max_chars - max_chars // 3],
        "mda_page": (mda_start + 1) if mda_start is not None else None,
        "section": section,
    }
    store.put("pdf_text", key, result)
    return result
