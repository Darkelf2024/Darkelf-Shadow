from utils.url_utils import sanitize_url_clearurls

def test_url_sanitization_removes_tracking():
    url = "https://example.com/?utm_source=test&id=1"
    cleaned = sanitize_url_clearurls(url)

    assert "utm_source" not in cleaned
    assert "id=1" in cleaned


def test_url_sanitization_no_query():
    url = "https://example.com/"
    cleaned = sanitize_url_clearurls(url)

    assert cleaned.startswith("https://example.com")
