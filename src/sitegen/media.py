"""Image and video conversion for teasers and the failure of the month."""
from __future__ import annotations

import io
import shutil
import subprocess
from pathlib import Path

from PIL import Image

from sitegen.util import log


def ffmpeg_bin() -> str | None:
    if shutil.which("ffmpeg"):
        return "ffmpeg"
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return None


def save_image(raw: bytes, dest: Path, max_w: int = 900) -> bool:
    """Convert any image to a white-backed WebP, at most max_w wide. Rejects icons and logos."""
    try:
        im = Image.open(io.BytesIO(raw))
        if im.mode in ("P", "LA"):
            im = im.convert("RGBA")
        if im.mode == "RGBA":  # flatten transparent figures onto white
            bg = Image.new("RGB", im.size, "white")
            bg.paste(im, mask=im.split()[-1])
            im = bg
        im = im.convert("RGB")
        if im.width < 160 or im.height < 90:
            return False
        if im.width > max_w:
            im = im.resize((max_w, round(im.height * max_w / im.width)), Image.LANCZOS)
        dest.parent.mkdir(parents=True, exist_ok=True)
        im.save(dest, "WEBP", quality=82)
        return True
    except Exception as e:
        log("  ! image conversion failed:", e)
        return False


def save_video(raw: bytes, dest_mp4: Path, dest_poster: Path, *, seconds: float = 6, width: int = 480,
               keep_audio: bool = False, crf: int = 30) -> bool:
    """Trim and compress a video to an MP4 (H.264, faststart) plus a WebP poster frame."""
    ff = ffmpeg_bin()
    if not ff:
        log("  ! no ffmpeg available; skipping video")
        return False
    dest_mp4.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest_mp4.with_suffix(".src")
    tmp.write_bytes(raw)
    audio = ["-c:a", "aac", "-b:a", "64k"] if keep_audio else ["-an"]
    try:
        subprocess.run([ff, "-y", "-loglevel", "error", "-i", str(tmp), "-t", str(seconds),
                        "-vf", f"scale={width}:-2", "-c:v", "libx264", "-preset", "slow", "-pix_fmt", "yuv420p",
                        "-crf", str(crf), *audio, "-movflags", "+faststart", str(dest_mp4)],
                       check=True, timeout=300)
        subprocess.run([ff, "-y", "-loglevel", "error", "-ss", "1", "-i", str(dest_mp4), "-frames:v", "1",
                        str(dest_poster)], check=True, timeout=60)
        return dest_mp4.exists() and dest_mp4.stat().st_size > 0
    except Exception as e:
        log("  ! video conversion failed:", e)
        return False
    finally:
        if tmp.exists():
            tmp.unlink()
