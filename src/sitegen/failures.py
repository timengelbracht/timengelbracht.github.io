"""Failure of the month: compress a clip and put it at the top of content/failures.yml."""
from __future__ import annotations

import re
from pathlib import Path

import yaml

from sitegen.media import save_video
from sitegen.paths import Paths
from sitegen.util import load_yaml, log


def add(paths: Paths, video: Path, month: str, caption: str = "", title: str = "") -> dict:
    slug = re.sub(r"[^a-z0-9]+", "-", month.lower()).strip("-")
    mp4, poster = paths.failures / f"{slug}.mp4", paths.failures / f"{slug}.webp"
    if not save_video(video.read_bytes(), mp4, poster, seconds=60, width=960, keep_audio=True):
        raise SystemExit("Could not convert the video (is ffmpeg available?).")
    entry = {"month": month, "video": paths.rel(mp4), "poster": paths.rel(poster)}
    if title:
        entry["title"] = title
    entry["caption"] = caption
    items = load_yaml(paths.content / "failures.yml", [])
    items = [e for e in items if e.get("month") != month]
    items.insert(0, entry)
    (paths.content / "failures.yml").write_text(
        "# Failure of the month, newest first. Add one with:\n"
        "#   python -m sitegen add-failure clip.mov \"November 2026\" --caption \"...\"\n"
        + yaml.safe_dump(items, allow_unicode=True, sort_keys=False), encoding="utf-8")
    log(f"added {month}: {mp4.stat().st_size / 1e6:.1f} MB")
    return entry
