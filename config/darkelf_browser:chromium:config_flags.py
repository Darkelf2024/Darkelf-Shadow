import os

def set_chromium_flags():
    """
    Call once before WebEngine profile creation.

    Risky flags like --disable-web-security are COMMENTED OUT for safety.
    """
    flags = [
        "--disable-features=ServiceWorker",
        "--disable-features=WebRtcHideLocalIpsWithMdns",
        "--disable-gpu-shader-disk-cache",
        "--disable-background-networking",
        "--disable-sync",
        "--metrics-recording-only",
        "--no-first-run",
        "--force-webrtc-ip-handling-policy=disable_non_proxied_udp",
        "--webrtc-ip-handling-policy=disable_non_proxied_udp",
        "--disable-webrtc",
        "--disable-media-stream",
        "--disable-geolocation",
        "--disable-accelerated-2d-canvas",
        "--disable-software-rasterizer",
        "--disable-site-isolation-trials",
        "--disable-features=IsolateOrigins,site-per-process",
        # "--disable-web-security",   # DANGEROUS: disables same-origin checks; commented out
    ]
    flags_str = " ".join(flags)
    existing = os.environ.get("QTWEBENGINE_CHROMIUM_FLAGS", "")
    os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = f"{existing} {flags_str}".strip()
