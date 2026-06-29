# shadow/browser.py

# --- Standard ---
import gc
import hashlib
import http.client
import json
import math
import os
import platform as _platform
import platform
import random
import re
import secrets
import shutil
import socket
import subprocess  # nosec B404
import sys
import tempfile
import time
import urllib.request
import uuid
from collections import deque
from urllib.error import HTTPError, URLError
from urllib.parse import quote_plus


# --- Qt Core ---
from PySide6.QtCore import (
    Qt, QUrl, QUrlQuery, QSize, QPointF, QRectF,
    QTimer, QPropertyAnimation, QThread, Signal, QEvent
)

# --- Qt GUI ---
from PySide6.QtGui import (
    QAction, QIcon, QPixmap, QPainter, QColor,
    QPalette, QPen, QBrush, QPolygonF,
    QPainterPath, QFont, QShortcut, QKeySequence
)

# --- Qt Widgets ---
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QLineEdit, QToolBar, QPushButton, QLabel,
    QWidget, QDialog, QMessageBox, QToolButton,
    QProgressBar, QMenu, QWidgetAction, QGridLayout, QVBoxLayout, QFrame, QScrollArea,
    QHBoxLayout, QFileDialog, QProgressDialog, QInputDialog, QStyle, QTabWidget, QSizePolicy
)

# --- Qt WebEngine ---
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebEngineCore import (
    QWebEngineProfile, QWebEnginePage, QWebEngineScript,
    QWebEngineSettings, QWebEngineUrlRequestInfo,
    QWebEngineUrlRequestInterceptor, QWebEngineDownloadRequest
)

# --- Nexus Modules ---
from shadow.miniai import DarkelfMiniAISentinel

from shadow.darkelf_context_menu import DarkelfContextMenu
from shadow.settings_dialog import DarkelfSettingsDialog

# --- Temporary legacy bridge (to be removed later) ---
from shadow.utils import (
    should_rotate,
    rotate_internal_seed,
    _safe_download_dir,
    _randomized_filename,
    sanitize_url_clearurls,
    DUCK_LITE_HTTPS,
    BOOTUP_CANVAS_SEED
)

from shadow.browser_icons import (
    make_nav_arrow_icon,
    make_reload_icon,
    make_bookmark_icon,
    make_bookmark_filled_icon,
    make_find_icon,
    make_keyboard_icon,
    make_java_icon,
    make_quantum_icon,
    make_shield_icon,
    make_nuke_icon,
    make_settings_icon,
    make_source_icon,
    make_cut_icon,
    make_copy_icon,
    make_paste_icon,
    make_delete_icon,
    make_select_all_icon,    
    detect_nav_platform,
)

from shadow.browser_downloads import (
    DownloadItem,
    DownloadShelf,
    create_color_palette_menu,
)

from shadow.browser_page import HardenedWebPage
from shadow.browser_homepage import HOMEPAGE

from shadow.browser_ui import BrowserUIMixin

#devnull = open(os.devnull, 'w')
#os.dup2(devnull.fileno(), sys.stderr.fileno())

# --------------------------------------------------
# Homepage Themes
# --------------------------------------------------

HOMEPAGE_THEMES = {
    "Aurora": ("#6D28D9", "#A855F7", "#14B8A6"),
    "Nebula": ("#0A2A66", "#0050B3", "#7C3AED"),
    "Void": ("#050505", "#121212", "#2B2B2B"),
    "Matrix": ("#003A1A", "#00AA44", "#00FF66"),
    "Circuit": ("#032D4B", "#0E7490", "#22D3EE"),
    "Graded": ("#1F2937", "#475569", "#9CA3AF"),
}

# ------------------------------------------------
# Main browser class
# ------------------------------------------------
class DarkelfBrowser(BrowserUIMixin, QMainWindow):
    def __init__(self, profile, mini_ai, engine):
        super().__init__()
        
        self.accent_color = "#A855F7"
        
        self.homepage_theme = ""

        self.setWindowTitle("")
        self.resize(1200, 800)

        # ✅ macOS FIX (PUT HERE)

        # ADD THIS
        self.setUnifiedTitleAndToolBarOnMac(False)

        self.setStyleSheet("""
        QMainWindow {
            background-color: #000000;
        }

        QToolBar {
            background-color: #000000;
            border: none;
        }
        """)

        self.shared_profile = profile
        print("OffTheRecord:", self.shared_profile.isOffTheRecord())

        # ✅ SET THESE FIRST (before ANY use)
        self.easy = engine
        self.mini_ai = mini_ai
        self.mini_ai.ui = self
        
        self.lockdown_timer = QTimer()

        self.lockdown_timer.timeout.connect(
            self.mini_ai.check_lockdown_timeout
        )

        self.lockdown_timer.start(1000)
        
        print("Loaded network rules:", len(self.easy.network_rules))
        
        # -----------------------------
        # Session Bookmarks
        # -----------------------------
        self.bookmarks = []
        
        # -----------------------------
        # TABS
        # -----------------------------
        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.setMovable(True)
        self.tabs.setDocumentMode(False)  # 🔥 IMPORTANT
        
        # + button on tab bar
        self.plus_btn = QToolButton()

        self.plus_btn.setText("+")
        self.plus_btn.setCursor(Qt.PointingHandCursor)

        # slightly tighter sizing
        self.plus_btn.setFixedSize(32, 32)

        # better alignment
        self.plus_btn.setStyleSheet(f"""
        QToolButton {{
            background: transparent;
            color: {self.accent_color};
            border: none;

            font-size: 22px;
            font-weight: 400;

            padding-bottom: 4px;
            padding-right: 6px;
        }}

        QToolButton:hover {{
            color: white;
        }}
        """)

        self.plus_btn.clicked.connect(
            lambda: self._add_tab(home=True)
        )

        self.tabs.setCornerWidget(
            self.plus_btn,
            Qt.TopRightCorner
        )
        
        self.tabs.tabCloseRequested.connect(self.close_tab)

        # -----------------------------
        # DOWNLOAD SHELF
        # -----------------------------
        self.download_shelf = DownloadShelf()
        self.download_shelf.hide()

        # -----------------------------
        # TOOLBAR (CREATE HERE)
        # -----------------------------
        self.toolbar = self._make_toolbar()

        # 🔥 THIS IS CRITICAL — DO NOT PUT TOOLBAR IN LAYOUT
        self.addToolBar(Qt.TopToolBarArea, self.toolbar)

        # -----------------------------
        # LAYOUT (NO TOOLBAR HERE)
        # -----------------------------
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        container = QWidget()

        self._create_find_bar()

        layout.addWidget(self.find_bar)
        layout.addWidget(self.tabs)
        layout.addWidget(self.download_shelf)

        container.setLayout(layout)
        self.setCentralWidget(container)
        # -----------------------------
        # STYLING
        # -----------------------------
        self._set_tab_style()
        self.set_accent_color(QColor(self.accent_color))

        # -----------------------------
        # STARTUP TAB
        # -----------------------------
        QApplication.instance().aboutToQuit.connect(self._cleanup_webengine)
        self._add_tab(home=True)

        # -----------------------------
        # DOWNLOADS
        # -----------------------------
        # Download folder is created lazily only when a download starts.
        self._download_dir = None
        self._downloaded_files: list[str] = []
        self._hook_secure_downloads()

        QApplication.instance().aboutToQuit.connect(self._wipe_download_traces)

        # -----------------------------
        # HOTKEYS
        # -----------------------------
        self._shortcuts = []
        self.setup_hotkeys()
        
        self.addr.installEventFilter(self)

        # -----------------------------
        # MINI AI TIMER
        # -----------------------------
        self.miniai_timer = QTimer()
        self.miniai_timer.timeout.connect(self.update_miniai_icon)
        self.miniai_timer.start(1500)

        # -----------------------------
        # MEMORY CLEANUP
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
        
    def _darkelf_library_dir(self):
        """
        Parent folder for Darkelf user-created artifacts.

        This folder is intentionally created lazily so it does not appear
        unless the user downloads a file or takes a snapshot.
        """
        desktop = os.path.join(os.path.expanduser("~"), "Desktop")
        return os.path.join(desktop, "Darkelf Library")

    def _ensure_private_dir(self, path):
        """
        Create a folder with user-only permissions where the OS supports it.
        """
        os.makedirs(path, mode=0o700, exist_ok=True)
            
        try:
            os.chmod(path, 0o700)
        except OSError:
            # Ignore permission or filesystem limitations.
            pass
            

        return path

    def _ensure_download_dir(self):
        """
        Create the temporary download folder only when a download starts.
        """
        library_dir = self._ensure_private_dir(self._darkelf_library_dir())

        download_dir = self._ensure_private_dir(
            os.path.join(library_dir, "Darkelf Temp Folder")
        )

        self._download_dir = download_dir
        return download_dir

    def _ensure_snapshot_dir(self):
        """
        Create the snapshot folder only when the user takes a snapshot.
        """
        library_dir = self._ensure_private_dir(self._darkelf_library_dir())

        return self._ensure_private_dir(
            os.path.join(library_dir, "Darkelf Snap Folder")
        )

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

        
    def close_tab(self, i=None):
        if i is None:
            i = self.tabs.currentIndex()

        if i < 0:
            return

        self.tabs.removeTab(i)

        if self.tabs.count() == 0:
            self._add_tab(home=True)

        new_view = self.current_view()
        if new_view:
            new_view.setFocus()

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
        
    def eventFilter(self, obj, event):
        if event.type() == QEvent.KeyPress:
            key = event.key()
            mods = event.modifiers()

            ctrl = bool(mods & Qt.ControlModifier)
            shift = bool(mods & Qt.ShiftModifier)
            alt = bool(mods & Qt.AltModifier)
            meta = bool(mods & Qt.MetaModifier)

            # Fullscreen: catch before QLineEdit/WebEngine can eat it
            if key == Qt.Key_F11 or (alt and key in (Qt.Key_Return, Qt.Key_Enter)):
                self.toggle_fullscreen()
                return True

            # Close tab
            if ctrl and key == Qt.Key_W:
                self.close_tab(self.tabs.currentIndex())
                return True

            # New tab
            if ctrl and key == Qt.Key_T:
                self.new_tab()
                return True

            # Reload
            if ctrl and key == Qt.Key_R:
                self.reload_page()
                return True

            # Focus URL bar
            if ctrl and key == Qt.Key_L:
                self.addr.setFocus()
                self.addr.selectAll()
                return True

            # Escape URL bar back to webpage
            if key == Qt.Key_Escape and self.addr.hasFocus():
                v = self.current_view()
                if v:
                    v.setFocus()
                return True

            # Tab switching
            if ctrl and key == Qt.Key_Tab:
                if self.tabs.count():
                    delta = -1 if shift else 1
                    self.tabs.setCurrentIndex(
                        (self.tabs.currentIndex() + delta) % self.tabs.count()
                    )
                return True

            # Zoom
            if ctrl and key in (Qt.Key_Equal, Qt.Key_Plus):
                self.zoom_in()
                return True

            if ctrl and key == Qt.Key_Minus:
                self.zoom_out()
                return True

            if ctrl and key == Qt.Key_0:
                self.reset_zoom()
                return True

        return super().eventFilter(obj, event)
        
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

    def make_outline_lock_icon(self, color="#ffffff", size=24):
        pix = QPixmap(size, size)
        pix.fill(Qt.transparent)

        p = QPainter(pix)
        p.setRenderHint(QPainter.Antialiasing)

        pen = QPen(QColor(color))
        pen.setWidth(2)
        p.setPen(pen)

        body_w = size * 0.42
        body_h = size * 0.34

        x = (size - body_w) / 2
        y = size * 0.48

        p.drawRoundedRect(x, y, body_w, body_h, 2, 2)

        p.drawArc(
            int(x),
            int(size * 0.18),
            int(body_w),
            int(size * 0.50),
            0,
            180 * 16
        )

        p.end()
        return QIcon(pix)
            

    # ------------------------------------------------
    # BOOKMARK CARD
    # ------------------------------------------------

    def _create_bookmark_card(self, bookmark):

        title = bookmark["title"]
        url = bookmark["url"]

        card = QFrame()

        card.setStyleSheet(f"""
        QFrame {{
            background:#11161d;
            border:1px solid #242b36;
            border-radius:16px;
        }}

        QLabel {{
            background:transparent;
            color:white;
        }}

        QPushButton {{
            background:#1a2028;
            border:1px solid #313b48;
            border-radius:10px;
            color:white;
            padding:6px 16px;
        }}

        QPushButton:hover {{
            border:1px solid {self.accent_color};
        }}
        """)

        outer = QVBoxLayout(card)
        outer.setContentsMargins(18,18,18,18)
        outer.setSpacing(10)

        top = QHBoxLayout()

        icon = QLabel()
        icon.setFixedSize(42, 42)
        icon.setAlignment(Qt.AlignCenter)

        fav = bookmark.get("icon")

        if fav and not fav.isNull():
            icon.setPixmap(fav.pixmap(32, 32))
        else:
            icon.setText("🌐")
            icon.setStyleSheet(f"""
                background:{self.accent_color};
                color:black;
                border-radius:21px;
                font-size:18px;
                font-weight:bold;
            """)

        labels = QVBoxLayout()

        title_lbl = QLabel(title)
        title_lbl.setStyleSheet("""
            font-size:16px;
            font-weight:700;
            color:white;
        """)

        url_lbl = QLabel(url)
        url_lbl.setStyleSheet("""
            color:#8f99a6;
            font-size:12px;
        """)

        labels.addWidget(title_lbl)
        labels.addWidget(url_lbl)

        top.addWidget(icon)
        top.addSpacing(12)
        top.addLayout(labels)
        top.addStretch()

        outer.addLayout(top)

        buttons = QHBoxLayout()
        buttons.addStretch()

        open_btn = QPushButton("Open")
        remove_btn = QPushButton("Remove")

        buttons.addWidget(open_btn)
        buttons.addWidget(remove_btn)

        outer.addLayout(buttons)

        open_btn.clicked.connect(
            lambda: self.navigate_to(url)
        )

        remove_btn.clicked.connect(
            lambda: self.remove_bookmark(card, title, url)
        )

        return card
        
        # ------------------------------------------------
        # REFRESH BOOKMARK LIST
        # ------------------------------------------------

    def refresh_bookmark_manager(self):

        if getattr(self, "bookmark_cards", None) is None:
            return
    
        if not hasattr(self, "bookmarks"):
            self.bookmarks = []
            
        while self.bookmark_cards.count() > 1:

            item = self.bookmark_cards.takeAt(0)

            if item.widget():
                item.widget().deleteLater()

        if not getattr(self, "bookmarks", None):

            empty = QLabel(
                "No bookmarks yet.\n\nSave your favorite websites here."
            )

            empty.setAlignment(Qt.AlignCenter)

            empty.setStyleSheet("""
                color:#7b8592;
                font-size:15px;
                padding:50px;
            """)

            self.bookmark_cards.insertWidget(0, empty)

            return

        for bm in self.bookmarks:

            card = self._create_bookmark_card(bm)

            self.bookmark_cards.insertWidget(0, card)
            
                
    def _build_threat_report_html(self):

        stats = self.mini_ai.get_statistics()

        base = QColor(self.accent_color)

        accent  = base.name()
        accent2 = base.lighter(130).name()
        accent3 = base.darker(130).name()

        accent_rgba  = f"rgba({base.red()}, {base.green()}, {base.blue()}, .45)"

        accent2_rgba = (
            f"rgba({base.lighter(130).red()}, "
            f"{base.lighter(130).green()}, "
            f"{base.lighter(130).blue()}, .40)"
        )

        accent3_rgba = (
            f"rgba({base.darker(130).red()}, "
            f"{base.darker(130).green()}, "
            f"{base.darker(130).blue()}, .45)"
        )

        grid_rgba = f"rgba({base.red()}, {base.green()}, {base.blue()}, .18)"

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
    --accent:{accent};
    --accent2:{accent2};
    --accent3:{accent3};
    --danger:#ff3b30;
    --warn:#ffd36b;
    --muted:#9db0be;
    --card:rgba(255,255,255,.05);
    }}

    *{{box-sizing:border-box}}
    html,body{{margin:0;height:100%;font-family:ui-sans-serif,system-ui,-apple-system;}}

    body{{
    background:
    radial-gradient(1200px 800px at 15% -10%,
    {accent_rgba},
    transparent 70%),

    radial-gradient(900px 600px at 110% 0%,
    {accent2_rgba},
    transparent 70%),

    radial-gradient(1200px 700px at 50% 120%,
    {accent3_rgba},
    transparent 70%),

    var(--bg);

    color:#eef2f6;
    }}

    body::before {{
    content:"";
    position:fixed;
    inset:0;

    background:
    linear-gradient(
    {grid_rgba} 1px,
    transparent 1px
    ),

    linear-gradient(
    90deg,
    {grid_rgba} 1px,
    transparent 1px
    );

    background-size:40px 40px;
    pointer-events:none;
    opacity:.22;
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

    .green {{background:var(--accent)}}
    .cyan {{background:var(--accent2)}}
    .purple {{background:var(--accent3)}}

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
    box-shadow:0 0 40px {accent2_rgba};
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


        
    @staticmethod
    def _short_label_from_qurl(qurl):
        try:
            host = qurl.host().lower() if hasattr(qurl, "host") else ""
        except Exception as e:
            print(e)
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
        view.setFocusPolicy(Qt.StrongFocus)
        view.installEventFilter(self)
        view._profile = profile
        
        page = HardenedWebPage(view, profile, canvas_seed=canvas_seed)
        page._parent_view = view
        view.setPage(page)
        page.fullScreenRequested.connect(self.handle_fullscreen)
        
        view.setContextMenuPolicy(Qt.CustomContextMenu)
        view.customContextMenuRequested.connect(
            lambda pos, v=view: self.show_page_context_menu(v, pos)
        )
        
        # --------------------------------
        # Keep bookmark icon synchronized
        # --------------------------------

        view.urlChanged.connect(
            lambda *_: self.update_bookmark_icon()
        )

        view.loadFinished.connect(
            lambda *_: self.update_bookmark_icon()
        )

        view.titleChanged.connect(
            lambda *_: self.update_bookmark_icon()
        )
        
        # ---- EasyList Cosmetic Injection ----
        def apply_easylist_cosmetics(v=view):
            try:
                host = v.url().host().lower()
            except Exception as e:
                print(e)
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
        
        self.tabs.currentChanged.connect(
            lambda *_: self.update_bookmark_icon()
        )
        
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
            bg1, bg2, bg3 = HOMEPAGE_THEMES.get(
                self.homepage_theme,
                HOMEPAGE_THEMES["Nebula"]
            )

            html = (
                HOMEPAGE
                .replace("ACCENT_COLOR", self.accent_color)
                .replace("BG1", bg1)
                .replace("BG2", bg2)
                .replace("BG3", bg3)
            )

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
        
    def open_source(self, url):
        try:
            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent": "Mozilla/5.0"
                }
            )

            with urllib.request.urlopen(req) as response:
                html = response.read().decode(
                    "utf-8",
                    errors="replace"
                )

            self._show_source_tab(html)

        except Exception as e:
            self._show_source_tab(
                f"<h2>Unable to load source</h2><pre>{e}</pre>"
            )

    def close_tab(self, idx):
        w = self.tabs.widget(idx)

        self.tabs.removeTab(idx)

        if isinstance(w, QWebEngineView):
            try:
                w.page().runJavaScript(
                    "document.querySelectorAll('video,audio').forEach(m=>{try{m.pause(); m.src='';}catch(e){}})"
                )
            except Exception as e:
                print(e)
                pass

            try:
                w.page().triggerAction(QWebEnginePage.Stop)
                w.page().setAudioMuted(True)
                w.setUrl(QUrl("about:blank"))
            except Exception as e:
                print(e)
                pass

            w.page().deleteLater()
            w.deleteLater()

        # reopen homepage if all tabs closed
        if self.tabs.count() == 0:
            self._add_tab(home=True)
                    

    # ------------------------------------------------
    # BOOKMARK MANAGER (Darkelf Style)
    # ------------------------------------------------

    def show_bookmark_manager(self):

        if hasattr(self, "_bookmark_dialog"):
            try:
                self._bookmark_dialog.close()
            except Exception:
                pass

        dlg = QDialog(self)
        self._bookmark_dialog = dlg

        dlg.resize(760, 620)
        dlg.setWindowTitle("Bookmarks")

        dlg.setStyleSheet(f"""
        QDialog {{
        background:#090b10;
        }}

        QLabel {{
            color:white;
            background:transparent;
        }}

        QLineEdit {{
            background:#11161d;
            color:white;
            border:1px solid #252b36;
            border-radius:14px;
            padding:10px;
            font-size:14px;
        }}

        QLineEdit:focus {{
            border:1px solid {self.accent_color};
        }}

        QPushButton {{
            background:#11161d;
            color:white;
            border:1px solid #2d3642;
            border-radius:12px;
            padding:8px 18px;
        }}

        QPushButton:hover {{
            border:1px solid {self.accent_color};
        }}

        QPushButton#accent {{
            background:{self.accent_color};
            color:black;
            font-weight:bold;
            border:none;
        }}

        QScrollArea {{
            border:none;
            background:transparent;
        }}
        """)

        layout = QVBoxLayout(dlg)
        layout.setContentsMargins(26,26,26,26)
        layout.setSpacing(18)

        title = QLabel("Bookmarks")
        title.setStyleSheet(f"""
            font-size:28px;
            font-weight:800;
            color:{self.accent_color};
        """)

        subtitle = QLabel("Manage your saved bookmarks")
        subtitle.setStyleSheet("color:#9aa5b1;")

        layout.addWidget(title)
        layout.addWidget(subtitle)

        self.bookmark_title = QLineEdit()
        self.bookmark_title.setPlaceholderText("Bookmark title")

        self.bookmark_url = QLineEdit()
        self.bookmark_url.setPlaceholderText("https://example.com")

        layout.addWidget(self.bookmark_title)
        layout.addWidget(self.bookmark_url)

        row = QHBoxLayout()

        self.add_bookmark_btn = QPushButton("Add Bookmark")
        self.add_bookmark_btn.setObjectName("accent")
        
        self.add_bookmark_btn.clicked.connect(
            self.add_bookmark
        )
        
        row.addStretch()
        row.addWidget(self.add_bookmark_btn)

        layout.addLayout(row)

        self.bookmark_scroll = QScrollArea()
        self.bookmark_scroll.setWidgetResizable(True)

        holder = QWidget()

        self.bookmark_cards = QVBoxLayout(holder)
        self.bookmark_cards.setSpacing(12)
        self.bookmark_cards.setContentsMargins(0,0,0,0)
        self.bookmark_cards.addStretch()

        self.bookmark_scroll.setWidget(holder)

        layout.addWidget(self.bookmark_scroll)
        
        self.refresh_bookmark_manager()
        
        dlg.exec()
        
    # ------------------------------------------------
    # ADD BOOKMARK
    # ------------------------------------------------

    def add_bookmark(self):
    
        if not hasattr(self, "bookmarks"):
            self.bookmarks = []
            
        title = self.bookmark_title.text().strip()
        url = self.bookmark_url.text().strip()

        if not url:
            QMessageBox.warning(
                self,
                "Bookmark",
                "Please enter a URL."
            )
            return
    
        if not title:
            title = url

        # prevent duplicates
        for bm in self.bookmarks:
            if bm["url"] == url:
                QMessageBox.information(
                    self,
                    "Bookmark",
                    "That bookmark already exists."
                )
                return

        self.bookmarks.insert(0, {
            "title": title,
            "url": url
        })

        self.bookmark_title.clear()
        self.bookmark_url.clear()

        self.refresh_bookmark_manager()


    # ------------------------------------------------
    # REMOVE BOOKMARK
    # ------------------------------------------------

    def remove_bookmark(self, card, title, url):

        # Session-only bookmark list
        if not hasattr(self, "bookmarks"):
            self.bookmarks = []
            return

        self.bookmarks = [
            bm
            for bm in self.bookmarks
            if not (
                bm["title"] == title
                and
                bm["url"] == url
            )
        ]

        if card is not None:
            card.deleteLater()

        self.refresh_bookmark_manager()
        
        self.update_bookmark_icon()

        if hasattr(self, "bookmark_bar"):
            self.refresh_bookmark_bar()

    # ------------------------------------------------
    # OPEN BOOKMARK
    # ------------------------------------------------

    def navigate_to(self, url):

        self._add_tab(url=url)
        
    def next_tab(self):
        count = self.tabs.count()
        if count <= 1:
            return

        self.tabs.setCurrentIndex(
            (self.tabs.currentIndex() + 1) % count
        )

        v = self.current_view()
        if v:
            v.setFocus()


    def prev_tab(self):
        count = self.tabs.count()
        if count <= 1:
            return

        self.tabs.setCurrentIndex(
            (self.tabs.currentIndex() - 1) % count
        )

        v = self.current_view()
        if v:
            v.setFocus()
            
    def _shortcut(self, keys, callback):
        if isinstance(keys, str):
            keys = [keys]

        for key in keys:
            sc = QShortcut(QKeySequence(key), self)
            sc.setContext(Qt.ApplicationShortcut)
            sc.activated.connect(callback)
            self._shortcuts.append(sc)

    def setup_hotkeys(self):
        self._shortcut("Ctrl+T", self.new_tab)

        self._shortcut("Ctrl+W", lambda: self.close_tab(self.tabs.currentIndex()))

        self._shortcut("Ctrl+R", self.reload_page)

        self._shortcut("Ctrl+F", self.show_find_bar)
        self._shortcut("Ctrl+G", self.find_next)

        self._shortcut(["Ctrl+=", "Ctrl++", "Meta+=", "Meta++"], self.zoom_in)
        self._shortcut(["Ctrl+-", "Meta+-"], self.zoom_out)
        self._shortcut(["Ctrl+0", "Meta+0"], self.reset_zoom)

        self._shortcut("Ctrl+L", lambda: self.addr.setFocus())

        self._shortcut(["Ctrl+Shift+S", "Meta+Shift+S"], self.take_snapshot)

        self._shortcut(
            ["Ctrl+PgUp", "Meta+Left", "Alt+Left"],
            self.prev_tab
        )

        self._shortcut(
            ["Ctrl+PgDown", "Meta+Right", "Alt+Right"],
            self.next_tab
        )

        self._shortcut(
            ["F11", "Alt+Return", "Alt+Enter", "Meta+Return"],
            self.toggle_fullscreen
        )
        
        self._shortcut(
            ["Ctrl+Tab", "Meta+Right", "Alt+Right", "Ctrl+PgDown"],
            self.next_tab
        )
        
    def take_snapshot(self):
        view = self.tabs.currentWidget()
        if not view:
            return

        # Grab screenshot of current tab
        pixmap = view.grab()

        # Create Darkelf Library/Snap Folder lazily only when a snapshot is taken.
        snap_dir = self._ensure_snapshot_dir()

        # Filename
        filename = f"darkelf_snapshot_{int(time.time())}.png"
        path = os.path.join(snap_dir, filename)

        # Save image
        pixmap.save(path, "PNG")
        
        self.debounce_cleanup()

        print(f"[Darkelf] Snapshot saved → {path}")
        
    def _create_find_bar(self):
        self.find_bar = QFrame()
        self.find_bar.hide()
        self.find_bar.setFixedHeight(42)

        self._update_find_bar_style()

        layout = QHBoxLayout(self.find_bar)
        layout.setContentsMargins(12, 4, 12, 4)
        layout.setSpacing(8)

        title = QLabel("Find")

        self.find_edit = QLineEdit()
        self.find_edit.setPlaceholderText("Find in page")
        self.find_edit.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Fixed
        )

        self.find_count = QLabel("")

        self.find_prev_btn = QToolButton()
        self.find_prev_btn.setText("‹")

        self.find_next_btn = QToolButton()
        self.find_next_btn.setText("›")

        self.find_close_btn = QToolButton()
        self.find_close_btn.setText("✕")
        
        for btn in (
            self.find_prev_btn,
            self.find_next_btn,
            self.find_close_btn,
        ):
            btn.setFixedSize(34, 34)
            btn.setStyleSheet("""
                QToolButton {{
                    font-size: 24px;
                    font-weight: 300;
                }}
            """)
            
        layout.addWidget(title)
        layout.addWidget(self.find_edit)
        layout.addWidget(self.find_count)
        layout.addWidget(self.find_prev_btn)
        layout.addWidget(self.find_next_btn)

        layout.addStretch()

        layout.addWidget(self.find_close_btn)

        self.find_edit.textChanged.connect(self.find_text)
        self.find_edit.returnPressed.connect(self.find_next)

        self.find_prev_btn.clicked.connect(self.find_previous)
        self.find_next_btn.clicked.connect(self.find_next)
        self.find_close_btn.clicked.connect(self.hide_find_bar)
        
    def _update_find_bar_style(self):
        c = self.accent_color

        self.find_bar.setStyleSheet(f"""
        QFrame {{
            background:#10131a;
            border-top:1px solid #20242d;
            border-bottom:1px solid #20242d;
        }}

        QLineEdit {{
            background:#161b24;
            color:white;
            border:1px solid #252b36;
            border-radius:8px;
            padding:5px 10px;
            selection-background-color:{c};
            selection-color:black;
        }}

        QLineEdit:focus {{
            border:1px solid {c};
        }}

        QLabel {{
            color:#8f99a6;
            background:transparent;
            font-size:12px;
        }}

        QToolButton {{
            background: transparent;
            border: none;
            color: #cfd8e3;
            border-radius: 8px;

            min-width: 36px;
            min-height: 36px;
            max-width: 36px;
            max-height: 36px;

            font-size: 24px;
            font-weight: 600;
        }}

        QToolButton:hover {{
            color:{c};
            background:rgba(255,255,255,.08);
        }}

        QToolButton:pressed {{
            background: rgba(255,255,255,.15);
        }}
        """)
        
    def show_find_bar(self):
        self.find_bar.show()
        self.find_edit.setFocus()
        self.find_edit.selectAll()

    def hide_find_bar(self):
        self.find_bar.hide()

        view = self.current_view()

        if view:
            view.page().findText("")
            view.setFocus()

        self.find_edit.clear()
        self.find_count.clear()
            
    def find_text(self, text):
        view = self.current_view()

        if not view:
            return

        self._last_find_text = text

        view.page().findText("")

        if text:
            view.page().findText(text)
            
    def find_next(self):
        if not getattr(self, "_last_find_text", ""):
            return

        view = self.current_view()

        if view:
            view.page().findText(
                self._last_find_text,
                QWebEnginePage.FindFlag(0)
            )
            
    def find_previous(self):
        if not getattr(self, "_last_find_text", ""):
            return

        view = self.current_view()

        if view:
            view.page().findText(
                self._last_find_text,
                QWebEnginePage.FindBackward
            )
            
    def _shortcut(self, keys, callback):
        if isinstance(keys, str):
            keys = [keys]

        for key in keys:
            sc = QShortcut(QKeySequence(key), self)
            sc.setContext(Qt.ApplicationShortcut)
            sc.activated.connect(callback)
            self._shortcuts.append(sc)
        
    def reset_zoom(self):
        v = self.current_view()
        if v:
            v.setZoomFactor(1.0)
            
    def _cleanup_webengine(self):
    
        self._destroy_quantum_state()
        
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
        if not v:
            return

        bg1, bg2, bg3 = HOMEPAGE_THEMES.get(
            self.homepage_theme,
            HOMEPAGE_THEMES["Nebula"]
        )

        html = (
            HOMEPAGE
            .replace("ACCENT_COLOR", self.accent_color)
            .replace("BG1", bg1)
            .replace("BG2", bg2)
            .replace("BG3", bg3)
        )

        v.setHtml(html)
        v._is_homepage = True
        
    def refresh_homepage(self):
        for i in range(self.tabs.count()):
            view = self.tabs.widget(i)

            if getattr(view, "_is_homepage", False):

                bg1, bg2, bg3 = HOMEPAGE_THEMES.get(
                    self.homepage_theme,
                    HOMEPAGE_THEMES["Aurora"]
                )

                html = (
                    HOMEPAGE
                    .replace("ACCENT_COLOR", self.accent_color)
                    .replace("BG1", bg1)
                    .replace("BG2", bg2)
                    .replace("BG3", bg3)
                )

                view.setHtml(html)
                
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
                
    def confirm_nuke_dialog(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("Delete browsing data")
        dlg.setModal(True)
        dlg.setFixedSize(560, 220)

        dlg.setStyleSheet(f"""
        QDialog {{
            background:#0d1017;
            border:1px solid #24293a;
            border-radius:24px;
        }}

        QLabel#title {{
            color:white;
            font-size:22px;
            font-weight:700;
        }}

        QLabel#text {{
            color:#9aa5b1;
            font-size:14px;
        }}

        QPushButton {{
            background:#171b27;
            color:white;
            border:1px solid #262d42;
            border-radius:14px;
            min-height:40px;
            padding:0 28px;
            font-size:15px;
        }}

        QPushButton:hover {{
            border:1px solid {self.accent_color};
        }}

        QPushButton#danger {{
            color:#ff6666;
            border:1px solid #5a2b34;
        }}

        QPushButton#danger:hover {{
            background:#30161a;
            border:1px solid #ff6666;
        }}
        """)

        layout = QVBoxLayout(dlg)
        layout.setContentsMargins(32, 24, 32, 24)
        layout.setSpacing(16)

        title = QLabel("Delete browsing data")
        title.setObjectName("title")

        text = QLabel(
            "This wipes all cookies, cache and visited links, "
            "then closes the browser."
        )
        text.setWordWrap(True)
        text.setObjectName("text")

        layout.addWidget(title)
        layout.addWidget(text)
        layout.addStretch()

        buttons = QHBoxLayout()
        buttons.addStretch()

        cancel = QPushButton("Cancel")
        delete = QPushButton("Delete and Quit")
        delete.setObjectName("danger")

        buttons.addWidget(cancel)
        buttons.addSpacing(12)
        buttons.addWidget(delete)

        layout.addLayout(buttons)

        cancel.clicked.connect(dlg.reject)
        delete.clicked.connect(dlg.accept)

        return dlg.exec() == QDialog.Accepted
        
    def nuke_all_data(self):
    
        self._destroy_quantum_state()
        
        if not self.confirm_nuke_dialog():
            return

        try:
            # Stop all pages first
            for i in range(self.tabs.count()):
                view = self.tabs.widget(i)
                if isinstance(view, QWebEngineView):
                    try:
                        view.page().triggerAction(QWebEnginePage.Stop)
                    except Exception as e:
                        print("Error stopping page:", e)

            profile = QWebEngineProfile.defaultProfile()

            # Wipe browser data
            profile.cookieStore().deleteAllCookies()
            profile.clearHttpCache()
            profile.clearAllVisitedLinks()

        except Exception as e:
            print("NUKE ERROR:", e)

        # Close every tab
        self.tabs.clear()

        # Force cleanup
        gc.collect()

        # Quit shortly after cleanup
        QTimer.singleShot(150, QApplication.quit)
        
    def _destroy_quantum_state(self):
        interceptor = getattr(
            self.shared_profile,
            "_darkelf_interceptor",
            None
        )

        if interceptor and hasattr(interceptor, "pq"):
            interceptor.pq.destroy()
            
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

        # Create Darkelf Library/Temp Folder lazily only when a download starts.
        download_dir = self._ensure_download_dir()

        item.setDownloadDirectory(download_dir)
        item.setDownloadFileName(filename)

        self._downloaded_files.append(os.path.join(download_dir, filename))

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
        except Exception as e:
            print(e)
            pass
        
if __name__ == "__main__":

    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    # ===== PALETTE =====
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor("#0a0b10"))
    palette.setColor(QPalette.WindowText, QColor("#eafaf0"))
    palette.setColor(QPalette.Base, QColor("#12141b"))
    palette.setColor(QPalette.AlternateBase, QColor("#0f1114"))
    palette.setColor(QPalette.ToolTipBase, QColor("#eafaf0"))
    palette.setColor(QPalette.ToolTipText, QColor("#0a0b10"))
    palette.setColor(QPalette.Text, QColor("#eafaf0"))
    palette.setColor(QPalette.Button, QColor("#0f1114"))
    palette.setColor(QPalette.ButtonText, QColor("#eafaf0"))
    palette.setColor(QPalette.Highlight, QColor(self.accent_color))
    palette.setColor(QPalette.HighlightedText, QColor("#0a0b10"))
    app.setPalette(palette)

    app.setStyleSheet(app.styleSheet() + """
    QMenu { background: qlineargradient(x1:0,y1:0,x2:0,y1:1, stop:0 #171b20, stop:1 #15191c);
    border: 1px solid #1a1f23; border-radius: 6px; padding: 6px;}
    QMenu::separator{ height:1px; background:#23292e; margin:6px 8px; }
    QMenu::item{ color: #e5e7eb; padding:6px 16px; border-radius:8px; background:transparent;}
    QMenu::item:selected, QMenu::item:hover{background:#A855F7;color:#181a1b;font-weight:bold;}
    QMenu::item:disabled {color:#7f8c8d;background:transparent;}
    QToolTip{background:#161a1e;color:#e5e7eb;border:1px solid #22292f; padding:6px 8px;}
    """)

    # ===== SPLASH =====
    splash = BootSplash()
    splash.show()
    app.processEvents()

    # ===== INIT (NO TOR) =====
    splash.status.setText("Initializing network...")
    app.processEvents()

    # ===== PROFILE =====
    splash.status.setText("Preparing secure profile...")
    app.processEvents()

    profile = QWebEngineProfile("", app)
    profile.setHttpCacheType(QWebEngineProfile.MemoryHttpCache)
    profile.setPersistentCookiesPolicy(QWebEngineProfile.NoPersistentCookies)
    profile.setHttpAcceptLanguage("en-US,en;q=0.9")

    settings = profile.settings()
    settings.setAttribute(QWebEngineSettings.LocalStorageEnabled, True)
    settings.setAttribute(QWebEngineSettings.PluginsEnabled, False)
    settings.setAttribute(QWebEngineSettings.HyperlinkAuditingEnabled, False)
    settings.setAttribute(QWebEngineSettings.JavascriptCanOpenWindows, False)
    settings.setAttribute(QWebEngineSettings.JavascriptCanAccessClipboard, False)
    settings.setAttribute(QWebEngineSettings.LocalContentCanAccessRemoteUrls, False)
    settings.setAttribute(QWebEngineSettings.LocalContentCanAccessFileUrls, False)
    settings.setAttribute(QWebEngineSettings.FullScreenSupportEnabled, True)

    # ===== SCRIPT INJECTION =====
    script = QWebEngineScript()
    script.setName("darkelf_global_patch")
    script.setInjectionPoint(QWebEngineScript.DocumentCreation)
    script.setWorldId(QWebEngineScript.MainWorld)
    script.setRunsOnSubFrames(True)
    profile.scripts().insert(script)

    # ===== WORKER =====
    worker = BootWorker()
    splash._anim = None

    def update_progress(val, text):
        splash.status.setText(text)

        anim = QPropertyAnimation(splash.bar, b"value")
        anim.setDuration(300)
        anim.setStartValue(splash.bar.value())
        anim.setEndValue(val)
        anim.start()

        splash._anim = anim

    def boot_done(ai):
        splash.close()
        w = DarkelfBrowser(profile)
        w.show()

    worker.progress.connect(update_progress)
    worker.finished.connect(boot_done)

    worker.start()

    sys.exit(app.exec())
