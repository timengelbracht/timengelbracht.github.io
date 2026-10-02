"""Finding and checking a paper's links (project page, code, video, data, paper)."""
from __future__ import annotations

import re
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from sitegen.http import as_json, get
from sitegen.sources import arxiv
from sitegen.util import ascii_lower, short_name

URL_RE = re.compile(r"https?://[^\s,;)\]>\"']+")

SKIP = ("arxiv.org", "doi.org", "creativecommons", "w3.org", "orcid.org", "openreview", "ieee.org", "acm.org",
        "springer", "twitter.com", "x.com", "linkedin", "mailto:", "semanticscholar", "scholar.google")
VIDEO_HOSTS = ("youtube", "youtu.be", "vimeo", "photos.app.goo.gl", "photos.google")
DATA_HOSTS = ("huggingface", "zenodo")


def classify(urls: list[str], links: dict) -> dict:
    """Sort raw URLs into link kinds. Existing entries win."""
    for u in urls:
        u = u.rstrip(".,;)")
        host = urlparse(u).netloc.lower()
        if not host or any(s in u.lower() for s in SKIP):
            continue
        if "github.com" in host:
            links.setdefault("code", u)
        elif any(h in host for h in VIDEO_HOSTS):
            links.setdefault("video", u)
        elif any(h in host for h in DATA_HOSTS):
            links.setdefault("data", u)
        else:
            links.setdefault("project", u)
    return links


def from_text(p: dict) -> list[str]:
    return URL_RE.findall(" ".join([p.get("abstract", ""), p.get("comment", "")]))


def from_arxiv_html(p: dict) -> list[str]:
    """Project pages usually sit on the first page: under the authors, in the abstract or a footnote."""
    got = arxiv.html_page(p)
    if not got:
        return []
    soup, _ = got
    urls = [a["href"] for a in soup.select(
        ".ltx_authors a[href], .ltx_abstract a[href], .ltx_note a[href], .ltx_title a[href]")]
    for a in soup.select("a[href]"):
        ctx = (a.get_text(" ") + " " + (a.parent.get_text(" ") if a.parent else ""))[:200].lower()
        if re.search(r"project (page|website)|website|webpage|code (is )?available", ctx):
            urls.append(a["href"])
    return [u for u in urls if u.startswith("http")]


def github_homepage(code_url: str) -> str | None:
    m = re.match(r"https://github\.com/([^/]+)/([^/#?]+)", code_url or "")
    if not m:
        return None
    hp = as_json(get(f"https://api.github.com/repos/{m.group(1)}/{m.group(2)}", tries=1)).get("homepage") or ""
    return hp if hp.startswith("http") and "github.com" not in hp else None


def guesses(p: dict, patterns: list[str]) -> list[str]:
    s = short_name(p["title"])
    variants = dict.fromkeys([s, s.lower(), s.replace(" ", "-"), s.lower().replace(" ", "-"),
                              f"{s}-Website", f"{s.lower()}-website"])
    return [pat.format(short=v) for pat in patterns for v in variants]


def page_mentions_paper(html: str, p: dict) -> bool:
    """At least two of: short name, three title words, two author surnames."""
    page = ascii_lower(BeautifulSoup(html, "html.parser").get_text(" "))
    short = ascii_lower(short_name(p["title"]))
    words = [w for w in re.findall(r"[a-z0-9]+", ascii_lower(p["title"])) if len(w) > 3][:5]
    surnames = [ascii_lower(a.split()[-1]) for a in (p.get("authors") or [])[:4] if a.split()]
    hits = (short in page) + (sum(w in page for w in words) >= 3) + (sum(n in page for n in surnames) >= 2)
    return hits >= 2


def verify(url: str, p: dict) -> bool:
    """True only if the URL loads (200), is a real page and is about this paper."""
    r = get(url, tries=2, timeout=15)
    if r is None or r.status_code != 200 or len(r.text) < 500:
        return False
    return page_mentions_paper(r.text, p)


def is_arxiv_doi(url: str) -> bool:
    return "10.48550/arxiv" in (url or "").lower() or "arxiv.org" in (url or "").lower()
