"""Pull the paper list and write data/publications.json plus teaser media.

Per paper:
  1. list     Google Scholar + Semantic Scholar profile(s) + extra arXiv ids
  2. enrich   authors, abstract, date, venue (arXiv -> Semantic Scholar -> OpenAlex -> DBLP)
  3. links    project page, code, video, data; every project/data link is verified
  4. teaser   see sitegen.teasers
Nothing needs manual input when a new paper appears, and every step fails soft:
a source that is down never removes a paper or makes an entry worse than last time.
"""
from __future__ import annotations

import json
import re
import time

from sitegen import links as L
from sitegen import venues
from sitegen.paths import Paths
from sitegen.sources import arxiv, dblp, openalex, scholar, semantic_scholar
from sitegen.teasers import Teasers, doodle
from sitegen.util import collaborators_config, is_abbreviated, load_yaml, log, norm, person_key, slugify

KEEP_FROM_LAST_SYNC = ("authors", "abstract", "date", "venue", "arxiv", "arxiv_url", "doi", "pdf_url")
MANUAL_LINK_KINDS = ("project", "code", "video", "data", "paper")


def merge(lists: list[list[dict]]) -> list[dict]:
    """Merge papers from several sources by normalized title; the first non-empty value wins."""
    by_title: dict[str, dict] = {}
    for lst in lists:
        for p in lst:
            key = norm(p.get("title", ""))
            if not key:
                continue
            cur = by_title.setdefault(key, {})
            for field, value in p.items():
                if value and not cur.get(field):
                    cur[field] = value
    return list(by_title.values())


def fill(p: dict, found: dict, overwrite=()) -> None:
    for field, value in (found or {}).items():
        if value and (field in overwrite or not p.get(field)):
            p[field] = value


def better_authors(current: list[str], candidate: list[str]) -> bool:
    """Prefer a list with fewer abbreviated names ('Z. Bauer') of about the same length."""
    if not candidate:
        return False
    if not current:
        return True
    abbr = lambda names: sum(is_abbreviated(n) for n in names)  # noqa: E731
    return abs(len(candidate) - len(current)) <= 1 and abbr(candidate) < abbr(current)


def enrich_metadata(p: dict) -> None:
    title = p["title"]
    if not p.get("arxiv"):
        fill(p, semantic_scholar.match(title))
        time.sleep(1)
    if not p.get("arxiv"):
        p["arxiv"] = arxiv.search_title(title)
        time.sleep(3)
    if p.get("arxiv"):
        fill(p, arxiv.meta(p["arxiv"]), overwrite=("abstract", "authors", "comment"))
        accepted = venues.from_text(p.get("comment", ""))  # e.g. "Accepted to CVPR 2026"
        if accepted and (not p.get("venue") or "arxiv" in p["venue"].lower()):
            p["venue"] = accepted
        p["arxiv_url"] = f"https://arxiv.org/abs/{p['arxiv']}"
        time.sleep(3)  # arXiv asks for one request every 3 s
    needs_names = any(is_abbreviated(a) for a in p.get("authors") or [])
    if not p.get("authors") or not p.get("abstract") or needs_names:
        found = openalex.match(title)
        if better_authors(p.get("authors") or [], found.get("authors") or []):
            p["authors"] = found["authors"]
        fill(p, found)
        time.sleep(1)
    needs_names = any(is_abbreviated(a) for a in p.get("authors") or [])
    if not p.get("authors") or needs_names or (not p.get("arxiv") and not p.get("paper_url")):
        found = dblp.match(title)
        if better_authors(p.get("authors") or [], found.get("authors") or []):
            p["authors"] = found["authors"]
        fill(p, found)
        time.sleep(1)
    if not p.get("paper_url") and p.get("doi"):
        p["paper_url"] = f"https://doi.org/{p['doi']}"


def find_links(p: dict, cfg: dict) -> None:
    links = dict(p.get("links") or {})  # manual links from content/paper_links.yml come first
    manual = set(links)
    L.classify(L.from_text(p) + L.from_arxiv_html(p), links)
    if "project" not in links and links.get("code"):
        hp = L.github_homepage(links["code"])
        if hp:
            links["project"] = hp
    if "project" not in links:
        for guess in L.guesses(p, cfg.get("project_page_guesses", [])):
            if L.verify(guess, p):
                links["project"] = guess
                break
    for kind in [k for k in ("project", "data") if k in links and k not in manual]:
        if not L.verify(links[kind], p):
            log(f"  ! dropped {kind} link that did not check out: {links[kind]}")
            links.pop(kind)
    if p.get("arxiv_url"):
        links["arxiv"] = p["arxiv_url"]
    if p.get("paper_url") and not L.is_arxiv_doi(p["paper_url"]):
        links.setdefault("paper", p["paper_url"])
    if L.is_arxiv_doi(links.get("paper", "")):
        links.pop("paper")
    p["links"] = links


def tidy(p: dict) -> None:
    abstract = p.get("abstract") or ""
    abstract = re.sub(r"\s*(The\s+)?[Pp]roject\s+[Ww]ebsite[^.]*?https?://\S+\s*$", "", abstract)
    abstract = re.sub(r"\s*We provide code and data at:?\s*https?://\S+\s*$", "", abstract)
    p["abstract"] = abstract.strip()
    if not p.get("year") and p.get("date"):
        p["year"] = int(str(p["date"])[:4])
    p["slug"] = slugify(p["title"])
    for k in ("comment", "_html"):
        p.pop(k, None)


def run(paths: Paths) -> list[dict]:
    cfg = load_yaml(paths.config, {})
    src = cfg.get("sources", {})
    manual = load_yaml(paths.content / "paper_links.yml", {})
    old_papers = json.loads(paths.data.read_text(encoding="utf-8")).get("papers", []) if paths.data.exists() else []
    old = {norm(p["title"]): p for p in old_papers}
    teasers = Teasers(paths)

    extra = []
    for aid in src.get("extra_arxiv_ids", []):
        m = arxiv.meta(aid)
        if m:
            extra.append(m)
        time.sleep(3)
    papers = merge([scholar.papers(src.get("google_scholar_id", "")),
                    semantic_scholar.author_papers(src.get("semantic_scholar_ids", [])),
                    extra])
    excluded = {norm(x) for x in src.get("exclude", [])} | set(src.get("exclude", []))
    papers = [p for p in papers if norm(p["title"]) not in excluded and p.get("arxiv") not in excluded]
    log(f"{len(papers)} unique papers")

    out = []
    for p in papers:
        log("•", p["title"][:80])
        extra_info = manual.get(slugify(p["title"])) or manual.get(p.get("arxiv") or "-") or {}
        if extra_info.get("hide"):
            continue
        p["links"] = {k: v for k, v in extra_info.items() if k in MANUAL_LINK_KINDS}
        lookup_ok = True
        try:
            enrich_metadata(p)
            find_links(p, cfg)
        except Exception as e:  # keep going with what we have
            lookup_ok = False
            log(f"  ! lookup failed ({type(e).__name__}: {e}); keeping the basic entry")
        for f in ("authors", "abstract", "venue"):
            if extra_info.get(f):
                p[f] = extra_info[f]
        tidy(p)
        prev = old.get(norm(p["title"]), {})
        for f in KEEP_FROM_LAST_SYNC:  # a flaky source must never make the site worse
            if not p.get(f) and prev.get(f):
                p[f] = prev[f]
        for kind, url in (prev.get("links") or {}).items():  # links found last time but missed now
            if kind in p["links"] or (kind == "paper" and L.is_arxiv_doi(url)):
                continue
            if kind in ("project", "data") and lookup_ok and not L.verify(url, p):
                continue  # re-checked and it no longer works
            p["links"][kind] = url
        try:
            p["teaser"] = teasers.find(p, prev.get("teaser"))
        except Exception as e:
            log(f"  ! teaser failed ({type(e).__name__}: {e}); using a doodle")
            p["teaser"] = doodle(p)
        log(f"  teaser: {p['teaser']['from']}")
        out.append(p)

    # Papers never disappear because a source was down; remove one only via `exclude`.
    have = {norm(p["title"]) for p in out}
    for key, prev in old.items():
        if key not in have and key not in excluded and prev.get("arxiv") not in excluded:
            log(f"  kept from last sync (not found this time): {prev['title'][:70]}")
            out.append(prev)
    out.sort(key=lambda p: str(p.get("date") or f"{p.get('year') or 0}-00-00"), reverse=True)

    key, others, hide = collaborators_config(cfg)
    listed = {person_key(c["name"]) for c in key} | {person_key(n) for n in cfg.get("my_author_names", []) + hide}
    if others == "all":  # everyone else is shown under "+N more" anyway
        listed |= {person_key(a) for p in out for a in p.get("authors") or []}
    else:
        listed |= {person_key(c["name"]) for c in others or []}
    unlisted: dict[str, int] = {}
    for p in out:
        for a in p.get("authors") or []:
            if person_key(a) not in listed:
                unlisted[a] = unlisted.get(a, 0) + 1
    if unlisted:
        log("co-authors not in config.yml collaborators:",
            ", ".join(f"{a} ({n})" for a, n in sorted(unlisted.items(), key=lambda x: -x[1])))

    paths.data.parent.mkdir(parents=True, exist_ok=True)
    paths.data.write_text(json.dumps({"synced": time.strftime("%Y-%m-%d"), "papers": out,
                                      "unlisted_coauthors": unlisted}, ensure_ascii=False, indent=2) + "\n",
                          encoding="utf-8")
    log(f"wrote {paths.rel(paths.data)} with {len(out)} papers")
    return out
