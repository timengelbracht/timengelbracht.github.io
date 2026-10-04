"""DBLP search API: reliable full author names and venue links."""

from __future__ import annotations

import re

from sitegen.http import as_json, get
from sitegen.util import norm


def match(title: str) -> dict:
    r = get("https://dblp.org/search/publ/api", params={"q": title, "format": "json", "h": 5})
    hits = (((as_json(r).get("result") or {}).get("hits") or {}).get("hit")) or []
    for h in hits:
        info = h.get("info", {})
        if norm(info.get("title", "")) != norm(title):
            continue
        authors = (info.get("authors") or {}).get("author") or []
        authors = authors if isinstance(authors, list) else [authors]
        ee = info.get("ee") or []
        ee = ee if isinstance(ee, list) else [ee]
        out = {
            # DBLP disambiguates namesakes as "Name 0001"; drop that suffix
            "authors": [re.sub(r"\s\d{4}$", "", a["text"]) for a in authors if a.get("text")],
            "venue": info.get("venue") or "",
        }
        for u in ee:
            m = re.search(r"arxiv\.org/abs/([\d.]+)", u)
            if m:
                out["arxiv"] = m.group(1)
            elif not out.get("paper_url"):
                out["paper_url"] = u
        return out
    return {}
