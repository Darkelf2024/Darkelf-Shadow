from adblock.easylist_engine import EasyListEngine


def test_adblock_blocks_known_ad():
    engine = EasyListEngine()

    url = "https://ads.doubleclick.net/banner.js"
    first_party = "https://example.com"

    result = engine.should_block(url, first_party, req_type="script")

    assert result is True


def test_adblock_allows_normal_site():
    engine = EasyListEngine()

    url = "https://example.com/script.js"
    first_party = "https://example.com"

    result = engine.should_block(url, first_party, req_type="script")

    assert result is False


# 🔥 NEW: test Google Analytics (real tracker)
def test_blocks_google_analytics():
    engine = EasyListEngine()

    url = "https://www.google-analytics.com/collect"
    first_party = "https://example.com"

    result = engine.should_block(url, first_party, req_type="xmlhttprequest")

    assert result is True


# 🔥 NEW: ensure first-party is NOT blocked
def test_allows_first_party_request():
    engine = EasyListEngine()

    url = "https://example.com/api/data"
    first_party = "https://example.com"

    result = engine.should_block(url, first_party, req_type="xmlhttprequest")

    assert result is False


# 🔥 NEW: image rule (should NOT block normal images)
def test_allows_image_cdn():
    engine = EasyListEngine()

    url = "https://cdn.example.com/image.png"
    first_party = "https://example.com"

    result = engine.should_block(url, first_party, req_type="image")

    assert result is False


# 🔥 NEW: third-party ad script detection
def test_blocks_third_party_ad_script():
    engine = EasyListEngine()

    url = "https://adservice.google.com/script.js"
    first_party = "https://example.com"

    result = engine.should_block(url, first_party, req_type="script")

    assert result is True
