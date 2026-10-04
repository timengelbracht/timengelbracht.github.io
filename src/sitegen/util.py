"""Small helpers shared by sync and build."""

from __future__ import annotations

import re
import unicodedata
from pathlib import Path
from typing import Any

import yaml


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


def load_yaml(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return yaml.safe_load(path.read_text(encoding="utf-8")) or default


def person_key(name: str) -> str:
    """'Zuria Bauer' and 'Z. Bauer' -> 'zbauer', so abbreviated names match full ones."""
    parts = [p for p in re.split(r"[\s.]+", ascii_lower(name or "")) if p]
    if not parts:
        return ""
    return re.sub(r"[^a-z]", "", parts[0][:1] + parts[-1])


def collaborators_config(cfg: dict) -> tuple:
    """(key, others, hide) from config.yml; also accepts the older plain list of people."""
    c = cfg.get("collaborators") or {}
    if isinstance(c, list):  # old format: everyone listed is "key"
        return c, [], []
    return c.get("key") or [], c.get("others", "all"), c.get("hide") or []


def is_abbreviated(name: str) -> bool:
    """'Z. Bauer' or 'A Mercurio' style author names."""
    return (
        bool(re.match(r"^([A-Z]\.?\s?)+\s?[A-Z][^.]+$", name.strip()))
        and len(name.split()[0].rstrip(".")) == 1
    )
