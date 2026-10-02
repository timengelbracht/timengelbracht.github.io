"""Google Scholar profile page (no official API, so this reads the public HTML).

Google sometimes blocks automated requests, especially from CI runners. That is
expected: the other sources still produce the full list.
"""
from __future__ import annotations

from urllib.parse import urljoin

from bs4 import BeautifulSoup

from sitegen.http import get
from sitegen.util import log


def papers(user_id: str) -> list[dict]:
    if not user_id:
        return []
    r = get("https://scholar.google.com/citations",
            params={"user": user_id, "hl": "en", "cstart": 0, "pagesize": 100, "sortby": "pubdate"})
    if r is None or "gsc_a_tr" not in r.text:
        log("Google Scholar unavailable (blocked or empty); using the other sources")
        return []
    soup = BeautifulSoup(r.text, "html.parser")
    out = []
    for row in soup.select("tr.gsc_a_tr"):
        a = row.select_one("a.gsc_a_at")
        if a is None:
            continue
        grey = row.select("div.gs_gray")
        year = row.select_one("span.gsc_a_h")
        out.append({
            "title": a.get_text(strip=True),
            "authors_short": grey[0].get_text(strip=True) if grey else "",
            "venue": grey[1].get_text(strip=True) if len(grey) > 1 else "",
            "year": int(year.get_text()) if year and year.get_text().isdigit() else None,
            "scholar_url": urljoin("https://scholar.google.com", a.get("href", "")),
        })
    log(f"Google Scholar: {len(out)} papers")
    return out
