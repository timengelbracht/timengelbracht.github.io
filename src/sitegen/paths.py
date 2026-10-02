"""Where everything lives inside the repository."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


def find_root(start: Path | None = None) -> Path:
    """The repository root is the nearest folder (upwards) that contains config.yml."""
    here = (start or Path.cwd()).resolve()
    for d in (here, *here.parents):
        if (d / "config.yml").exists():
            return d
    raise SystemExit("config.yml not found. Run this from inside the website repository.")


@dataclass(frozen=True)
class Paths:
    root: Path

    @property
    def config(self) -> Path:
        return self.root / "config.yml"

    @property
    def content(self) -> Path:
        return self.root / "content"

    @property
    def data(self) -> Path:
        return self.root / "data" / "publications.json"

    @property
    def assets(self) -> Path:
        return self.root / "assets"

    @property
    def teasers(self) -> Path:
        return self.assets / "teasers"

    @property
    def failures(self) -> Path:
        return self.assets / "failures"

    @property
    def overrides(self) -> Path:
        return self.root / "overrides"

    @property
    def site(self) -> Path:
        return self.root / "site"

    def rel(self, p: Path) -> str:
        return p.relative_to(self.root).as_posix()
