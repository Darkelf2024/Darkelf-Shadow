import gc
import json
import os
import re
import secrets
import shutil
import sys
import time
from urllib.parse import quote_plus

from PySide6.QtCore import Qt, QSize, QTimer, QUrl
from PySide6.QtGui import QAction, QColor, QIcon, QPainter, QPalette, QPen, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QGridLayout,
    QHBoxLayout,
    QLineEdit,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QTabWidget,
    QToolBar,
    QToolButton,
    QVBoxLayout,
    QWidget,
    QWidgetAction,
)
from PySide6.QtWebEngineCore import QWebEnginePage, QWebEngineProfile, QWebEngineSettings
from PySide6.QtWebEngineWidgets import QWebEngineView

from adblock.easylist_engine import EASYLIST_URLS, EasyListEngine
from browser.downloads import DownloadShelf, randomized_filename, safe_download_dir
from browser.hardened_page import HardenedWebPage
from browser.interceptor import StealthInterceptor
from browser.youtube_adblock import install_darkelf_youtube_adblock
from security.miniai import DarkelfMiniAISentinel
from ui.icons import (
    make_fullscreen_icon,
    make_house_icon,
    make_icon,
    make_java_icon,
    make_nav_arrow_icon,
    make_nuke_icon,
    make_reload_icon,
    make_shield_icon,
    make_zoom_icon,
)
from utils.url_utils import sanitize_url_clearurls

BOOTUP_CANVAS_SEED = secrets.randbits(32) & 0xFFFFFFFF
DUCK_LITE_HTTPS = "https://duckduckgo.com/lite/"
MUTE_LOGS_AFTER_BOOT_MS = 0


HOMEPAGE = """ <!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Darkelf Browser</title>
<meta name="referrer" content="no-referrer">

<meta http-equiv="Content-Security-Policy"
content="
default-src 'self' data:;
style-src 'unsafe-inline';
script-src 'unsafe-inline';
img-src data:;
base-uri 'none';
object-src 'none';
frame-src 'none';
">

<style>
:root{
  --bg:#0a0b10;
  --accent:ACCENT_COLOR;
  --text:#eef2f6;
  --muted:#d7dee8;
}

*{ box-sizing:border-box; }

html,body{
  height:100%;
  margin:0;
  overflow:hidden;
}

body{
  font-family:
    ui-sans-serif,
    system-ui,
    -apple-system,
    Segoe UI,
    Roboto,
    Helvetica,
    Arial;

background:
radial-gradient(1200px 600px at 20% -10%, color-mix(in srgb, var(--accent) 35%, transparent), transparent 60%),
radial-gradient(1000px 600px at 120% 10%, color-mix(in srgb, var(--accent) 45%, transparent), transparent 60%),
var(--bg);

  display:flex;
  flex-direction:column;
  justify-content:center;
  align-items:center;
  color:var(--text);

  opacity:0;
  animation:bootFade 1.15s ease forwards;
}

@keyframes bootFade{
  from{ opacity:0; transform:scale(.985); }
  to{ opacity:1; transform:scale(1); }
}

.particles{
  position:fixed;
  inset:0;
  pointer-events:none;
  background-image:radial-gradient(color-mix(in srgb, var(--accent) 70%, transparent) 1px, transparent 1px);
  background-size:86px 86px;
  opacity:.18;
  animation:particleMove 60s linear infinite;
}

@keyframes particleMove{
  from{ transform:translateY(0); }
  to{ transform:translateY(-200px); }
}

.brand{
  display:flex;
  align-items:center;
  gap:14px;
  font-weight:800;
  font-size:3.75rem;
  line-height:1;
  animation:brandRise 1s ease forwards;
}

@keyframes brandRise{
  from{
    opacity:0;
    transform:translateY(34px);
  }
  to{
    opacity:1;
    transform:translateY(0);
  }
}

.brand svg{
  width:42px;
  height:42px;
  flex:0 0 auto;
  stroke:var(--accent);
  stroke-width:2;
  margin-top:4px;
  filter:
    drop-shadow(0 0 8px color-mix(in srgb, var(--accent) 75%, transparent))
    drop-shadow(0 0 18px color-mix(in srgb, var(--accent) 45%, transparent));
  animation:circlePulse 3s ease-in-out infinite;
}

@keyframes circlePulse{
  0%{
    transform:scale(1);
    filter:
      drop-shadow(0 0 7px color-mix(in srgb, var(--accent) 70%, transparent))
      drop-shadow(0 0 16px color-mix(in srgb, var(--accent) 40%, transparent));
  }
  50%{
    transform:scale(1.03);
    filter:
      drop-shadow(0 0 12px color-mix(in srgb, var(--accent) 90%, transparent))
      drop-shadow(0 0 26px color-mix(in srgb, var(--accent) 60%, transparent));
  }
  100%{
    transform:scale(1);
    filter:
      drop-shadow(0 0 7px color-mix(in srgb, var(--accent) 70%, transparent))
      drop-shadow(0 0 16px color-mix(in srgb, var(--accent) 40%, transparent));
  }
}

.brand span{
  color:var(--accent);
  letter-spacing:-.02em;
  text-shadow:
    0 0 10px color-mix(in srgb, var(--accent) 85%, transparent),
    0 0 24px color-mix(in srgb, var(--accent) 50%, transparent),
    0 0 44px color-mix(in srgb, var(--accent) 30%, transparent);
  animation:titlePulse 3s ease-in-out infinite;
}

@keyframes titlePulse{
  0%{
    text-shadow:
      0 0 10px color-mix(in srgb, var(--accent) 85%, transparent),
      0 0 24px color-mix(in srgb, var(--accent) 50%, transparent),
      0 0 44px color-mix(in srgb, var(--accent) 30%, transparent);
  }
  50%{
    text-shadow:
      0 0 16px color-mix(in srgb, var(--accent) 100%, transparent),
      0 0 34px color-mix(in srgb, var(--accent) 65%, transparent),
      0 0 58px color-mix(in srgb, var(--accent) 38%, transparent);
  }
  100%{
    text-shadow:
      0 0 10px color-mix(in srgb, var(--accent) 85%, transparent),
      0 0 24px color-mix(in srgb, var(--accent) 50%, transparent),
      0 0 44px color-mix(in srgb, var(--accent) 30%, transparent);
  }
}

.tagline{
margin-top:18px;
font-size:1.1rem;
letter-spacing:.25em;
text-transform:uppercase;
color:#cfd8e3;

text-align:center;
width:100%;
}

@keyframes taglineFade{
  0%{ opacity:0; transform:translateY(8px); }
  100%{ opacity:1; transform:translateY(0); }
}

.ai-status{
  position:absolute;
  bottom:42px;
  font-size:.95rem;
  font-weight:700;
  letter-spacing:.28em;
  color:var(--accent);
  opacity:.78;
  text-shadow:
    0 0 8px color-mix(in srgb, var(--accent) 85%, transparent),
    0 0 18px color-mix(in srgb, var(--accent) 35%, transparent);
  animation:miniPulse 3s ease-in-out infinite;
}

@keyframes miniPulse{
  0%{
    opacity:.68;
    text-shadow:
      0 0 8px color-mix(in srgb, var(--accent) 85%, transparent),
      0 0 18px color-mix(in srgb, var(--accent) 35%, transparent);
  }
  50%{
    opacity:.95;
    text-shadow:
      0 0 12px color-mix(in srgb, var(--accent) 100%, transparent),
      0 0 26px color-mix(in srgb, var(--accent) 50%, transparent);
  }
  100%{
    opacity:.68;
    text-shadow:
      0 0 8px color-mix(in srgb, var(--accent) 85%, transparent),
      0 0 18px color-mix(in srgb, var(--accent) 35%, transparent);
  }
}
</style>
</head>

<body>
  <div class="particles"></div>

  <div class="brand">
    <svg viewBox="0 0 32 32" fill="none" aria-hidden="true">
      <ellipse cx="16" cy="16" rx="13" ry="14"/>
    </svg>
    <span>Darkelf Browser</span>
  </div>

  <div class="tagline">
    Shadow • Private • Hardened
  </div>

  <div class="ai-status">
    Darkelf MiniAI Sentinel
  </div>
</body>
</html>
"""


def create_color_palette_menu(parent, callback):
    menu = QMenu(parent)

    palette = QWidget(menu)
    grid = QGridLayout(palette)
    grid.setSpacing(2)
    grid.setContentsMargins(4, 4, 4, 4)

    colors = [
        "#34C759",
        "#444444", "#666666", "#999999",
        "#ff4d4f", "#ff7a45", "#ffa940",
        "#ffd666", "#73d13d", "#36cfc9", "#40a9ff",
        "#597ef7", "#9254de", "#f759ab", "#bfbfbf",
        "#FFFFFF",
        "#FFC0CB",
        "#00BFA6",
        "#FF6F61",
        "#8BC34A",
        "#FFB6C1",
        "#FFD700",
        "#7B68EE",
        "#20B2AA",
    ]

    row = 0
    col = 0

    for color_hex in colors:
        btn = QPushButton()
        btn.setFixedSize(20, 20)
        btn.setStyleSheet(
            f"""
            QPushButton {{
                background:{color_hex};
                border:1px solid #555;
            }}
            QPushButton:hover {{
                border:2px solid white;
            }}
            """
        )
        btn.clicked.connect(lambda _, c=color_hex: callback(QColor(c)))
        grid.addWidget(btn, row, col)

        col += 1
        if col == 8:
            col = 0
            row += 1

    action = QWidgetAction(menu)
    action.setDefaultWidget(palette)
    menu.addAction(action)
    return menu


# ------------------------------------------------
# Main browser class
# ------------------------------------------------
class DarkelfBrowser(QMainWindow):
    def __init__(self, profile):
        super().__init__()
                
        self.accent_color = "#34C759"

        self.toolbar = self._make_toolbar()

        self.setWindowTitle("")
        self.resize(1200, 800)

        self.shared_profile = profile
        
        install_darkelf_youtube_adblock(profile)
        
        print("OffTheRecord:", self.shared_profile.isOffTheRecord())

        self.easy = EasyListEngine()
        self.easy.load_and_build(EASYLIST_URLS)

        print("Loaded network rules:", len(self.easy.network_rules))

        self.mini_ai = DarkelfMiniAISentinel()
        
        self.mini_ai.ui = self

        self.interceptor = StealthInterceptor(
            self.easy,
            self.mini_ai
        )
        self.shared_profile._darkelf_interceptor = self.interceptor
        self.shared_profile.setUrlRequestInterceptor(self.interceptor)

        # -----------------------------
        # Create UI
        # -----------------------------
        self.tabs = QTabWidget()

        # enable close buttons
        self.tabs.setTabsClosable(True)
        self.tabs.setMovable(True)

        # connect close signal
        self.tabs.tabCloseRequested.connect(self.close_tab)

        # ensure tabbar supports close buttons
        tabbar = self.tabs.tabBar()
        tabbar.setTabsClosable(True)

        # -----------------------------
        # Download shelf
        # -----------------------------
        self.download_shelf = DownloadShelf()
        self.download_shelf.hide()

        self.tabs_layout = QVBoxLayout()
        self.tabs_layout.addWidget(self.tabs)
        self.tabs_layout.addWidget(self.download_shelf)

        container = QWidget()
        container.setLayout(self.tabs_layout)

        # ONLY CALL setCentralWidget ONCE
        self.setCentralWidget(container)

        # -----------------------------
        # Apply tab styling
        # -----------------------------
        self._set_tab_style()
        
        self.set_accent_color(QColor(self.accent_color))

        # -----------------------------
        # Toolbar
        # -----------------------------
        self.toolbar = self._make_toolbar()
        self.addToolBar(Qt.TopToolBarArea, self.toolbar)

        # -----------------------------
        # Startup tab
        # -----------------------------
        QApplication.instance().aboutToQuit.connect(self._cleanup_webengine)
        self._add_tab(home=True)

        # -----------------------------
        # Downloads
        # -----------------------------
        self._download_dir = _safe_download_dir()
        self._downloaded_files: list[str] = []
        self._hook_secure_downloads()

        QApplication.instance().aboutToQuit.connect(self._wipe_download_traces)

        # -----------------------------
        # Hotkeys
        # -----------------------------
        self.setup_hotkeys()
        
        #----------------------------
        # Timer For Darkelf MiniAI
        #----------------------------
        self.miniai_timer = QTimer()
        self.miniai_timer.timeout.connect(self.update_miniai_icon)
        self.miniai_timer.start(1500)
        # -----------------------------
        # Memory cleanup timers
        # -----------------------------
        self.cleanup_timer = QTimer(self)
        self.cleanup_timer.setSingleShot(True)
        self.cleanup_timer.timeout.connect(self.memory_cleanup)

        self.maintenance_timer = QTimer(self)
        self.maintenance_timer.timeout.connect(self.memory_cleanup)
        self.maintenance_timer.start(300000)

        self.renderer_cleanup_timer = QTimer(self)
        self.renderer_cleanup_timer.timeout.connect(self.release_renderer_memory)
        self.renderer_cleanup_timer.start(600000)

    def release_renderer_memory(self):
        try:
            for i in range(self.tabs.count()):
                view = self.tabs.widget(i)

                if not view:
                    continue

                page = view.page()

                if not page:
                    continue

                if i != self.tabs.currentIndex():  # skip active tab
                    page.triggerAction(QWebEnginePage.Stop)
                    page.setLifecycleState(QWebEnginePage.LifecycleState.Discarded)

        except Exception as e:
            print("[Darkelf] Renderer cleanup error:", e)

    def new_tab(self):
        self._add_tab(home=True)
        self.debounce_cleanup()

        
    def close_tab(self):
        if i >= 0:
            self.tabs.removeTab(i)
            self.debounce_cleanup()
            
    def reload_page(self):
        view = self.tabs.currentWidget()
        if view:
            view.reload()
        
    def on_url_entered(self):
        text = self.addr.text().strip()
        if not text:
            self._add_tab(home=True)
            return
        has_scheme = re.match(r'^[a-zA-Z][a-zA-Z0-9+.-]*://', text) is not None
        looks_like_domain = re.match(r'^[\w.-]+\.[A-Za-z]{2,}(/|$)', text) is not None
        looks_like_ip_or_local = re.match(r'^(localhost|(?:\d{1,3}\.){3}\d{1,3})(:\d+)?(/|$)?$', text) is not None
        if has_scheme:
            url = text
        elif looks_like_domain or looks_like_ip_or_local:
            url = "https://" + text
        else:
            base = DUCK_LITE_HTTPS
            url = base + "?q=" + quote_plus(text)

        # SANIIZE HERE!
        url = sanitize_url_clearurls(url)

        self._add_tab(url=url)
        
    def debounce_cleanup(self, delay=5000):
        # Restart timer every time
        self.cleanup_timer.start(delay)
        
    def memory_cleanup(self):
        try:
            gc.collect()
            print("[Darkelf] GC complete")

        except Exception as e:
            print("[Darkelf] Cleanup error:", e)
                    
    def update_miniai_icon(self):

        if self.mini_ai.panic_mode_active:
            color = "#8B0000"  # panic

        elif self.mini_ai.lockdown_active:
            color = "#ff0033"  # lockdown

        else:
            color = self.accent_color  # normal

        self.miniai_action.setIcon(make_shield_icon(color, 18))

    def make_outline_lock_icon(self, color="#ffffff", size=16):
        pix = QPixmap(size, size)
        pix.fill(Qt.transparent)

        painter = QPainter(pix)
        painter.setRenderHint(QPainter.Antialiasing)

        pen = QPen(QColor(color))
        pen.setWidth(2)
        painter.setPen(pen)

        # Lock body
        painter.drawRoundedRect(4, 7, 8, 7, 2, 2)

        # Lock shackle
        painter.drawArc(4, 2, 8, 10, 0 * 16, 180 * 16)

        painter.end()
        return QIcon(pix)
        
    def _make_toolbar(self):

        tb = QToolBar()
        tb.setMovable(False)
        tb.setIconSize(QSize(22, 22))

        c = self.accent_color

        self.back_action = QAction(make_nav_arrow_icon("left", c, 22), "Back", self)
        self.fwd_action = QAction(make_nav_arrow_icon("right", c, 22), "Forward", self)
        self.reload_action = QAction(make_reload_icon(c, 22), "Reload", self)
        self.home_action = QAction(make_house_icon(c, 22), "Home", self)
        self.zoom_in_action = QAction(make_zoom_icon("+", c, 20), "Zoom In", self)
        self.zoom_out_action = QAction(make_zoom_icon("-", c, 20), "Zoom Out", self)
        self.full_action = QAction(make_fullscreen_icon(c, 20), "Full Screen", self)


        self.java_action = QAction(make_java_icon(self.accent_color, 18), "JavaScript", self)
        self.miniai_action = QAction(
            make_shield_icon(self.accent_color, 18),
            "MiniAI Monitor",
            self
            )
        self.miniai_action.triggered.connect(self.show_miniai_status)

        self.nuke_action = QAction(make_nuke_icon("#ff2a2a", 18), "Nuke", self)

        self.addtab_action = QAction(make_icon(c, 20), "New Tab", self)

        self.nuke_action.triggered.connect(self.nuke_all_data)

        self.back_action.triggered.connect(self.go_back)
        self.fwd_action.triggered.connect(self.go_fwd)
        self.reload_action.triggered.connect(self.reload)
        self.home_action.triggered.connect(self.go_home)
        self.zoom_in_action.triggered.connect(self.zoom_in)
        self.zoom_out_action.triggered.connect(self.zoom_out)
        self.full_action.triggered.connect(self.toggle_fullscreen)
        self.addtab_action.triggered.connect(lambda: self._add_tab(home=True))

        tb.addAction(self.back_action)
        tb.addAction(self.fwd_action)
        tb.addAction(self.reload_action)
        tb.addAction(self.home_action)
        tb.addSeparator()

        self.addr = QLineEdit()
        self.addr.setPlaceholderText("Search or enter URL")
        self.addr.returnPressed.connect(self.on_url_entered)
        tb.addWidget(self.addr)
        tb.addSeparator()
        
        # ADD LOCK ICON HERE
        self.lock_action = self.addr.addAction(
            self.make_outline_lock_icon("#ffffff", 16),
            QLineEdit.LeadingPosition
        )
        self.lock_action.setVisible(False)
        
        self.addr.setStyleSheet(f"""
        QLineEdit {{
            background-color: #12141b;
            color: #eafaf0;
            border: 1px solid {self.accent_color};
            border-radius: 6px;
            padding: 4px 8px;
            selection-background-color: {self.accent_color};
            selection-color: #0a0b10;
        }}
        """)


        tb.addAction(self.zoom_out_action)
        tb.addAction(self.zoom_in_action)
        tb.addAction(self.full_action)
        tb.addAction(self.addtab_action)
        
        # ---- Accent color picker ----

        self.color_btn = QToolButton()
        self.color_btn.setText("◈")  # cyber style icon
        self.color_btn.setFixedSize(28, 24)

        self.color_btn.setStyleSheet(f"""
        QToolButton {{
            background: transparent;
            color: {self.accent_color};
            border: none;
            font-size: 16px;
        }}

        QToolButton:hover {{
            color: white;
        }}
        """)

        self.color_btn.setMenu(
            create_color_palette_menu(self, self.set_accent_color)
        )

        self.color_btn.setPopupMode(QToolButton.InstantPopup)


        tb.addWidget(self.color_btn)


        tb.addSeparator()

        self.java_action.setCheckable(True)
        self.java_action.setChecked(True)
        self.java_action.setToolTip("Enable/Disable JavaScript globally")
        tb.addAction(self.java_action)
        
        tb.addAction(self.miniai_action)

        tb.addAction(self.nuke_action)
        
        def update_js_icon():
            enabled = self.java_action.isChecked()
            color = "#f89820" if enabled else "#bbbbbb"
            self.java_action.setIcon(make_java_icon(color, 18))
            self.java_action.setText("JavaScript" if enabled else "JS Off")
            self.toggle_javascript()
        self.java_action.triggered.connect(update_js_icon)

        tb.addSeparator()
        return tb
        
    def show_miniai_status(self):

        html = self._build_threat_report_html()

        win = QDialog(self)
        win.setWindowTitle("Darkelf MiniAI Threat Console")
        win.resize(900,600)

        layout = QVBoxLayout(win)

        view = QWebEngineView()
        view.setHtml(html)

        layout.addWidget(view)

        win.exec_()

    def _build_threat_report_html(self):

        stats = self.mini_ai.get_statistics()
        
        recent_upgrades = [
            e for e in self.mini_ai.events
            if "HTTP_AUTO_UPGRADE" in e.get("threats", [])
        ][-5:]

        return f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
    <meta charset="UTF-8"/>
    <meta name="viewport" content="width=device-width, initial-scale=1.0"/>

    <meta http-equiv="Content-Security-Policy"
    content="
    default-src 'none';
    style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net;
    font-src https://cdn.jsdelivr.net;
    img-src 'self' data:;
    connect-src 'none';
    script-src 'none';
    object-src 'none';
    frame-ancestors 'none';
    base-uri 'none';
    form-action 'none';
    ">

    <title>Darkelf Threat Console</title>

    <link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.css" rel="stylesheet">

    <style>

    :root {{
    --bg:#05060a;
    --accent:#36ff9a;
    --accent2:#00eaff;
    --accent3:#b400ff;
    --danger:#ff3b30;
    --warn:#ffd36b;
    --muted:#9db0be;
    --card:rgba(255,255,255,.05);
    }}

    *{{box-sizing:border-box}}
    html,body{{margin:0;height:100%;font-family:ui-sans-serif,system-ui,-apple-system;}}

    body{{
    background:
    radial-gradient(1200px 800px at 15% -10%, rgba(0,234,255,.35), transparent 70%),
    radial-gradient(900px 600px at 110% 0%, rgba(54,255,154,.35), transparent 70%),
    radial-gradient(1200px 700px at 50% 120%, rgba(180,0,255,.35), transparent 70%),
    var(--bg);
    color:#eef2f6;
    }}

    body::before {{
    content:"";
    position:fixed;
    inset:0;
    background:
    linear-gradient(rgba(0,255,180,.05) 1px, transparent 1px),
    linear-gradient(90deg, rgba(0,255,180,.05) 1px, transparent 1px);
    background-size:40px 40px;
    pointer-events:none;
    opacity:.3;
    }}

    .scanline {{
    position:fixed;
    top:0;
    left:0;
    width:100%;
    height:2px;
    background:linear-gradient(90deg,transparent,var(--accent2),transparent);
    animation:scan 5s linear infinite;
    opacity:.5;
    }}

    @keyframes scan {{
    0%{{transform:translateY(-20px)}}
    100%{{transform:translateY(100vh)}}
    }}

    .container {{
    max-width:1100px;
    margin:auto;
    padding:90px 24px;
    }}

    .title {{
    font-size:1.8rem;
    font-weight:900;
    letter-spacing:.15em;
    background:linear-gradient(90deg,var(--accent),var(--accent2),var(--accent3));
    -webkit-background-clip:text;
    -webkit-text-fill-color:transparent;
    }}

    .status-lights {{
    margin-top:18px;
    display:flex;
    gap:10px;
    }}

    .light {{
    width:10px;
    height:10px;
    border-radius:50%;
    }}

    .green {{background:#36ff9a;box-shadow:0 0 10px #36ff9a}}
    .cyan {{background:#00eaff;box-shadow:0 0 10px #00eaff}}
    .purple {{background:#b400ff;box-shadow:0 0 10px #b400ff}}

    .badge {{
    display:inline-flex;
    align-items:center;
    gap:10px;
    margin-top:20px;
    padding:8px 16px;
    border-radius:999px;
    font-size:.7rem;
    font-weight:800;
    letter-spacing:.15em;
    background:{"#ff3b30" if stats['lockdown']['active'] else "#36ff9a"};
    color:#000;
    }}

    .badge::before {{
    content:"";
    width:8px;
    height:8px;
    border-radius:50%;
    background:#fff;
    animation:pulse 1.5s infinite;
    }}

    @keyframes pulse {{
    0%{{transform:scale(.7);opacity:.6}}
    50%{{transform:scale(1.4);opacity:1}}
    100%{{transform:scale(.7);opacity:.6}}
    }}

    .cards {{
    margin-top:60px;
    display:grid;
    grid-template-columns:1fr 1fr;
    gap:50px;
    }}

    .card {{
    background:var(--card);
    backdrop-filter:blur(20px);
    padding:40px;
    border-radius:18px;
    border:1px solid rgba(255,255,255,.08);
    box-shadow:0 30px 60px rgba(0,0,0,.6),0 0 40px rgba(0,234,255,.15);
    }}

    .section-title {{
    font-size:.75rem;
    letter-spacing:.25em;
    text-transform:uppercase;
    color:var(--muted);
    margin-bottom:24px;
    }}

    .line {{
    display:grid;
    grid-template-columns:28px auto max-content;
    align-items:center;
    column-gap:14px;
    margin:16px 0;
    }}

    .icon {{
    font-size:1.2rem;
    color:var(--accent2);
    }}

    .stat-label {{color:#c3d2dd}}

    .stat-value {{
    font-weight:900;
    font-size:1.15rem;
    }}

    .footer {{
    margin-top:80px;
    text-align:center;
    font-size:.8rem;
    color:var(--muted);
    opacity:.7;
    }}

    </style>
    </head>

    <body>

    <div class="scanline"></div>
    
    <div class="container">

    <div class="title">Darkelf MiniAI Threat Console</div>

    <div class="status-lights">
    <div class="light green"></div>
    <div class="light cyan"></div>
    <div class="light purple"></div>
    </div>

    <div class="badge">
    {"LOCKDOWN ACTIVE" if stats['lockdown']['active'] else "SYSTEM MONITORING"}
    </div>

    <div class="cards">

    <div class="card">
    <div class="section-title">Session Metrics</div>

    <div class="line"><i class="bi bi-clock-history icon"></i><span class="stat-label">Session Uptime</span><span class="stat-value">{stats['uptime_seconds']:.1f}s</span></div>
    <div class="line"><i class="bi bi-activity icon"></i><span class="stat-label">Total Events</span><span class="stat-value">{stats['total_events']}</span></div>
    <div class="line"><i class="bi bi-globe2 icon"></i><span class="stat-label">Unique Domains</span><span class="stat-value">{stats['unique_domains']}</span></div>

    <div class="line">
    <i class="bi bi-shield-exclamation icon"></i>
    <span class="stat-label">Threat Score</span>
    <span class="stat-value">{stats['threat_score']}</span>
    </div>

    </div>

    <div class="card">
    <div class="section-title">Threat Analysis</div>

    <div class="line"><i class="bi bi-crosshair icon"></i><span class="stat-label">Trackers</span><span class="stat-value">{stats['threats']['trackers']}</span></div>
    <div class="line"><i class="bi bi-bullseye icon"></i><span class="stat-label">Intrusions</span><span class="stat-value">{stats['threats']['intrusions']}</span></div>
    <div class="line"><i class="bi bi-bug-fill icon"></i><span class="stat-label">Malware</span><span class="stat-value">{stats['threats']['malware']}</span></div>
    <div class="line"><i class="bi bi-lightning-charge-fill icon"></i><span class="stat-label">Exploits</span><span class="stat-value">{stats['threats']['exploits']}</span></div>
    <div class="line"><i class="bi bi-fingerprint icon"></i><span class="stat-label">Fingerprinting</span><span class="stat-value">{stats['threats']['fingerprinting']}</span></div>
    <div class="line"><i class="bi bi-arrow-left-right icon"></i><span class="stat-label">HTTP Blocks</span><span class="stat-value">{stats['threats']['http_blocks']}</span></div>

    </div>

    </div>

    <div class="footer">
    Darkelf Browser • MiniAI Sentinel • Hardened Runtime
    </div>

    </div>
    </body>
    </html>
    """

    def set_accent_color(self, color):

        self.accent_color = color.name()
        c = self.accent_color

        # update Qt highlight palette (text selection, menus, etc.)
        app = QApplication.instance()
        palette = app.palette()
        palette.setColor(QPalette.Highlight, QColor(c))
        palette.setColor(QPalette.HighlightedText, QColor("#0a0b10"))
        palette.setColor(QPalette.Link, QColor(c))
        palette.setColor(QPalette.LinkVisited, QColor(c))
        app.setPalette(palette)

        # update toolbar icons
        self.back_action.setIcon(make_nav_arrow_icon("left", c, 22))
        self.fwd_action.setIcon(make_nav_arrow_icon("right", c, 22))
        self.reload_action.setIcon(make_reload_icon(c, 22))
        self.home_action.setIcon(make_house_icon(c, 22))
        self.zoom_in_action.setIcon(make_zoom_icon("+", c, 20))
        self.zoom_out_action.setIcon(make_zoom_icon("-", c, 20))
        self.full_action.setIcon(make_fullscreen_icon(c, 20))
        self.addtab_action.setIcon(make_icon(c, 20))
        self.java_action.setIcon(make_java_icon(c, 18))
        self.miniai_action.setIcon(make_shield_icon(c, 18))
        
        self.addr.setStyleSheet(f"""
        QLineEdit {{
            background-color: #12141b;
            color: #eafaf0;
            border: 1px solid {c};
            border-radius: 6px;
            padding: 4px 8px;
            selection-background-color: {c};
            selection-color: #0a0b10;
        }}
        """)

        # update diamond palette button
        self.color_btn.setStyleSheet(f"""
        QToolButton {{
            background: transparent;
            color: {c};
            border: none;
            font-size: 16px;
        }}

        QToolButton:hover {{
            color: white;
        }}
        """)

        # update application stylesheet
        QApplication.instance().setStyleSheet(f"""
            QMainWindow {{
                background-color: #0b0f14;
            }}

            QWidget {{
                background-color: #0b0f14;
                color: white;
            }}

            QLineEdit {{
                background-color: #111;
                color: white;
                border: 1px solid #444;
                border-radius: 6px;
                padding: 4px;
            }}

            QLineEdit:focus {{
                border: 1px solid {c};
            }}

            QToolBar {{
                background-color: #0b0f14;
                border-bottom: 1px solid #222;
            }}

            QPushButton {{
                background-color: #111;
                color: white;
                border: 1px solid #444;
                border-radius: 4px;
            }}

            QPushButton:hover {{
                border: 1px solid {c};
            }}

            QPushButton#accent {{
                background-color: {c};
                color: black;
                border: none;
            }}

            QLabel#accentText {{
                color: {c};
                font-weight: bold;
            }}

            QTabBar::tab:selected {{
                border-bottom: 2px solid {c};
            }}

            /* -------- FIX CONTEXT MENUS -------- */

            QMenu {{
                background-color: #0b0f14;
                border: 1px solid #222;
                padding: 4px;
            }}

            QMenu::item {{
                color: #eafaf0;
                padding: 6px 18px;
                background: transparent;
            }}

            QMenu::item:selected {{
                background: {c};
                color: #0a0b10;
                border-radius: 4px;
            }}

            QMenu::separator {{
                height: 1px;
                background: #222;
                margin: 4px 6px;
            }}
        """)

        self._set_tab_style()

        for i in range(self.tabs.count()):
            view = self.tabs.widget(i)

            js = f"""
            document.documentElement.style.setProperty('--accent', '{self.accent_color}');
            """

            try:
                view.page().runJavaScript(js)
            except:
                pass


    def _configure_tabbar_small(self):
        bar = self.tabs.tabBar()
        bar.setExpanding(False)
        bar.setMovable(True)
        bar.setElideMode(Qt.TextElideMode.ElideRight)
        bar.setIconSize(QSize(16, 16))
        bar.setUsesScrollButtons(True)
        bar.setStyleSheet("""
            QTabBar::tab { height: 22px; padding: 2px 8px; max-width: 140px; }
        """)

    def _set_tab_style(self):

        if not hasattr(self, "tabs"):
            return

        c = self.accent_color

        self.tabs.setStyleSheet(f"""
        QTabWidget::pane {{
            border: 0;
        }}

        QTabBar::tab {{
            background: #333;
            color: #fff;
            padding: 5px 10px;
            border-radius: 10px;
            margin: 2px;
        }}

        QTabBar::tab:selected,
        QTabBar::tab:hover {{
            background: {c};
            color: #000;
        }}

        QTabBar::close-button {{
            image: url(:/qt-project.org/styles/commonstyle/images/standardbutton-close-16.png);
            background: transparent;
            border: none;
        }}

        QTabBar::close-button:hover {{
            background: transparent;
        }}
        """)

    @staticmethod
    def _short_label_from_qurl(qurl):
        try:
            host = qurl.host().lower() if hasattr(qurl, "host") else ""
        except Exception:
            host = ""
        if not host:
            return "Home"
        aliases = {
            "youtube.com": "YouTube", "www.youtube.com": "YouTube", "youtu.be": "YouTube",
            "bbc.com": "BBC", "www.bbc.com": "BBC", "bbc.co.uk": "BBC", "www.bbc.co.uk": "BBC",
            "github.com": "GitHub",
            "twitter.com": "Twitter", "x.com": "Twitter",
            "reddit.com": "Reddit", "www.reddit.com": "Reddit",
            "duckduckgo.com": "DuckDuckGo",
        }
        if host in aliases:
            return aliases[host]
        if host.startswith("www."):
            host = host[4:]
        parts = host.split(".")
        base = parts[-2] if len(parts) >= 2 else host
        return base.capitalize()
        
    def _add_tab(self, url=None, home=False):
        profile = self.shared_profile
        tab_seed = secrets.randbits(32) & 0xFFFFFFFF
        canvas_seed = tab_seed ^ BOOTUP_CANVAS_SEED

        view = QWebEngineView(self)
        view._profile = profile
        
        page = HardenedWebPage(view, profile, canvas_seed=canvas_seed)
        view.setPage(page)
        page.fullScreenRequested.connect(self.handle_fullscreen)
        
        # ---- EasyList Cosmetic Injection ----
        def apply_easylist_cosmetics(v=view):
            try:
                host = v.url().host().lower()
            except Exception:
                return

            if not host:
                return

            css = self.easy.css_for_host(host)
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

            v.page().runJavaScript(js)
    
        # Inject once after page load
        view.loadFinished.connect(
            lambda ok, v=view: apply_easylist_cosmetics(v) if ok else None
        )

        idx = self.tabs.addTab(view, "New Tab")
        self.tabs.setCurrentIndex(idx)

        view.urlChanged.connect(self._sync_urlbar)

        def relabel_from_url(qurl, view=view):
            i = self.tabs.indexOf(view)
            if i != -1:
                self.tabs.setTabText(i, self._short_label_from_qurl(qurl))
        view.urlChanged.connect(relabel_from_url)

        def set_icon(icon, view=view):
            i = self.tabs.indexOf(view)
            if i != -1:
                self.tabs.setTabIcon(i, icon)
        view.iconChanged.connect(set_icon)

        if home:
            html = HOMEPAGE.replace("ACCENT_COLOR", self.accent_color)
            view.setHtml(html)
            view._is_homepage = True

        elif url and url.startswith("view-source:"):
            real_url = url.replace("view-source:", "")
            view.load(QUrl(real_url))
            view.page().toHtml(lambda html: self._show_source_tab(html))

        else:
            view.load(QUrl(url or "https://duckduckgo.com/lite/"))
            
            # ---- Accent Color Injection ----
        def apply_accent(v):
            js = f"""
            try {{
                document.documentElement.style.setProperty('--accent', '{self.accent_color}');
            }} catch(e) {{}}
            """
            v.page().runJavaScript(js)

        view.loadFinished.connect(lambda ok, v=view: apply_accent(v) if ok else None)

    def _show_source_tab(self, html):
        view = QWebEngineView(self)
        view.setHtml(f"<pre style='white-space:pre-wrap;font-family:monospace'>{html.replace('<','&lt;')}</pre>")
        idx = self.tabs.addTab(view, "Source")
        self.tabs.setCurrentIndex(idx)

    def close_tab(self, idx):
        w = self.tabs.widget(idx)

        self.tabs.removeTab(idx)

        if isinstance(w, QWebEngineView):
            try:
                w.page().runJavaScript(
                    "document.querySelectorAll('video,audio').forEach(m=>{try{m.pause(); m.src='';}catch(e){}})"
                )
            except Exception:
                pass

            try:
                w.page().triggerAction(QWebEnginePage.Stop)
                w.page().setAudioMuted(True)
                w.setUrl(QUrl("about:blank"))
            except Exception:
                pass

            w.page().deleteLater()
            w.deleteLater()

        # reopen homepage if all tabs closed
        if self.tabs.count() == 0:
            self._add_tab(home=True)

    def take_snapshot(self):
        view = self.tabs.currentWidget()
        if not view:
            return

        # Grab screenshot of current tab
        pixmap = view.grab()

        # Desktop path
        desktop = os.path.join(os.path.expanduser("~"), "Desktop")

        # Darkelf Snap folder
        snap_dir = os.path.join(desktop, "Darkelf Snap Folder")

        # Create folder if missing
        os.makedirs(snap_dir, exist_ok=True)

        # Filename
        filename = f"darkelf_snapshot_{int(time.time())}.png"
        path = os.path.join(snap_dir, filename)

        # Save image
        pixmap.save(path, "PNG")
        
        self.debounce_cleanup

        print(f"[Darkelf] Snapshot saved → {path}")
        
    def setup_hotkeys(self):

        # New tab
        new_tab_action = QAction(self)
        new_tab_action.setShortcut("Ctrl+T")
        new_tab_action.triggered.connect(self.new_tab)
        self.addAction(new_tab_action)

        # Close tab
        close_tab_action = QAction(self)
        close_tab_action.setShortcut("Ctrl+W")
        close_tab_action.triggered.connect(self.close_tab)
        self.addAction(close_tab_action)

        # Reload
        reload_action = QAction(self)
        reload_action.setShortcut("Ctrl+R")
        reload_action.triggered.connect(self.reload_page)
        self.addAction(reload_action)

        # Focus URL
        focus_url_action = QAction(self)
        focus_url_action.setShortcut("Ctrl+L")
        focus_url_action.triggered.connect(lambda: self.url_bar.setFocus())

        # Next tab
        next_tab_action = QAction(self)
        next_tab_action.setShortcut("Ctrl+Tab")
        next_tab_action.triggered.connect(
            lambda: self.tabs.setCurrentIndex(
                (self.tabs.currentIndex() + 1) % self.tabs.count()
            )
        )
        self.addAction(next_tab_action)

        # Previous tab
        prev_tab_action = QAction(self)
        prev_tab_action.setShortcut("Ctrl+Shift+Tab")
        prev_tab_action.triggered.connect(
            lambda: self.tabs.setCurrentIndex(
                (self.tabs.currentIndex() - 1) % self.tabs.count()
            )
        )
        self.addAction(prev_tab_action)
        
        # Snapshot
        snapshot_action = QAction(self)
        snapshot_action.setShortcuts(["Ctrl+Shift+S", "Meta+Shift+S"])
        snapshot_action.triggered.connect(self.take_snapshot)
        self.addAction(snapshot_action)
        
    def _cleanup_webengine(self):
        # Close tabs from last to first
        for i in reversed(range(self.tabs.count())):
            self.close_tab(i)
            
    def handle_fullscreen(self, request):
        if request.toggleOn():
            self.showFullScreen()
        else:
            self.showNormal()

        request.accept()

    def _close_tab_current(self):
        self.close_tab(self.tabs.currentIndex())

    def current_view(self):
        w = self.tabs.currentWidget()
        return w if isinstance(w, QWebEngineView) else None

    def go_back(self):
        v = self.current_view()
        if v: v.back()
    def go_fwd(self):
        v = self.current_view()
        if v: v.forward()
    def reload(self):
        v = self.current_view()
        if v: v.reload()
    def go_home(self):
        v = self.current_view()
        if v:
            html = HOMEPAGE.replace("ACCENT_COLOR", self.accent_color)
            v.setHtml(html)
    def zoom_in(self):
        v = self.current_view()
        if v: v.setZoomFactor(v.zoomFactor() + 0.1)
    def zoom_out(self):
        v = self.current_view()
        if v: v.setZoomFactor(v.zoomFactor() - 0.1)
    def toggle_fullscreen(self):
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()
            
    def _sync_urlbar(self, url=None):
        v = self.current_view()
        if not v:
            return

        qurl = v.url() if url is None else url
        u = qurl.toString()

        if u.startswith("data:text/html"):
            self.addr.setText("")
            self.lock_action.setVisible(False)
            return

        self.addr.setText(u)

        if qurl.scheme() == "https":
            self.lock_action.setVisible(True)
            self.addr.setStyleSheet(f"""
                QLineEdit {{
                    color: {self.accent_color};
                    font-weight: bold;
                }}
            """)
        else:
            self.lock_action.setVisible(False)
            self.addr.setStyleSheet("""
                QLineEdit {
                    color: #cfd8e3;
                    font-weight: normal;
                }
            """)
            
    def toggle_javascript(self):
        enabled = self.java_action.isChecked()
        settings = self.shared_profile.settings()
        settings.setAttribute(QWebEngineSettings.JavascriptEnabled, enabled)
        for i in range(self.tabs.count()):
            view = self.tabs.widget(i)
            if isinstance(view, QWebEngineView):
                view.reload()
                
    def nuke_all_data(self):
        reply = QMessageBox.question(
            self,
            "Confirm Nuke",
            "This will erase ALL cookies, cache, history and close the browser.\n\nContinue?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply != QMessageBox.Yes:
            return

        try:
            # Stop all pages first (prevents WebEngine memory explosion)
            for i in range(self.tabs.count()):
                view = self.tabs.widget(i)
                if isinstance(view, QWebEngineView):
                    try:
                        view.page().triggerAction(QWebEnginePage.Stop)
                    except:
                        pass

            # Use the default profile once instead of per-tab
            profile = QWebEngineProfile.defaultProfile()

            profile.cookieStore().deleteAllCookies()
            profile.clearHttpCache()
            profile.clearAllVisitedLinks()

        except Exception as e:
            print("NUKE ERROR:", e)

        # Close all tabs safely
        self.tabs.clear()

        QMessageBox.information(
            self,
            "Nuke Complete",
            "All browser data wiped.\nBrowser will now close."
        )

        # Fully shutdown browser
        gc.collect()
        QApplication.quit()

    def authenticate_cookie(self, controller, cookie_path):
        try:
            with open(cookie_path, 'rb') as f:
                cookie = f.read()
            controller.authenticate(cookie)
        except Exception as e:
            print(f"[Darkelf] Tor cookie authentication failed: {e}")
            
    def _hook_secure_downloads(self):

        signal = self.shared_profile.downloadRequested

        if getattr(self, "_download_signal_connected", False):
            return

        signal.connect(self._handle_download_requested)
        self._download_signal_connected = True

    def _handle_download_requested(self, item):

        filename = _randomized_filename(item.downloadFileName())
        filename = os.path.basename(filename)

        item.setDownloadDirectory(self._download_dir)
        item.setDownloadFileName(filename)

        item.accept()

        # show shelf
        self.download_shelf.show()

        # add item to shelf
        self.download_shelf.add_download(item)
        
    def closeEvent(self, event):
        try:
            if hasattr(self, "mini_ai"):
                self.mini_ai.shutdown()
        except Exception as e:
            print("[MiniAI] shutdown error:", e)

        super().closeEvent(event)
        
    def _wipe_download_traces(self):
        """
        Deletes the per-session temp download directory (best-effort).
        """
        try:
            if getattr(self, "_download_dir", None) and os.path.isdir(self._download_dir):
                shutil.rmtree(self._download_dir, ignore_errors=True)
        except Exception:
            pass
