"""arXiv: export API for metadata, the HTML version for links and Figure 1.

arXiv asks for at most one request every 3 seconds; callers sleep accordingly.
"""

from __future__ import annotations

import logging
import re
import time
import xml.etree.ElementTree as ET

from bs4 import BeautifulSoup

from sitegen.http import get
from sitegen.util import norm

logger = logging.getLogger(__name__)

API = "https://export.arxiv.org/api/query"
ATOM = {"a": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}


def _entries(content: bytes) -> list[ET.Element] | None:
    try:
        return ET.fromstring(content).findall("a:entry", ATOM)
    except ET.ParseError:
        return None


def meta(arxiv_id: str) -> dict:
    r = get(API, params={"id_list": arxiv_id})
    entries = _entries(r.content) if r is not None else None
    if entries is None:
        if r is not None:
            logger.warning(f"arXiv answered with something that is not XML for {arxiv_id}; skipping")
        return {}
    if not entries or entries[0].find("a:title", ATOM) is None:
        return {}
    e = entries[0]

    def txt(tag: str) -> str:
        return re.sub(r"\s+", " ", e.findtext(tag, "", ATOM) or "").strip()

    return {
        "title": txt("a:title"),
        "abstract": txt("a:summary"),
        "authors": [
            re.sub(r"\s+", " ", a.findtext("a:name", "", ATOM)).strip() for a in e.findall("a:author", ATOM)
        ],
        "date": txt("a:published")[:10],
        "comment": txt("arxiv:comment"),
        "arxiv": arxiv_id,
    }


def search_title(title: str) -> str | None:
    q = 'ti:"' + re.sub(r"[^\w\s-]", " ", title)[:200] + '"'
    r = get(API, params={"search_query": q, "max_results": 5})
    entries = _entries(r.content) if r is not None else None
    for e in entries or []:
        if norm(e.findtext("a:title", "", ATOM)) == norm(title):
            return re.sub(r"v\d+$", "", e.findtext("a:id", "", ATOM).rsplit("/", 1)[-1])
    return None


def html_page(p: dict) -> tuple[BeautifulSoup, str] | None:
    """(soup, url) of the paper's HTML version, cached on the paper dict as _html."""
    if not p.get("arxiv"):
        return None
    if "_html" not in p:
        r = get(f"https://arxiv.org/html/{p['arxiv']}")
        p["_html"] = (BeautifulSoup(r.text, "html.parser"), r.url) if r is not None else None
        time.sleep(3)
    return p["_html"]
