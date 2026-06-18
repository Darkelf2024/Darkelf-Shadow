# Darkelf Shadow backend (hardened engine)
#
# This package contains everything that touches the network or the web engine:
#   - profile:     hardened, off-the-record QWebEngineProfile factory
#   - hardening:   profile-level fingerprint-defense script injection
#   - interceptor: per-request URL interception (block / HTTPS-upgrade)
#   - filters:     EasyList/uBO network + cosmetic filter engine
#   - miniai:      passive heuristic threat sentinel
#   - constants:   user-agent strings
#   - utils:       URL sanitization, download helpers
#
# The frontend (QML) must never import network logic directly; it talks to the
# engine only through the objects this package exposes.
