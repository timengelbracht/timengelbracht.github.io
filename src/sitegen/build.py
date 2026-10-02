"""Render site/ from config.yml, content/*.yml and data/publications.json."""
from __future__ import annotations

import html
import json
import re
import shutil
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from sitegen.paths import Paths
from sitegen.util import load_yaml, log, norm

TEMPLATES = Path(__file__).parent / "templates"

SCRIBBLES = [  # hand-drawn underline paths for [[keywords]] in the bio
    ("k1", "M1 6c18-4 30 3 48-1s34-3 50 1"),
    ("k2", "M1 5c14 3 30-4 46 0s36 3 52-2"),
    ("k3", "M1 4c20 4 36-3 52 1s30 2 46-1"),
]

VENUES = [  # (pattern, short name), checked in order
    (r"arxiv", "arXiv"),
    (r"computer vision and pattern recognition|\bcvpr\b", "CVPR"),
    (r"international conference on computer vision|\biccv\b", "ICCV"),
    (r"european conference on computer vision|\beccv\b", "ECCV"),
    (r"robotics and automation letters|\bra-?l\b", "RA-L"),
    (r"international conference on robotics and automation|\bicra\b", "ICRA"),
    (r"intelligent robots and systems|\biros\b", "IROS"),
    (r"robotics: science and systems|\brss\b", "RSS"),
    (r"conference on robot learning|\bcorl\b", "CoRL"),
    (r"neural information processing|\bneurips\b", "NeurIPS"),
    (r"learning representations|\biclr\b", "ICLR"),
    (r"3d vision|\b3dv\b", "3DV"),
    (r"winter conference on applications of computer vision|\bwacv\b", "WACV"),
]

CHIPS = (("project", "project page"), ("arxiv", "arXiv"), ("paper", "paper"),
         ("code", "code"), ("video", "video"), ("data", "data"))


def bio_html(text: str) -> str:
    """[[keyword]] -> keyword with a hand-drawn underline."""
    out, i = [], 0
    for n, m in enumerate(re.finditer(r"\[\[(.+?)\]\]", text)):
        out.append(html.escape(text[i:m.start()]))
        cls, d = SCRIBBLES[n % len(SCRIBBLES)]
        out.append(f'<span class="kw {cls}">{html.escape(m.group(1))}<svg viewBox="0 0 100 10" '
                   f'preserveAspectRatio="none"><path d="{d}"/></svg></span>')
        i = m.end()
    out.append(html.escape(text[i:]))
    return "".join(out)


def authors_html(p: dict, me: set) -> str:
    """Comma-separated authors with yours underlined. Empty if unknown: never a placeholder."""
    authors = p.get("authors") or [a.strip() for a in (p.get("authors_short") or "").split(",")
                                   if a.strip() and "..." not in a and "…" not in a]
    if not authors:
        return ""
    if len(authors) > 9:  # long consortium lists stay readable
        mine = next((i for i, a in enumerate(authors) if norm(a) in me), 0)
        authors = [authors[i] for i in sorted(set(range(6)) | {mine})] + ["et al."]
    return ", ".join(f"<u>{html.escape(a)}</u>" if norm(a) in me else html.escape(a) for a in authors)


def venue_short(p: dict) -> str:
    raw = (p.get("venue") or "").strip()
    v = next((short for pat, short in VENUES if re.search(pat, raw, re.I)), raw)
    if not v and p.get("arxiv"):
        v = "arXiv"
    return " ".join(x for x in (v, str(p.get("year") or "")) if x)


def split_title(t: str):
    """'Hoi! - A Multimodal Dataset' -> ('Hoi!', 'A Multimodal Dataset')."""
    m = re.match(r"^(.{2,40}?)\s*(?::|\s[-–—]\s)\s*(.+)$", t)
    return (m.group(1).strip(), m.group(2).strip()) if m else (t, "")


def prepare(p: dict, me: set) -> dict:
    p = dict(p)
    links = p.get("links") or {}
    p["link"] = links.get("project") or links.get("arxiv") or links.get("paper") or p.get("s2_url") \
        or p.get("scholar_url") or "#"
    p["authors_html"] = authors_html(p, me)
    p["venue_short"] = venue_short(p)
    p["chips"] = [(label, links[k]) for k, label in CHIPS if links.get(k)]
    p.setdefault("teaser", {"kind": "doodle", "scene": "reading", "from": "doodle"})
    return p


def run(paths: Paths) -> Path:
    cfg = load_yaml(paths.config, {})
    pubs = {"papers": [], "synced": "never"}
    if paths.data.exists():
        pubs = json.loads(paths.data.read_text(encoding="utf-8"))
    me = {norm(n) for n in cfg.get("my_author_names", [])}
    if cfg.get("headshot") and not (paths.root / cfg["headshot"]).exists():
        cfg["headshot"] = None  # placeholder until the photo exists

    papers = [prepare(p, me) for p in pubs.get("papers", [])]
    newest = None
    if papers:
        short, rest = split_title(papers[0]["title"])
        if len(rest) > 70:
            rest = rest[:68].rsplit(" ", 1)[0] + "…"
        newest = {"short": short, "rest": rest, "link": papers[0]["link"]}

    # collaborators: only people you listed, and only once they actually co-authored something
    coauthors = {norm(a) for p in papers for a in (p.get("authors") or [])}
    crew = [c for c in cfg.get("collaborators", []) if norm(c["name"]) in coauthors]

    today = load_yaml(paths.content / "robot_today.yml", [])
    env = Environment(loader=FileSystemLoader(str(TEMPLATES)), autoescape=select_autoescape(["html", "j2"]))
    page = env.get_template("index.html.j2").render(
        cfg=cfg, bio_html=bio_html(cfg.get("bio", "")), papers=papers, newest=newest, crew=crew,
        today=today, today_js=json.dumps(today, ensure_ascii=False),
        news=load_yaml(paths.content / "news.yml", []),
        failures=load_yaml(paths.content / "failures.yml", []),
        synced=pubs.get("synced", "never"))

    paths.site.mkdir(exist_ok=True)
    (paths.site / "index.html").write_text(page, encoding="utf-8")
    if paths.assets.exists():
        shutil.copytree(paths.assets, paths.site / "assets", dirs_exist_ok=True)
    (paths.site / ".nojekyll").write_text("")  # GitHub Pages: serve files as they are
    log(f"built {paths.rel(paths.site / 'index.html')}: {len(papers)} papers, {len(crew)} collaborators")
    return paths.site / "index.html"
