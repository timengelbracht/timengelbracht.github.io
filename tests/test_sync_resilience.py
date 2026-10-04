"""The sync must never make the site worse when sources are down or misbehave."""

import json

from sitegen import sync


def test_everything_down_keeps_all_papers(repo, offline):
    before = json.loads(repo.data.read_text())["papers"]
    out = sync.run(repo)
    assert {p["title"] for p in out} == {p["title"] for p in before}
    after = {p["title"]: p for p in json.loads(repo.data.read_text())["papers"]}
    for p in before:  # authors, abstracts and teasers survive
        assert after[p["title"]].get("authors") == p.get("authors")
        assert after[p["title"]].get("abstract") == p.get("abstract")
        assert after[p["title"]]["teaser"] == p["teaser"]


def test_no_duplicates_when_slug_changes(repo, offline):
    data = json.loads(repo.data.read_text())
    clone = dict(data["papers"][0], slug="an-old-slug")
    data["papers"].append(clone)
    repo.data.write_text(json.dumps(data))
    out = sync.run(repo)
    titles = [p["title"] for p in out]
    assert len(titles) == len(set(titles))


def test_merge_by_title_first_value_wins():
    merged = sync.merge(
        [
            [{"title": "SpotLight: X", "year": 2024}],
            [{"title": "Spotlight: x", "abstract": "abc", "year": 1999}],
        ]
    )
    assert merged == [{"title": "SpotLight: X", "year": 2024, "abstract": "abc"}]


def test_full_names_beat_abbreviations():
    assert sync.better_authors(
        ["Hermann Blum", "A. Mercurio", "Z. Bauer"], ["Hermann Blum", "Alessandro Mercurio", "Zuria Bauer"]
    )
    assert not sync.better_authors(["Hermann Blum", "Zuria Bauer"], ["H. Blum", "Z. Bauer"])
