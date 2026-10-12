from sitegen.bibtex import cite_key, entry

SPOT = {
    "title": "SpotLight: Robotic Scene Understanding",
    "authors": ["Tim Engelbracht", "René Zurbrügg"],
    "year": 2024,
    "arxiv": "2409.11870",
}


def test_cite_key() -> None:
    assert cite_key(SPOT) == "engelbracht2024spotlight"
    assert (
        cite_key({"title": "Hoi! - A Dataset", "authors": ["René Zurbrügg"], "year": 2025})
        == "zurbrugg2025hoi"
    )


def test_conference_paper() -> None:
    bib = entry(SPOT, "Humanoids 2025")
    assert bib.startswith("@inproceedings{engelbracht2025spotlight,")  # venue year, not arXiv year
    assert "year      = {2025}" in bib
    assert "booktitle = {IEEE-RAS International Conference on Humanoid Robots (Humanoids)}" in bib
    assert "author    = {Tim Engelbracht and René Zurbrügg}" in bib
    assert "eprint    = {2409.11870}" in bib


def test_preprint_and_workshop() -> None:
    assert "journal   = {arXiv preprint arXiv:2409.11870}" in entry(SPOT, "arXiv 2024")
    assert "Workshops (CVPRW)" in entry(SPOT, "CVPR Workshop 2025")


def test_doi_kept_unless_arxiv() -> None:
    p = {"title": "CroCoDL", "authors": ["Hermann Blum"], "year": 2025, "doi": "10.1109/CVPR52734.2025.02554"}
    assert "doi       = {10.1109/CVPR52734.2025.02554}" in entry(p, "CVPR 2025")
    assert "doi" not in entry({**SPOT, "doi": "10.48550/arXiv.2409.11870"}, "arXiv 2024")


def test_unknown_authors_give_nothing() -> None:
    assert entry({"title": "X", "authors": []}, "CVPR 2025") == ""


def test_title_capitals_protected() -> None:
    from sitegen.bibtex import protect

    assert protect("SpotLight: Robotic Scene Understanding") == "{SpotLight}: Robotic Scene Understanding"
    assert protect("Hoi! - A Dataset for 3D Scenes") == "{Hoi}! - A Dataset for {3D} Scenes"
    assert protect("Articulated 3D Scene Graphs") == "Articulated {3D} Scene Graphs"
