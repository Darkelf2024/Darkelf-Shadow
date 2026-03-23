from browser.browser_window import DarkelfBrowser


def test_short_label():
    class DummyUrl:
        def host(self):
            return "www.youtube.com"

    label = DarkelfBrowser._short_label_from_qurl(DummyUrl())

    assert label == "YouTube"


def test_short_label_generic():
    class DummyUrl:
        def host(self):
            return "example.com"

    label = DarkelfBrowser._short_label_from_qurl(DummyUrl())

    assert label == "Example"
