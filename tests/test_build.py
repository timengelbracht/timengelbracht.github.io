from sitegen import build


def test_build_renders_every_paper(repo):
    index = build.run(repo)
    html = index.read_text()
    import json
    for p in json.loads(repo.data.read_text())["papers"]:
        assert p["title"].split(":")[0] in html
    assert "co-authors" not in html          # never a placeholder author line
    assert "failure of the month" in html
    assert "photo coming soon" in html       # headshot placeholder until assets/headshot.jpg exists
    assert 'id="buddy"' not in html          # cursor robot is off unless cursor_robot: true


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
