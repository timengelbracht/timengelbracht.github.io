"""Semantic Scholar Graph API (free, no key needed for low volumes)."""

from __future__ import annotations

import logging
import time

from sitegen.http import as_json, get

logger = logging.getLogger(__name__)


API = "https://api.semanticscholar.org/graph/v1"
FIELDS = "title,year,publicationDate,venue,authors,externalIds,abstract,url,openAccessPdf"


def to_paper(p: dict) -> dict:
    ext = p.get("externalIds") or {}
    pdf = (p.get("openAccessPdf") or {}).get("url")
    return {
        "title": p.get("title") or "",
        "year": p.get("year"),
        "date": p.get("publicationDate"),
        "venue": p.get("venue") or "",
        "authors": [a["name"] for a in p.get("authors") or [] if a.get("name")],
        "abstract": p.get("abstract") or "",
        "arxiv": ext.get("ArXiv"),
        "doi": ext.get("DOI"),
        "s2_url": p.get("url"),
        "pdf_url": pdf,
    }


def author_papers(author_ids: list[str]) -> list[dict]:
    out = []
    for aid in author_ids:
        r = get(f"{API}/author/{aid}/papers", params={"fields": FIELDS, "limit": 200})
        out += [to_paper(p) for p in as_json(r).get("data", [])]
        time.sleep(1)
    logger.info(f"Semantic Scholar: {len(out)} papers")
    return out


def match(title: str) -> dict:
    r = get(f"{API}/paper/search/match", params={"query": title, "fields": FIELDS})
    data = as_json(r).get("data") or []
    return to_paper(data[0]) if data else {}
