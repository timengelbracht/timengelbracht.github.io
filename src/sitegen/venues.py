"""Conference and journal names: recognising them and writing them short ("CVPR 2026")."""
from __future__ import annotations

import re

VENUES = [  # (pattern, short name); first match wins, so specific names come first
    (r"humanoid", "Humanoids"),
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
    (r"science robotics", "Science Robotics"),
    (r"arxiv", "arXiv"),
]
YEAR = re.compile(r"\b(20\d{2})\b")


def short(raw: str, year=None) -> str:
    """'2025 IEEE/CVF Conference on Computer Vision and Pattern Recognition Workshops' -> 'CVPR Workshop 2025'.

    Text that already reads like a short venue with a year ("Humanoids 2025") is kept as written.
    """
    raw = (raw or "").strip()
    if not raw:
        return ""
    m = YEAR.search(raw)
    if m and len(raw) <= 30:
        return raw
    name = next((s for pat, s in VENUES if re.search(pat, raw, re.I)), raw)
    if name != "arXiv" and re.search(r"workshop", raw, re.I):
        name += " Workshop"
    y = m.group(1) if m else (str(year) if year else "")
    return f"{name} {y}".strip()


def from_text(text: str) -> str | None:
    """Find 'accepted at CVPR 2026' style statements, e.g. in an arXiv comment."""
    text = text or ""
    if not re.search(r"accept|to appear|published|camera.?ready|\bat\b|\bin\b", text, re.I):
        return None
    for pat, name in VENUES:
        if name == "arXiv":
            continue
        m = re.search(rf"(?:{pat})[^.;]{{0,40}}?(?:'|’)?(\d{{4}}|\d{{2}})\b", text, re.I)
        if m:
            y = m.group(1)
            y = y if len(y) == 4 else f"20{y}"
            ws = " Workshop" if re.search(r"workshop", text, re.I) else ""
            return f"{name}{ws} {y}"
    return None


def is_published(label: str) -> bool:
    return bool(label) and not label.lower().startswith("arxiv")
