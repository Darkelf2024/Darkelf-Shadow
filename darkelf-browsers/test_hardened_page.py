from browser.hardened_page import HardenedWebPage


def test_hardened_page_initialization():
    page = HardenedWebPage(parent=None, profile=None)

    assert page is not None
    assert hasattr(page, "_canvas_seed")


def test_canvas_seed_random():
    p1 = HardenedWebPage()
    p2 = HardenedWebPage()

    assert p1._canvas_seed != p2._canvas_seed
