# backend/flags.py
#
# Chromium command-line flags. MUST be applied before the Qt application object
# is constructed, otherwise QtWebEngine ignores them.

import os

# Hardening flags:
#   --disable-sync                      no Google account sync
#   --disable-breakpad                  no crash dumps written to disk
#   --no-first-run                      no first-run network calls / profile churn
#   --no-pings                          drop <a ping> hyperlink auditing pings
#   --disable-background-networking     no speculative/background fetches
#   --disable-domain-reliability        no domain reliability beacons to Google
#   --disable-features=...              kill metrics/feedback/reporting subsystems
_FLAGS = (
    "--disable-sync"
    " --disable-breakpad"
    " --no-first-run"
    " --no-pings"
    " --disable-background-networking"
    " --disable-domain-reliability"
    " --disable-features=Translate,OptimizationHints,MediaRouter,"
    "AutofillServerCommunication,InterestFeedContentSuggestions,"
    "ReportingApiEnabled"
)


def apply_chromium_flags():
    # Always overwrite (no accumulation across runs).
    flags = _FLAGS
    # CI / headless runners need extra flags (e.g. --no-sandbox --disable-gpu).
    # These are opt-in via env so normal runs stay fully sandboxed.
    extra = os.environ.get("DARKELF_EXTRA_CHROMIUM_FLAGS", "").strip()
    if extra:
        flags = flags + " " + extra
    os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = flags
