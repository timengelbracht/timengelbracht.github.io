import io

from PIL import Image

from sitegen import teasers


def _pdf_with_figure():
    try:
        import pymupdf as fitz
    except ImportError:
        import fitz
    doc = fitz.open()
    page = doc.new_page()
    buf = io.BytesIO()
    Image.new("RGB", (800, 400), (30, 120, 200)).save(buf, "PNG")
    # two pictures side by side above the caption, like a teaser collage
    page.insert_image(fitz.Rect(50, 60, 300, 260), stream=buf.getvalue())
    page.insert_image(fitz.Rect(310, 60, 560, 260), stream=buf.getvalue())
    page.insert_text((50, 280), "Figure 1. Our teaser.")
    page.insert_text((50, 330), "Abstract. Lorem ipsum.")
    return doc.tobytes()


def test_figure_from_pdf_takes_whole_collage_above_caption():
    png = teasers.figure_from_pdf(_pdf_with_figure())
    im = Image.open(io.BytesIO(png))
    assert im.width > im.height * 2  # both pictures, not just one


def test_cvf_pdf_url_is_built_from_title_and_first_author():
    p = {"title": "CroCoDL: Cross-device Collaborative Dataset for Localization", "year": 2025,
         "venue": "Computer Vision and Pattern Recognition", "authors": ["Hermann Blum", "Zuria Bauer"]}
    assert teasers.cvf_pdf_url(p) == ("https://openaccess.thecvf.com/content/CVPR2025/papers/"
                                     "Blum_CroCoDL_Cross-device_Collaborative_Dataset_for_Localization_CVPR_2025_paper.pdf")


def test_doodle_scene_by_keywords():
    assert teasers.doodle({"title": "SpotLight", "abstract": "light switches"})["scene"] == "switch"
    assert teasers.doodle({"title": "Something else", "abstract": ""})["scene"] == "reading"


def test_teaser_from_pdf_step(repo, monkeypatch):
    raw = _pdf_with_figure()
    monkeypatch.setattr(teasers, "get", lambda url, **kw: raw if kw.get("binary") else None)
    p = {"title": "CroCoDL: Cross-device Collaborative Dataset for Localization", "slug": "crocodl", "year": 2025,
         "venue": "CVPR", "authors": ["Hermann Blum"], "links": {}}
    t = teasers.Teasers(repo).paper_pdf(p)
    assert t["from"] == "paper PDF figure" and (repo.root / t["src"]).exists()
