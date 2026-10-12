"""Render site/ from config.yml, content/*.yml and data/publications.json."""

from __future__ import annotations

import html
import json
import logging
import re
import shutil
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

from sitegen import bibtex, venues
from sitegen.paths import Paths
from sitegen.util import collaborators_config, load_yaml, norm, person_key, slugify

logger = logging.getLogger(__name__)

TEMPLATES = Path(__file__).parent / "templates"

SCRIBBLES = [  # hand-drawn underline paths for [[keywords]] in the bio
    ("k1", "M1 6c18-4 30 3 48-1s34-3 50 1"),
    ("k2", "M1 5c14 3 30-4 46 0s36 3 52-2"),
    ("k3", "M1 4c20 4 36-3 52 1s30 2 46-1"),
]

CHIPS = (
    ("project", "project page"),
    ("arxiv", "arXiv"),
    ("paper", "paper"),
    ("code", "code"),
    ("video", "video"),
    ("data", "data"),
)


def bio_html(text: str) -> str:
    """[[keyword]] -> keyword with a hand-drawn underline; [text](url) -> link."""
    out, i, n = [], 0, 0
    for m in re.finditer(r"\[\[(.+?)\]\]|\[([^\]]+)\]\((https?://[^)\s]+)\)", text):
        out.append(html.escape(text[i : m.start()]))
        if m.group(1):
            cls, d = SCRIBBLES[n % len(SCRIBBLES)]
            n += 1
            out.append(
                f'<span class="kw {cls}">{html.escape(m.group(1))}<svg viewBox="0 0 100 10" '
                f'preserveAspectRatio="none"><path d="{d}"/></svg></span>'
            )
        else:
            url, label = html.escape(m.group(3)), html.escape(m.group(2))
            out.append(f'<a href="{url}" target="_blank" rel="noopener">{label}</a>')
        i = m.end()
    out.append(html.escape(text[i:]))
    return "".join(out)


def visible_links(links: list, root: Path) -> list:
    """Hide placeholder links (YOUR_...) and links to local files that don't exist yet."""
    out = []
    for link in links or []:
        url = link.get("url", "")
        if not url or "YOUR_" in url:
            continue
        if not re.match(r"^[a-z]+:", url) and not (root / url).exists():
            continue
        out.append(link)
    return out


def themes_with_papers(themes: list, papers: list) -> list:
    """Attach papers to themes: listed slugs first, then new papers that match the theme's pattern."""
    out = []
    for t in themes or []:
        t = dict(t)
        listed = list(t.get("papers") or [])
        pattern = t.get("match")
        for p in papers:
            text = p["title"] + " " + (p.get("abstract") or "")
            if (
                p["slug"] not in listed
                and pattern
                and re.search(pattern, text, re.I)
                and not any(p["slug"] in (o.get("papers") or []) for o in themes)
            ):
                listed.append(p["slug"])
        by_slug = {p["slug"]: p for p in papers}
        t["paper_refs"] = [
            {"slug": s, "short": by_slug[s].get("short") or split_title(by_slug[s]["title"])[0]}
            for s in listed
            if s in by_slug
        ]
        out.append(t)
    return out


def email_parts(email: str) -> dict:
    """Split an address so the page can show 'name [at] domain' and assemble the real one in the browser."""
    if not email or "@" not in email:
        return {}
    user, domain = email.split("@", 1)
    return {"user": user, "domain": domain}


def authors_html(p: dict, me: set) -> str:
    """Comma-separated authors with yours underlined. Empty if unknown: never a placeholder."""
    authors = p.get("authors") or [
        a.strip()
        for a in (p.get("authors_short") or "").split(",")
        if a.strip() and "..." not in a and "…" not in a
    ]
    if not authors:
        return ""
    if len(authors) > 9:  # long consortium lists stay readable
        mine = next((i for i, a in enumerate(authors) if norm(a) in me), 0)
        authors = [authors[i] for i in sorted(set(range(6)) | {mine})] + ["et al."]
    return ", ".join(f"<u>{html.escape(a)}</u>" if norm(a) in me else html.escape(a) for a in authors)


def venue_label(p: dict) -> str:
    v = venues.short(p.get("venue") or "", p.get("year"))
    if not v and p.get("arxiv"):
        v = f"arXiv {p.get('year') or ''}".strip()
    return v


def apply_overrides(p: dict, manual: dict) -> dict:
    """content/paper_links.yml also applies at build time, so edits there show up without a sync."""
    extra = manual.get(p.get("slug") or slugify(p["title"])) or manual.get(p.get("arxiv") or "-") or {}
    p = dict(p)
    for f in ("venue", "authors", "abstract", "title", "short"):
        if extra.get(f):
            p[f] = extra[f]
    links = dict(p.get("links") or {})
    links.update({k: v for k, v in extra.items() if k in ("project", "code", "video", "data", "paper")})
    p["links"] = links
    return p


def split_title(t: str) -> tuple[str, str]:
    """'Hoi! - A Multimodal Dataset' -> ('Hoi!', 'A Multimodal Dataset')."""
    m = re.match(r"^(.{2,40}?)\s*(?::|\s[-–—]\s)\s*(.+)$", t)
    return (m.group(1).strip(), m.group(2).strip()) if m else (t, "")


def prepare(p: dict, me: set) -> dict:
    p = dict(p)
    links = p.get("links") or {}
    p["link"] = (
        links.get("project")
        or links.get("arxiv")
        or links.get("paper")
        or p.get("s2_url")
        or p.get("scholar_url")
        or "#"
    )
    p["authors_html"] = authors_html(p, me)
    p["venue"] = venue_label(p)
    p["published"] = venues.is_published(p["venue"])
    p["bibtex"] = bibtex.entry(p, p["venue"])
    p.setdefault("slug", slugify(p["title"]))
    p["chips"] = [(label, links[k]) for k, label in CHIPS if links.get(k)]
    p.setdefault("teaser", {"kind": "doodle", "scene": "reading", "from": "doodle"})
    return p


def collaborators(cfg: dict, papers: list) -> tuple:
    """Key people up front; everyone else (all co-authors by default) behind '+N more'."""
    key, others, hide = collaborators_config(cfg)
    skip = {person_key(n) for n in cfg.get("my_author_names", [])} | {person_key(n) for n in hide}
    shown = [dict(c) for c in key if person_key(c["name"]) not in skip]
    taken = skip | {person_key(c["name"]) for c in shown}
    if others == "all":
        counts: dict = {}
        names: dict = {}
        for p in papers:
            for a in p.get("authors") or []:
                k = person_key(a)
                if not k or k in taken:
                    continue
                counts[k] = counts.get(k, 0) + 1
                if len(a) > len(names.get(k, "")):  # prefer 'Alessandro Mercurio' over 'A. Mercurio'
                    names[k] = a
        more = [{"name": names[k]} for k in sorted(counts, key=lambda k: (-counts[k], names[k].split()[-1]))]
    else:
        more = [dict(c) for c in others or [] if person_key(c["name"]) not in taken]
    return shown, more


def run(paths: Paths) -> Path:
    cfg = load_yaml(paths.config, {})
    pubs: dict[str, Any] = {"papers": [], "synced": "never"}
    if paths.data.exists():
        pubs = json.loads(paths.data.read_text(encoding="utf-8"))
    me = {norm(n) for n in cfg.get("my_author_names", [])}
    if cfg.get("headshot") and not (paths.root / cfg["headshot"]).exists():
        cfg["headshot"] = None  # placeholder until the photo exists

    manual = load_yaml(paths.content / "paper_links.yml", {})
    papers = [prepare(apply_overrides(p, manual), me) for p in pubs.get("papers", [])]
    newest = None
    if papers:
        short, rest = split_title(papers[0]["title"])
        if len(rest) > 70:
            rest = rest[:68].rsplit(" ", 1)[0] + "…"
        newest = {"short": short, "rest": rest, "link": papers[0]["link"]}

    crew, crew_more = collaborators(cfg, papers)

    today = load_yaml(paths.content / "robot_today.yml", [])
    themes_file = load_yaml(paths.content / "themes.yml", [])
    if isinstance(themes_file, dict):  # tolerate a mapping with themes + open_call
        themes, open_call = themes_file.get("themes", []), themes_file.get("open_call")
    else:
        themes, open_call = themes_file, None
    cfg["links"] = visible_links(cfg.get("links"), paths.root)
    site_url = (cfg.get("url") or "").rstrip("/")
    env = Environment(loader=FileSystemLoader(str(TEMPLATES)), autoescape=select_autoescape(["html", "j2"]))
    page = env.get_template("index.html.j2").render(
        cfg=cfg,
        bio_html=bio_html(cfg.get("bio", "")),
        papers=papers,
        newest=newest,
        crew=crew,
        crew_more=crew_more,
        today=today,
        today_js=json.dumps(today, ensure_ascii=False),
        themes=themes_with_papers(themes, papers),
        open_call=open_call,
        email=email_parts(cfg.get("email", "")),
        site_url=site_url,
        social_image=f"{site_url}/{cfg['social_image']}" if site_url and cfg.get("social_image") else "",
        news=load_yaml(paths.content / "news.yml", []),
        failures=load_yaml(paths.content / "failures.yml", []),
        synced=pubs.get("synced", "never"),
    )

    paths.site.mkdir(exist_ok=True)
    (paths.site / "index.html").write_text(page, encoding="utf-8")
    if paths.assets.exists():
        shutil.copytree(paths.assets, paths.site / "assets", dirs_exist_ok=True)
    (paths.site / ".nojekyll").write_text("")  # GitHub Pages: serve files as they are
    logger.info(
        f"built {paths.rel(paths.site / 'index.html')}: {len(papers)} papers, "
        f"{len(crew)}+{len(crew_more)} collaborators"
    )
    return paths.site / "index.html"
