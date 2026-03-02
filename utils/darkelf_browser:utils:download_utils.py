import os
import tempfile
import uuid
import secrets
import re

def safe_download_dir() -> str:
    """
    Per-session no-trace download directory.
    Deleted on exit and on 'Nuke'.
    """
    root = os.path.join(tempfile.gettempdir(), "darkelf_downloads")
    os.makedirs(root, exist_ok=True)
    sess = uuid.uuid4().hex
    d = os.path.join(root, sess)
    os.makedirs(d, exist_ok=True)
    return d

def randomized_filename(suggested: str) -> str:
    suggested = (suggested or "download").strip()
    suggested = re.sub(r"[^A-Za-z0-9._-]+", "_", suggested)[:120] or "download"
    base, ext = os.path.splitext(suggested)
    token = secrets.token_hex(6)
    base = (base[:60] or "download")
    ext = ext[:12]
    return f"{base}_{token}{ext}"
