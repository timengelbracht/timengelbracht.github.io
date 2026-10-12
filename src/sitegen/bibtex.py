"""BibTeX entries for the paper list, built from the synced metadata."""

from __future__ import annotations

import re

from sitegen import venues
from sitegen.util import ascii_lower, short_name

JOURNALS = {"RA-L", "Science Robotics"}


def protect(title: str) -> str:
    """Brace the short name and words like 'SpotLight' or '3D' so BibTeX styles keep their capitals."""
    name = short_name(title)
    has_name = bool(name) and name != title and title.startswith(name)
    rest = title[len(name) :] if has_name else title
    words = re.sub(r"\b(\w*[A-Z0-9]\w*[A-Z]\w*)\b", r"{\1}", rest)
    return f"{{{name}}}{words}" if has_name else words


def year_of(p: dict, label: str) -> str:
    """The venue's year for published papers ('CVPR 2026'), else the year it appeared."""
    m = re.search(r"(\d{4})$", label or "")
    return m.group(1) if m and venues.is_published(label) else str(p.get("year") or "")


def cite_key(p: dict, year: str = "") -> str:
    """'engelbracht2024spotlight': first author's surname, year, first title word."""
    authors = p.get("authors") or []
    surname = ascii_lower(authors[0].split()[-1]) if authors else "anon"
    word = next((w for w in re.findall(r"[a-z0-9]+", ascii_lower(p.get("title", ""))) if len(w) > 2), "paper")
    return re.sub(r"[^a-z0-9]", "", surname) + (year or str(p.get("year") or "")) + word


def _field(name: str, value: str) -> str:
    return f"  {name:<9} = {{{value}}}"


def entry(p: dict, label: str) -> str:
    """BibTeX for one paper. `label` is the short venue ("CVPR 2025"); without a real venue
    the paper is cited as an arXiv preprint. Empty if title or authors are unknown."""
    authors = p.get("authors") or []
    if not p.get("title") or not authors:
        return ""
    year = year_of(p, label)
    fields = [_field("title", protect(p["title"])), _field("author", " and ".join(authors))]
    name = re.sub(r"\s*\d{4}$", "", label)
    if label and venues.is_published(label):
        kind = "article" if name in JOURNALS else "inproceedings"
        fields.append(_field("journal" if kind == "article" else "booktitle", venues.full(name)))
    elif p.get("arxiv"):
        kind = "article"
        fields.append(_field("journal", f"arXiv preprint arXiv:{p['arxiv']}"))
    else:
        kind = "misc"
    if year:
        fields.append(_field("year", year))
    doi = p.get("doi") or ""
    if doi and "arxiv" not in doi.lower():
        fields.append(_field("doi", doi))
    if p.get("arxiv"):
        fields += [_field("eprint", p["arxiv"]), _field("archivePrefix", "arXiv")]
    return f"@{kind}{{{cite_key(p, year)},\n" + ",\n".join(fields) + "\n}"
