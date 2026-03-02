import json
from PySide6.QtCore import QUrl

def apply_easylist_cosmetics(view, easylist_engine):
    try:
        host = view.url().host().lower()
    except Exception:
        return
    if not host:
        return
    css = easylist_engine.css_for_host(host)
    if not css:
        return
    js = """
    (function() {
      try {
        const style = document.createElement('style');
        style.type = 'text/css';
        style.textContent = %s;
        (document.head || document.documentElement || document.body).appendChild(style);
      } catch(e) {}
    })();
    """ % json.dumps(css)
    view.page().runJavaScript(js)
