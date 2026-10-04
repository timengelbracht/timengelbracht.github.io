"""Failure of the month: compress a clip and put it at the top of content/failures.yml."""

from __future__ import annotations

import logging
import time
from pathlib import Path

import yaml

from sitegen.media import save_video
from sitegen.paths import Paths
from sitegen.util import load_yaml

logger = logging.getLogger(__name__)


def add(paths: Paths, video: Path, caption: str = "", title: str = "") -> dict:
    slug = time.strftime("%Y-%m-%d")  # file name only; the page shows no date, so nothing goes stale
    n = 1
    while (paths.failures / f"{slug}.mp4").exists():  # never overwrite an earlier failure
        n += 1
        slug = f"{time.strftime('%Y-%m-%d')}-{n}"
    mp4, poster = paths.failures / f"{slug}.mp4", paths.failures / f"{slug}.webp"
    if not save_video(video.read_bytes(), mp4, poster, seconds=60, width=960, keep_audio=True):
        raise SystemExit("Could not convert the video (is ffmpeg available?).")
    entry = {"video": paths.rel(mp4), "poster": paths.rel(poster)}
    if title:
        entry["title"] = title
    entry["caption"] = caption
    items = load_yaml(paths.content / "failures.yml", [])
    items = [e for e in items if e.get("video") != entry["video"]]
    items.insert(0, entry)
    (paths.content / "failures.yml").write_text(
        "# Failure of the month. The first entry is shown; older ones become small links.\n"
        '# Add one with:  sitegen add-failure clip.mov --caption "..." --title "..."\n'
        + yaml.safe_dump(items, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    logger.info(f"added {paths.rel(mp4)}: {mp4.stat().st_size / 1e6:.1f} MB")
    return entry
