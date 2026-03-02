import os

# EasyList URLs: privacy, social, annoyances, adblock, unbreak, badware, tracking
EASYLIST_URLS = [
    "https://easylist.to/easylist/easylist.txt",
    "https://easylist.to/easylist/easyprivacy.txt",
    "https://secure.fanboy.co.nz/fanboy-annoyance.txt",
    "https://easylist.to/easylist/fanboy-social.txt",
    "https://easylist-downloads.adblockplus.org/antiadblockfilters.txt",
    "https://filters.adtidy.org/extension/chromium/filters/3.txt",
    "https://raw.githubusercontent.com/uBlockOrigin/uAssets/master/filters/privacy.txt",
    "https://raw.githubusercontent.com/uBlockOrigin/uAssets/master/filters/unbreak.txt",
    "https://raw.githubusercontent.com/uBlockOrigin/uAssets/master/filters/badware.txt",
]

# User-level cache directory for filters
EASYLIST_CACHE_DIR = os.path.join(os.path.expanduser("~"), ".darkelf", "filterlists")
os.makedirs(EASYLIST_CACHE_DIR, exist_ok=True)

# 24 hours between refreshes
EASYLIST_REFRESH_EVERY = 24 * 60 * 60  # seconds
