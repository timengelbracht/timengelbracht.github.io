from sitegen import build


def test_build_renders_every_paper(repo):
    index = build.run(repo)
    html = index.read_text()
    import json
    for p in json.loads(repo.data.read_text())["papers"]:
        assert p["title"].split(":")[0] in html
    assert "co-authors" not in html          # never a placeholder author line
    assert "failure of the month" in html
    has_photo = (repo.root / "assets/headshot.jpg").exists()
    assert ("photo coming soon" in html) != has_photo  # placeholder only until the photo exists
    assert 'id="buddy"' not in html          # cursor robot is off unless cursor_robot: true
    assert 'id="lightSwitch"' not in html    # light switch is off unless light_switch: true
    assert "<b>now:</b>" not in html         # "now" line is left out while empty


def test_unknown_authors_render_nothing():
    assert build.authors_html({"title": "X"}, set()) == ""
    assert build.authors_html({"authors_short": "T Engelbracht, R Zurbrügg, ..."}, set()) == "T Engelbracht, R Zurbrügg"


def test_my_name_is_underlined():
    out = build.authors_html({"authors": ["Tim Engelbracht", "René Zurbrügg"]}, {"timengelbracht"})
    assert out.startswith("<u>Tim Engelbracht</u>")


def test_cursor_robot_can_be_switched_on(repo):
    repo.config.write_text(repo.config.read_text().replace("cursor_robot: false", "cursor_robot: true"))
    assert 'id="buddy"' in build.run(repo).read_text()


def test_venues_from_paper_links_show_without_sync(repo):
    html = build.run(repo).read_text()
    assert '<span class="venue">CVPR 2026</span>' in html
    assert '<span class="venue">Humanoids 2025</span>' in html


def test_contact_themes_and_link_previews(repo):
    html = build.run(repo).read_text()
    assert "tengelbracht [at] ethz.ch" in html and "tengelbracht@ethz.ch" not in html  # no plain address
    assert "what I work on" in html and "Work with me" in html
    assert 'href="#p-hoi"' in html and 'id="p-hoi"' in html                         # theme -> paper links
    assert 'property="og:image" content="https://timengelbracht.github.io/assets/social.png"' in html
    assert "YOUR_SCHOLAR_ID" not in html                                              # placeholder link hidden
    assert "shout-out to my collaborators" in html


def test_bio_links_and_keywords():
    out = build.bio_html("at the [ETH AI Center](https://ai.ethz.ch) on [[scene understanding]]")
    assert '<a href="https://ai.ethz.ch"' in out and 'class="kw k1"' in out


def test_new_papers_join_themes_by_keyword():
    themes = [{"title": "Forces", "papers": [], "match": "force"}]
    papers = [{"slug": "xyz", "title": "Xyz: something", "abstract": "we measure contact force"}]
    assert build.themes_with_papers(themes, papers)[0]["paper_refs"] == [{"slug": "xyz", "short": "Xyz"}]
