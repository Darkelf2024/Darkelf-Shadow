import re
from PySide6.QtCore import QUrl

CLEAR_PARAMS = [
    "utm_source","utm_medium","utm_campaign","utm_term",
    "utm_content","utm_id",
    "fbclid","gclid",
    "mc_campaign","mc_eid","mc_cid",
    "pk_campaign","pk_kwd"
]

def sanitize_url_clearurls(url):

    url_parts = QUrl(url)

    query = url_parts.query()

    new_query = "&".join(
        part for part in query.split("&")
        if not any(part.startswith(p + "=") for p in CLEAR_PARAMS)
    )

    url_parts.setQuery(new_query)

    return url_parts.toString()
