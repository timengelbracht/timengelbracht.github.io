"""Pick a teaser for each paper, fully automatically.

Order (first hit wins):
  1. overrides/<slug>/teaser.*               your own file, optional
  2. project page                              looping video, og:image, or an image named *teaser*
  3. arXiv HTML                                Figure 1
  4. arXiv LaTeX source                        teaser.* or the first included figure
  5. paper PDF                                 Figure 1 region on page 1 (or the largest picture)
  6. doodle                                    a drawn scene chosen by keywords
"""
from __future__ import annotations

import io
import re
import tarfile
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from sitegen.http import get
from sitegen.media import save_image, save_video
from sitegen.paths import Paths
from sitegen.sources import arxiv
from sitegen.util import log

VIDEO_EXT = (".mp4", ".webm", ".mov")
IMAGE_EXT = (".png", ".jpg", ".jpeg", ".webp", ".gif")


class Teasers:
    def __init__(self, paths: Paths):
        self.paths = paths

    # -- helpers ---------------------------------------------------------------
    def _image(self, p, raw, source):
        out = self.paths.teasers / f"{p['slug']}.webp"
        if raw and save_image(raw, out):
            return {"kind": "image", "src": self.paths.rel(out), "from": source}
        return None

    def _video(self, p, raw, source):
        mp4 = self.paths.teasers / f"{p['slug']}.mp4"
        poster = self.paths.teasers / f"{p['slug']}.webp"
        if raw and save_video(raw, mp4, poster):
            return {"kind": "video", "src": self.paths.rel(mp4), "poster": self.paths.rel(poster), "from": source}
        return None

    # -- steps -----------------------------------------------------------------
    def override(self, p):
        d = self.paths.overrides / p["slug"]
        if not d.is_dir():
            return None
        for f in sorted(d.iterdir()):
            if f.stem != "teaser":
                continue
            if f.suffix.lower() in VIDEO_EXT:
                return self._video(p, f.read_bytes(), "your override")
            if f.suffix.lower() in IMAGE_EXT:
                return self._image(p, f.read_bytes(), "your override")
        return None

    def project_page(self, p):
        url = (p.get("links") or {}).get("project")
        if not url:
            return None
        r = get(url)
        if r is None:
            return None
        soup = BeautifulSoup(r.text, "html.parser")
        videos = []
        for v in soup.find_all("video"):
            src = v.get("src") or (v.find("source") or {}).get("src")
            if src:
                videos.append(urljoin(r.url, src))
        videos.sort(key=lambda s: 0 if re.search(r"teaser|hero|overview|intro", s, re.I) else 1)
        for src in videos[:2]:
            raw = get(src, binary=True, timeout=60)
            if raw and len(raw) < 80_000_000:
                t = self._video(p, raw, "project page video")
                if t:
                    return t
        images = []
        og = soup.find("meta", property="og:image") or soup.find("meta", attrs={"name": "og:image"})
        if og and og.get("content"):
            images.append(urljoin(r.url, og["content"]))
        images += [urljoin(r.url, i["src"]) for i in soup.find_all("img", src=True)
                   if re.search(r"teaser", i["src"], re.I)]
        for src in images:
            t = self._image(p, get(src, binary=True), "project page")
            if t:
                return t
        return None

    def arxiv_html(self, p):
        got = arxiv.html_page(p)
        if not got:
            return None
        soup, url = got
        fig = soup.select_one("figure.ltx_figure img, figure img")
        if not fig or not fig.get("src"):
            return None
        base_tag = soup.find("base", href=True)
        base = urljoin(url, base_tag["href"]) if base_tag else url
        for cand in dict.fromkeys([urljoin(base, fig["src"]), urljoin(url + "/", fig["src"])]):  # arXiv pages vary
            raw = get(cand, binary=True, tries=1)
            if raw:
                return self._image(p, raw, "arXiv, Figure 1")
        return None

    def arxiv_source(self, p):
        if not p.get("arxiv"):
            return None
        raw = get(f"https://arxiv.org/e-print/{p['arxiv']}", binary=True, timeout=60)
        if not raw:
            return None
        try:
            tar = tarfile.open(fileobj=io.BytesIO(raw))
        except tarfile.TarError:
            return None
        names = [m.name for m in tar.getmembers() if m.isfile()]
        graphics = [n for n in names if re.search(r"\.(png|jpe?g|pdf)$", n, re.I)]
        pick = next((n for n in graphics if re.search(r"teaser", n, re.I)), None)
        if not pick:  # first \includegraphics in any tex file
            for n in names:
                if not n.endswith(".tex"):
                    continue
                tex = tar.extractfile(n).read().decode("utf-8", "ignore")
                m = re.search(r"\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}", tex)
                if m:
                    pick = next((g for g in graphics if m.group(1) in g), None)
                    if pick:
                        break
        if not pick:
            return None
        data = tar.extractfile(pick).read()
        if pick.lower().endswith(".pdf"):
            data = render_pdf_page(data)
        return self._image(p, data, "arXiv source figure") if data else None

    def paper_pdf(self, p):
        for url in pdf_candidates(p):
            raw = get(url, binary=True, timeout=60, tries=2)
            if raw and raw[:5] == b"%PDF-":
                png = figure_from_pdf(raw)
                if png:
                    return self._image(p, png, "paper PDF figure")
        return None

    # -- main ------------------------------------------------------------------
    def find(self, p: dict, previous: dict | None) -> dict:
        # Keep a real teaser from an earlier run (stable, saves bandwidth) unless you added an override.
        if (previous and previous.get("kind") in ("video", "image") and (self.paths.root / previous["src"]).exists()
                and previous.get("from") != "your override" and not (self.paths.overrides / p["slug"]).is_dir()):
            return previous
        for step in (self.override, self.project_page, self.arxiv_html, self.arxiv_source, self.paper_pdf):
            try:
                t = step(p)
            except Exception as e:
                log(f"  ! teaser step {step.__name__} crashed: {type(e).__name__}: {e}")
                t = None
            if t:
                return t
        return doodle(p)


# -- PDF helpers ---------------------------------------------------------------

CVF_VENUES = {"cvpr": "CVPR", "iccv": "ICCV", "wacv": "WACV"}


def pdf_candidates(p: dict) -> list[str]:
    """Possible PDF URLs for a paper, best first."""
    out = []
    if p.get("arxiv"):
        out.append(f"https://arxiv.org/pdf/{p['arxiv']}")
    if p.get("pdf_url"):
        out.append(p["pdf_url"])
    paper = (p.get("links") or {}).get("paper") or p.get("paper_url") or ""
    if "openaccess.thecvf.com" in paper and "/html/" in paper:
        out.append(paper.replace("/html/", "/papers/").replace(".html", ".pdf"))
    elif paper.lower().endswith(".pdf"):
        out.append(paper)
    cvf = cvf_pdf_url(p)
    if cvf:
        out.append(cvf)
    return list(dict.fromkeys(out))


def cvf_pdf_url(p: dict) -> str | None:
    """CVF open-access URLs follow a fixed pattern: <Surname>_<Title_Words>_<VENUE>_<year>_paper.pdf"""
    venue = (p.get("venue") or "") + " " + ((p.get("links") or {}).get("paper") or "") + " " + (p.get("doi") or "")
    key = next((k for k in CVF_VENUES if k in venue.lower()), None)
    if not key and "computer vision and pattern recognition" in venue.lower():
        key = "cvpr"
    authors = p.get("authors") or []
    year = p.get("year")
    if not key or not authors or not year:
        return None
    v = CVF_VENUES[key]
    surname = authors[0].split()[-1]
    title = re.sub(r"[^\w\s-]", "", p["title"]).strip()
    title = re.sub(r"\s+", "_", title)
    return f"https://openaccess.thecvf.com/content/{v}{year}/papers/{surname}_{title}_{v}_{year}_paper.pdf"


def _fitz():
    try:
        import pymupdf as fitz
    except ImportError:  # older PyMuPDF
        import fitz
    return fitz


def render_pdf_page(data: bytes, dpi: int = 110) -> bytes | None:
    try:
        fitz = _fitz()
        return fitz.open(stream=data, filetype="pdf")[0].get_pixmap(dpi=dpi).tobytes("png")
    except Exception:
        return None


def figure_from_pdf(raw: bytes) -> bytes | None:
    """The Figure 1 region on page 1-2: everything drawn above the 'Figure 1'/'Fig. 1' caption.

    Falls back to the single largest picture if there is no caption to anchor on.
    """
    try:
        fitz = _fitz()
        doc = fitz.open(stream=raw, filetype="pdf")
    except Exception:
        return None
    for page in list(doc)[:2]:
        caption = (page.search_for("Figure 1") or page.search_for("Fig. 1") or [None])[0]
        pics = [fitz.Rect(i["bbox"]) for i in page.get_image_info()]
        pics += [d["rect"] for d in page.get_drawings() if d["rect"].width > 20 and d["rect"].height > 20]
        if caption is not None:
            above = [r for r in pics if r.y1 <= caption.y0 + 4 and r.y0 >= caption.y0 - page.rect.height * 0.7
                     and r.width > 15]
            if above:
                region = fitz.Rect(above[0])
                for r in above[1:]:
                    region |= r
                if region.width > page.rect.width * 0.35 and region.height > 60:
                    return page.get_pixmap(dpi=150, clip=region).tobytes("png")
    best = None  # fallback: largest raster picture
    for page in list(doc)[:2]:
        for info in page.get_image_info():
            r = fitz.Rect(info["bbox"])
            if r.width > page.rect.width * 0.35 and (best is None or r.get_area() > best[1].get_area()):
                best = (page, r)
    if best:
        return best[0].get_pixmap(dpi=150, clip=best[1]).tobytes("png")
    return None


# -- doodles -------------------------------------------------------------------

DOODLES = [  # (scene, keywords): first match wins; the template draws these scenes
    ("switch", r"light switch|switch|lamp"),
    ("drawer", r"drawer|articulat|cabinet|door|open"),
    ("graph", r"scene graph|map|locali[sz]|3d scene"),
    ("camera", r"camera|video|egocentric|view"),
    ("hand", r"grasp|hand|manipulat|force|tactile"),
]


def doodle(p: dict) -> dict:
    text = (p["title"] + " " + (p.get("abstract") or "")).lower()
    for scene, pattern in DOODLES:
        if re.search(pattern, text):
            return {"kind": "doodle", "scene": scene, "from": "doodle"}
    return {"kind": "doodle", "scene": "reading", "from": "doodle"}
