from PySide6.QtCore import QUrl

def base_domain(host: str) -> str:
    """
    Returns the eTLD+1 (base domain) for a given host.
    Example: 'lite.duckduckgo.com' or 'duckduckgo.com' -> 'duckduckgo.com'
    """
    host = (host or "").split(":")[0]  # Remove port if present
    parts = host.lower().split(".")
    if len(parts) >= 2:
        return ".".join(parts[-2:])
    return host.lower()

def third_party_check(req_host: str, first_party_host: str) -> bool:
    """
    Use base domains for robust first-party check across subdomains.
    """
    if not req_host or not first_party_host:
        return True
    return base_domain(req_host) != base_domain(first_party_host)

def safe_host(u: str) -> str:
    try:
        return QUrl(u).host().lower()
    except Exception:
        return ""
