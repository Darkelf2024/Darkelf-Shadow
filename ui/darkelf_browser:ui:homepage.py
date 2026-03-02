from ..config.constants import DUCK_LITE_HTTPS

HOMEPAGE = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Darkelf Browser — Shadow, Private, Hardened</title>
<!-- CSP for Meta (no frame-ancestors, use spaces not semicolons!) -->
<meta http-equiv="Content-Security-Policy"
      content="default-src 'self' data: style-src 'unsafe-inline' script-src 'unsafe-inline' img-src 'self' data: form-action https://duckduckgo.com base-uri 'none' object-src 'none'">
<style>
:root {{
  --bg:#0a0b10;
  --accent:#34C759;
  --border:rgba(255,255,255,.10);
  --input-bg:#12141b;
  --input-text:#e5e7eb;
}}
* {{ box-sizing:border-box; }}
html, body {{ height:100%; }}
body {{
  margin:0;
  font-family:ui-sans-serif,system-ui,-apple-system,Segoe UI,Roboto,Helvetica,Arial;
  background:
    radial-gradient(1200px 600px at 20% -10%,rgba(4,168,200,.25),transparent 60%),
    radial-gradient(1000px 600px at 120% 10%,rgba(52,199,89,.18),transparent 60%),
    var(--bg);
  color:#eef2f6;
  display:flex;
  flex-direction:column;
  justify-content:center;
  align-items:center;
}}
.brand {{
  display:flex;
  gap:10px;
  align-items:center;
  justify-content:center;
  font-weight:700;
  font-size:2rem;
}}
.tagline {{
  font-size:.95rem;
  font-weight:700;
  letter-spacing:.18em;
  text-transform:uppercase;
  color:#cfd8e3;
  margin:6px 0 20px;
}}
.search-wrap {{
  display:flex;
  align-items:stretch;
  gap:10px;
  justify-content:center;
}}
.search-wrap input {{
  height:48px;
  padding:0 16px;
  width:min(720px,92vw);
  border-radius:12px;
  border:1px solid var(--border);
  background:var(--input-bg);
  color:var(--input-text);
  font-size:16px;
  outline:none;
}}
.search-wrap input::placeholder {{
  color:#9aa3ad;
}}
.search-wrap input:focus {{
  box-shadow:0 0 0 3px rgba(52,199,89,.30);
  border-color:transparent;
}}
.search-wrap button {{
  width:48px;
  height:48px;
  border-radius:12px;
  border:none;
  cursor:pointer;
  font-size:20px;
  display:inline-flex;
  align-items:center;
  justify-content:center;
  color:#fff;
  background:var(--accent);
}}
.search-wrap button:focus {{
  outline:2px solid #34C759;
}}
</style>
</head>
<body>
<div class="brand">
  <svg width="32" height="32" aria-hidden="true">
    <ellipse cx="16" cy="16" rx="13" ry="14"
             fill="#111b13"
             stroke="#34C759"
             stroke-width="2"/>
  </svg>
  <span style="color:#34C759">Darkelf Browser</span>
</div>
<div class="tagline">SHADOW • PRIVATE • HARDENED</div>
<form class="search-wrap"
      action="{DUCK_LITE_HTTPS}"
      method="get"
      role="search"
      aria-label="Search DuckDuckGo">

  <input type="text"
         name="q"
         placeholder="Search DuckDuckGo"
         autocomplete="off"
         aria-label="Search query">

  <button type="submit" aria-label="Search">
    <svg viewBox="0 0 24 24" width="22" height="22" aria-hidden="true">
      <path d="M10 3a7 7 0 1 1 0 14 7 7 0 0 1 0-14zm0 2a5 5 0 1 0 0 10 5 5 0 0 0 0-10zm9.707 12.293l-3.387-3.387a1 1 0 0 0-1.414 1.414l3.387 3.387a1 1 0 0 0 1.414-1.414z"/>
    </svg>
  </button>
</form>
</body>
</html>
"""
