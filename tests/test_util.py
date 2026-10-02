from sitegen.build import split_title, venue_short
from sitegen.util import is_abbreviated, norm, short_name, slugify


def test_short_names_and_slugs():
    assert short_name("SpotLight: Robotic Scene Understanding") == "SpotLight"
    assert short_name("Hoi! - A Multimodal Dataset") == "Hoi"
    assert short_name("Spot-On: A Mixed Reality Interface") == "Spot-On"
    assert slugify("Spot-On: A Mixed Reality Interface") == "spot-on"
    assert slugify("Articulated 3D Scene Graphs for Open-World Mobile Manipulation") == \
        "articulated-3d-scene-graphs-for-open-wor"


def test_norm_ignores_case_accents_punctuation():
    assert norm("René Zurbrügg") == norm("rene zurbrugg")
    assert norm("Hoi! - A Dataset") == norm("Hoi A dataset")


def test_abbreviated_names():
    assert is_abbreviated("Z. Bauer")
    assert is_abbreviated("A. Mercurio")
    assert not is_abbreviated("Zuria Bauer")
    assert not is_abbreviated("Tim Engelbracht")


def test_title_split_for_sticky_note():
    assert split_title("Hoi! - A Multimodal Dataset") == ("Hoi!", "A Multimodal Dataset")
    assert split_title("Spot-On: A Mixed Reality") == ("Spot-On", "A Mixed Reality")
    assert split_title("Articulated 3D Scene Graphs")[1] == ""


def test_venue_short():
    assert venue_short({"venue": "Computer Vision and Pattern Recognition", "year": 2025}) == "CVPR 2025"
    assert venue_short({"venue": "arXiv.org", "year": 2026}) == "arXiv 2026"
    assert venue_short({"venue": "", "arxiv": "2409.11870", "year": 2024}) == "arXiv 2024"
