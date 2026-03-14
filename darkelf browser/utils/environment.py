import os

def configure_webengine_environment():

    existing = os.environ.get("QTWEBENGINE_CHROMIUM_FLAGS", "")

    os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = existing + (
        " --disable-background-networking"
        " --disable-sync"
        " --metrics-recording-only"
        " --disable-default-apps"
        " --no-first-run"
        " --disable-features=UserAgentClientHint"
        " --disable-features=UserAgentReduction"
        " --disable-webrtc"
        " --disable-geolocation"
        " --disable-breakpad"
        " --disable-domain-reliability"
        " --disable-client-side-phishing-detection"
        " --disable-component-update"
        " --disable-extensions"
        " --disable-gpu-shader-disk-cache"
        " --disable-logging"
    )
