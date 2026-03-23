from security.miniai import DarkelfMiniAISentinel


def test_miniai_flags_suspicious_url():
    ai = DarkelfMiniAISentinel()

    url = "http://example.com/verify-account"

    ai.monitor_network(url)

    assert len(ai.events) > 0
    event = ai.events[-1]
    assert event["url"] == url.lower()
    assert "PHISHING" in event["threats"]
    assert event["risk_level"] in ("high", "critical")


def test_miniai_allows_normal_url():
    ai = DarkelfMiniAISentinel()

    url = "https://example.com"

    ai.monitor_network(url)

    assert len(ai.events) > 0
    event = ai.events[-1]
    assert event["url"] == url.lower()
    assert event["risk_level"] == "low"
