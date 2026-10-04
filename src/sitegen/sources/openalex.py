"""OpenAlex works API (free, no key)."""

from __future__ import annotations

from sitegen.http import as_json, get
from sitegen.util import norm


def match(title: str) -> dict:
    r = get(
        "https://api.openalex.org/works",
        params={"search": title, "per-page": 3, "mailto": "actions@github.com"},
    )
    for w in as_json(r).get("results", []):
        if norm(w.get("title") or "") != norm(title):
            continue
        inv = w.get("abstract_inverted_index") or {}
        words = sorted((i, word) for word, idx in inv.items() for i in idx)
        loc = w.get("primary_location") or {}
        best = w.get("best_oa_location") or {}
        return {
            "authors": [a["author"]["display_name"] for a in w.get("authorships", []) if a.get("author")],
            "abstract": " ".join(word for _, word in words),
            "date": w.get("publication_date"),
            "doi": (w.get("doi") or "").replace("https://doi.org/", "") or None,
            "paper_url": loc.get("landing_page_url"),
            "pdf_url": best.get("pdf_url") or loc.get("pdf_url"),
        }
    return {}
