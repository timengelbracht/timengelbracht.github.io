"""Small helpers shared by sync and build."""
from __future__ import annotations

import re
import sys
import unicodedata
from pathlib import Path

import yaml


def log(*args) -> None:
    print("[sitegen]", *args, file=sys.stderr, flush=True)


def ascii_lower(s: str) -> str:
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()


def norm(s: str) -> str:
    """Compare titles or names ignoring case, accents and punctuation."""
    return re.sub(r"[^a-z0-9]+", "", ascii_lower(s or ""))


def short_name(title: str) -> str:
    """'SpotLight: Robotic Scene ...' -> 'SpotLight'; 'Hoi! - A Multimodal ...' -> 'Hoi'."""
    return re.split(r"[:!]|\s[-–—]\s", title, maxsplit=1)[0].strip()


def slugify(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", ascii_lower(short_name(title))).strip("-")[:40] or "paper"


def load_yaml(path: Path, default):
    if not path.exists():
        return default
    return yaml.safe_load(path.read_text(encoding="utf-8")) or default


def is_abbreviated(name: str) -> bool:
    """'Z. Bauer' or 'A Mercurio' style author names."""
    return bool(re.match(r"^([A-Z]\.?\s?)+\s?[A-Z][^.]+$", name.strip())) and len(name.split()[0].rstrip(".")) == 1
