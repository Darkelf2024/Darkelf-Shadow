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
    QProgressBar, QMenu, QWidgetAction, QGridLayout, QVBoxLayout,
    QHBoxLayout, QFileDialog, QProgressDialog, QInputDialog, QStyle, QTabWidget
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
    make_house_icon,
    make_keyboard_icon,
    make_java_icon,
    make_shield_icon,
    make_nuke_icon,
    detect_nav_platform,
)

from shadow.browser_downloads import (
    DownloadItem,
    DownloadShelf,
    create_color_palette_menu,
)

from shadow.browser_page import HardenedWebPage
from shadow.browser_homepage import HOMEPAGE

devnull = open(os.devnull, 'w')
os.dup2(devnull.fileno(), sys.stderr.fileno())

# ------------------------------------------------
# Main browser class
# ------------------------------------------------
class DarkelfBrowser(QMainWindow):
    def __init__(self, profile, mini_ai, engine):
        super().__init__()
        
        self.accent_color = "#A855F7"

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

            font-size: 26px;
            font-weight: 700;

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

        layout.addWidget(self.tabs)
        layout.addWidget(self.download_shelf)

        container = QWidget()
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
        except Exception:
            # Some platforms/filesystems, especially Windows, may ignore POSIX chmod.
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
        tb.setIconSize(QSize(24, 24))

        c = self.accent_color

        self.back_action = QAction(make_nav_arrow_icon("left", c, 22), "Back", self)
        self.fwd_action = QAction(make_nav_arrow_icon("right", c, 22), "Forward", self)
        self.reload_action = QAction(make_reload_icon(c, 22), "Reload", self)
        self.home_action = QAction(make_house_icon(c, 22), "Home", self)


        self.java_action = QAction(make_java_icon(self.accent_color, 18), "JavaScript", self)
        self.miniai_action = QAction(
            make_shield_icon(self.accent_color, 18),
            "MiniAI Monitor",
            self
            )
        self.miniai_action.triggered.connect(self.show_miniai_status)

        self.nuke_action = QAction(
            make_nuke_icon(self.accent_color, 18),
            "Nuke",
            self
        )

        self.nuke_action.triggered.connect(self.nuke_all_data)

        self.back_action.triggered.connect(self.go_back)
        self.fwd_action.triggered.connect(self.go_fwd)
        self.reload_action.triggered.connect(self.reload)
        self.home_action.triggered.connect(self.go_home)

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
        
        # Clear / X button
        self.clear_action = self.addr.addAction(
            self.style().standardIcon(
                QStyle.SP_LineEditClearButton
            ),
            QLineEdit.TrailingPosition
        )

        self.clear_action.triggered.connect(
            self.addr.clear
        )

        # Hide until text exists
        self.clear_action.setVisible(False)

        # Auto show/hide
        self.addr.textChanged.connect(
            lambda text: self.clear_action.setVisible(bool(text))
        )
        
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
        
        # ---- Hotkey button ----

        self.hotkey_action = QAction(
            make_keyboard_icon(self.accent_color, 18),
            "Hotkeys",
            self
        )

        self.hotkey_action.setToolTip(
            "Keyboard Shortcuts"
        )

        self.hotkey_action.triggered.connect(
            self.show_hotkey_help
        )

        tb.addAction(self.hotkey_action)
        
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

        win.exec()

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
        self.java_action.setIcon(make_java_icon(c, 18))
        self.miniai_action.setIcon(make_shield_icon(c, 18))
        self.hotkey_action.setIcon(make_keyboard_icon(color.name(), 18))
        self.nuke_action.setIcon(make_nuke_icon(self.accent_color, 18))
        
        
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
        
        if hasattr(self, "plus_btn"):

            self.plus_btn.setStyleSheet(f"""
            QToolButton {{
                background: transparent;
                color: {self.accent_color};
                border: none;

                font-size: 26px;
                font-weight: 700;

                padding-bottom: 4px;
                padding-right: 6px;
            }}

            QToolButton:hover {{
                color: white;
            }}
            """)
            
        for i in range(self.tabs.count()):
            view = self.tabs.widget(i)

            js = f"""
            document.documentElement.style.setProperty('--accent', '{self.accent_color}');
            """

            try:
                view.page().runJavaScript(js)
            except Exception as e:
                print("Error:", e)


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
        view.setPage(page)
        page.fullScreenRequested.connect(self.handle_fullscreen)
        
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
            
    def show_hotkey_help(self):

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
        <meta charset="utf-8">

        <style>

        html, body {{
            margin:0;
            padding:0;
            background:#0b0d11;
            color:white;
            font-family:
                Inter,
                system-ui,
                sans-serif;
        }}

        body {{
            padding:28px;
        }}

        h1 {{
            color:{self.accent_color};
            font-size:24px;
            margin-bottom:24px;
        }}

        .group {{
            margin-bottom:24px;
        }}

        .title {{
            color:{self.accent_color};
            font-size:13px;
            letter-spacing:.12em;
            text-transform:uppercase;
            margin-bottom:10px;
            opacity:.85;
        }}

        .row {{
            display:flex;
            justify-content:space-between;
            align-items:center;

            background:rgba(255,255,255,.04);

            border:1px solid rgba(255,255,255,.06);

            padding:12px 14px;
            border-radius:12px;

            margin-bottom:8px;
        }}

        .key {{
            font-weight:700;
            color:{self.accent_color};
        }}

        .desc {{
            color:#d7dce2;
        }}

        </style>
        </head>
        
        

        <body>

            <h1>Keyboard Shortcuts</h1>

            <div class="group">

                <div class="title">
                    Tabs
                </div>

                <div class="row">
                    <div class="desc">New Tab</div>
                    <div class="key">Ctrl/⌘ + T</div>
                </div>

                <div class="row">
                    <div class="desc">Close Tab</div>
                    <div class="key">Ctrl/⌘ + W</div>
                </div>

                <div class="row">
                    <div class="desc">Focus Address Bar</div>
                    <div class="key">Ctrl/⌘ + L</div>
                </div>

            </div>

            <div class="group">

                <div class="title">
                    Navigation
                </div>

                <div class="row">
                    <div class="desc">Reload Page</div>
                    <div class="key">Ctrl/⌘ + R</div>
                </div>
                
                <div class="row">
                    <div class="desc">Take Snapshot</div>
                    <div class="key">Ctrl+Shift+S</div>
                </div>

            </div>

            <div class="group">

                <div class="title">
                    Zoom
                </div>

                <div class="row">
                    <div class="desc">Zoom In</div>
                    <div class="key">Ctrl/⌘ + +</div>
                </div>

                <div class="row">
                    <div class="desc">Zoom Out</div>
                    <div class="key">Ctrl/⌘ + -</div>
                </div>

                <div class="row">
                    <div class="desc">Reset Zoom</div>
                    <div class="key">Ctrl/⌘ + 0</div>
                </div>

            </div>

            <div class="group">

                <div class="title">
                    Find
                </div>

                <div class="row">
                    <div class="desc">Find on Page</div>
                    <div class="key">Ctrl/⌘ + F</div>
                </div>

                <div class="row">
                    <div class="desc">Find Next Match</div>
                    <div class="key">Ctrl/⌘ + G</div>
                </div>
                
            </div> 
            
            <div class="group">

                <div class="title">
                    Window
                </div>

                <div class="row">
                    <div class="desc">Toggle Fullscreen</div>
                    <div class="key">F11 / Alt+Enter</div>
                </div>

                <div class="row">
                    <div class="desc">macOS Fullscreen</div>
                    <div class="key">Ctrl+Return</div>
                </div>

            </div>
                 
            <div class="group">

                <div class="title">
                    Notes
                </div>

                <div class="row">
                    <div class="desc">
                        CapsLock
                    </div>

                    <div class="key">
                        Shift + Letter
                    </div>
                </div>

            </div>

        </body>
        </html>
        """

        win = QDialog(self)

        win.setWindowTitle("Hotkeys")

        win.resize(520, 560)

        layout = QVBoxLayout(win)

        view = QWebEngineView()

        view.setHtml(html)

        layout.addWidget(view)

        win.exec()
        
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
        
    def show_find_bar(self):

        text, ok = QInputDialog.getText(
            self,
            "Find",
            "Find on page:"
        )

        if not ok or not text:
            return

        self._last_find_text = text

        view = self.tabs.currentWidget()

        if not view:
            return

        view.page().findText("")
        view.page().findText(text)


    def find_next(self):

        if not getattr(self, "_last_find_text", None):
            return

        view = self.tabs.currentWidget()

        if not view:
            return

        view.page().findText(
            self._last_find_text
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
                    except Exception as e:
                        print("Error:", e)

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
    palette.setColor(QPalette.Highlight, QColor("#A855F7"))
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
