from sitegen import links

PAPER = {
    "title": "Articulated 3D Scene Graphs for Open-World Mobile Manipulation",
    "authors": ["Martin Büchner", "Adrian Röfer", "Tim Engelbracht"],
}


def test_classify_sorts_links_by_kind():
    out = links.classify(
        [
            "https://boysun045.github.io/LIME-Page/",
            "https://github.com/cvg/crocodl-benchmark",
            "https://youtu.be/abc.",
            "https://photos.app.goo.gl/xyz",
            "https://huggingface.co/CroCoDL",
            "https://arxiv.org/abs/1234.5678",
            "https://doi.org/10.1/x",
        ],
        {},
    )
    assert out == {
        "project": "https://boysun045.github.io/LIME-Page/",
        "code": "https://github.com/cvg/crocodl-benchmark",
        "video": "https://youtu.be/abc",
        "data": "https://huggingface.co/CroCoDL",
    }


def test_page_must_mention_the_paper():
    good = (
        "<html><body>"
        + "x" * 600
        + " Articulated scene graphs for mobile manipulation by Büchner, Röfer</body></html>"
    )
    parked = "<html><body>" + "y" * 600 + " This domain is for sale</body></html>"
    assert links.page_mentions_paper(good, PAPER)
    assert not links.page_mentions_paper(parked, PAPER)


def test_project_page_guesses():
    g = links.guesses({"title": "ForceTwin: Physics-informed"}, ["https://timengelbracht.github.io/{short}/"])
    assert "https://timengelbracht.github.io/forcetwin-website/" in g
    assert "https://timengelbracht.github.io/ForceTwin/" in g


def test_arxiv_doi_is_not_a_separate_paper_link():
    assert links.is_arxiv_doi("https://doi.org/10.48550/arXiv.2607.02417")
    assert not links.is_arxiv_doi("https://doi.org/10.1109/CVPR52734.2025.02554")
