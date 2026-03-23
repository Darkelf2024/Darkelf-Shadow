# test_miniai_performance.py
import pytest
import time
import tracemalloc
from security.miniai import DarkelfMiniAISentinel


@pytest.mark.performance
def test_miniai_performance():
    ai = DarkelfMiniAISentinel()

    urls = [
        "https://example.com",
        "https://ads.doubleclick.net/banner.js",
        "https://google-analytics.com/collect",
        "https://example.com/script.js",
        "https://tracker.facebook.net/pixel",
    ] * 1000  # 5k requests

    start = time.perf_counter()

    for url in urls:
        ai.monitor_network(url)

    duration = time.perf_counter() - start

    total = len(urls)
    rps = total / duration

    print(f"\n[PERF] {total} requests in {duration:.3f}s ({rps:.0f} req/sec)")

    assert rps > 1000


def test_miniai_stress():
    ai = DarkelfMiniAISentinel()

    start = time.perf_counter()

    for i in range(10000):
        ai.monitor_network(f"https://tracker{i}.doubleclick.net/ad.js")

    duration = time.perf_counter() - start

    rps = 10000 / duration
    print(f"\n[STRESS] {rps:.0f} req/sec")

    assert len(ai.events) > 0


def test_miniai_anomaly_trigger():
    ai = DarkelfMiniAISentinel()

    for i in range(500):
        ai.monitor_network(f"https://evil.com/{i}")

    stats = ai.get_statistics()

    print(f"\n[ANOMALY] {stats}")

    assert stats["total_events"] > 0


def test_miniai_memory():
    tracemalloc.start()

    ai = DarkelfMiniAISentinel()

    for i in range(5000):
        ai.monitor_network(f"https://example.com/{i}")

    current, peak = tracemalloc.get_traced_memory()

    tracemalloc.stop()

    print(f"\n[MEM] current={current/1024:.1f}KB peak={peak/1024:.1f}KB")

    assert peak < 50 * 1024 * 1024  # <50MB


def test_miniai_realistic_mix():
    ai = DarkelfMiniAISentinel()

    urls = [
        "https://example.com",
        "https://cdn.cloudflare.com/script.js",
        "https://ads.doubleclick.net/banner.js",
        "https://fonts.gstatic.com/font.woff2",
        "https://api.example.com/data",
    ] * 2000

    start = time.perf_counter()

    for url in urls:
        ai.monitor_network(url)

    duration = time.perf_counter() - start

    rps = len(urls) / duration

    print(f"\n[REAL] {rps:.0f} req/sec")

    assert rps > 1000
