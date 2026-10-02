"""Shared fixtures. Tests never touch the network: sitegen.http.get is replaced."""
from __future__ import annotations

import shutil
import time
from pathlib import Path

import pytest

from sitegen.paths import Paths

REPO = Path(__file__).resolve().parent.parent


class FakeResponse:
    def __init__(self, url, text="<html>error</html>", status=200, data=None):
        self.url, self.text, self.status_code = url, text, status
        self.content = text.encode()
        self._data = data

    def json(self):
        if self._data is None:
            raise ValueError("not json")
        return self._data


@pytest.fixture
def repo(tmp_path) -> Paths:
    """A throwaway copy of the repository's config, content and data."""
    for name in ("config.yml", "content", "data", "assets"):
        src = REPO / name
        if src.is_dir():
            shutil.copytree(src, tmp_path / name)
        elif src.exists():
            shutil.copy(src, tmp_path / name)
    (tmp_path / "assets" / "teasers").mkdir(parents=True, exist_ok=True)
    return Paths(tmp_path)


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    monkeypatch.setattr(time, "sleep", lambda *_: None)


@pytest.fixture
def offline(monkeypatch):
    """Every request answers with an HTML error page (the worst realistic case)."""
    def fake_get(url, **kw):
        return None if kw.get("binary") else FakeResponse(url)

    for mod in ("sitegen.http", "sitegen.links", "sitegen.teasers", "sitegen.sources.scholar",
                "sitegen.sources.semantic_scholar", "sitegen.sources.arxiv", "sitegen.sources.openalex",
                "sitegen.sources.dblp"):
        monkeypatch.setattr(f"{mod}.get", fake_get)
    return fake_get
