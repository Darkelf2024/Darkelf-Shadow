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
    QTimer, QPropertyAnimation, QThread, Signal
)

# --- Qt GUI ---
from PySide6.QtGui import (
    QAction, QIcon, QPixmap, QPainter, QColor,
    QPalette, QPen, QBrush, QPolygonF,
    QPainterPath, QFont
)

# --- Qt Widgets ---
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QLineEdit, QToolBar, QPushButton, QLabel,
    QWidget, QDialog, QTabWidget, QTabBar, QMessageBox, QToolButton,
    QProgressBar, QMenu, QWidgetAction, QGridLayout, QVBoxLayout,
    QHBoxLayout, QFileDialog, QProgressDialog, QInputDialog
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

devnull = open(os.devnull, 'w')
os.dup2(devnull.fileno(), sys.stderr.fileno())

# --- Custom Icon helpers (ported from fixed2) ---
def make_icon(color=None, size=24):

    if color is None:
        color = "#A855F7"

    pix = QPixmap(size, size)
    pix.fill(Qt.transparent)

    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing)

    p.setBrush(QColor(color))
    p.setPen(Qt.PenStyle.NoPen)

    p.drawEllipse(4, 4, size-8, size-8)

    p.end()
    return QIcon(pix)

def make_nav_arrow_icon(direction: str, color: str, size: int) -> QIcon:
    pix = QPixmap(size, size)
    pix.fill(Qt.GlobalColor.transparent)

    p = QPainter(pix)
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor(color))

    center = size / 2
    length = size * 0.19

    if direction == "left":
        points = [
            QPointF(center + length, center - length),
            QPointF(center - length, center),
            QPointF(center + length, center + length)
        ]
    elif direction == "right":
        points = [
            QPointF(center - length, center - length),
            QPointF(center + length, center),
            QPointF(center - length, center + length)
        ]
    else:
        points = []

    if points:
        polygon = QPolygonF(points)
        p.drawPolygon(polygon)

    p.end()
    return QIcon(pix)

def make_reload_icon(color: str, size: int) -> QIcon:
    pix = QPixmap(size, size)
    pix.fill(Qt.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing, True)
    pen_width = max(2, size // 16)
    margin = pen_width // 2 + 6
    radius = (size - 2 * margin) / 2
    center = size / 2
    start_angle_deg = 135
    span_angle_deg = 320
    rect = QRectF(center - radius, center - radius, 2 * radius, 2 * radius)
    pen = QPen(QColor(color), pen_width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
    p.setPen(pen)
    p.setBrush(Qt.NoBrush)
    p.drawArc(rect, int(start_angle_deg * 16), int(span_angle_deg * 16))
    p.end()
    return QIcon(pix)

def make_house_icon(color: str, size: int) -> QIcon:
    pix = QPixmap(size, size)
    pix.fill(Qt.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing, True)
    c = QColor(color)
    linew = max(2, int(size * 0.11))
    cx, cy = size / 2, size / 2
    scale = size / 42.0
    roof_w, roof_h = 20 * scale, 10 * scale
    wall_h, wall_w = 13 * scale, 16 * scale
    roof_peak = QPointF(cx, cy - roof_h)
    roof_left = QPointF(cx - roof_w / 2, cy)
    roof_right = QPointF(cx + roof_w / 2, cy)
    wall_top_left = QPointF(cx - wall_w / 2, cy)
    wall_top_right = QPointF(cx + wall_w / 2, cy)
    wall_bot_left = QPointF(cx - wall_w / 2, cy + wall_h)
    wall_bot_right = QPointF(cx + wall_w / 2, cy + wall_h)
    path = QPainterPath()
    path.moveTo(roof_left)
    path.lineTo(roof_peak)
    path.lineTo(roof_right)
    path.lineTo(wall_top_right)
    path.lineTo(wall_bot_right)
    path.lineTo(wall_bot_left)
    path.lineTo(wall_top_left)
    path.lineTo(roof_left)
    p.setPen(QPen(c, linew, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
    p.setBrush(Qt.NoBrush)
    p.drawPath(path)
    p.end()
    return QIcon(pix)

def make_zoom_icon(sign: str, color: str, size: int) -> QIcon:
    pix = QPixmap(size, size)
    pix.fill(Qt.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing)
    pen_width = max(2, size // 10)
    pen = QPen(QColor(color), pen_width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
    p.setPen(pen)
    center = size / 2
    length = size * 0.15
    if sign == "+":
        p.drawLine(QPointF(center - length, center), QPointF(center + length, center))
        p.drawLine(QPointF(center, center - length), QPointF(center, center + length))
    else:
        p.drawLine(QPointF(center - length, center), QPointF(center + length, center))
    p.end()
    return QIcon(pix)

def make_fullscreen_icon(color: str, size: int) -> QIcon:
    pix = QPixmap(size, size)
    pix.fill(Qt.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing, True)
    pen = QPen(QColor(color), max(2, size//10), Qt.SolidLine, Qt.RoundCap)
    p.setPen(pen)
    gap = size * 0.22
    span = size * 0.13
    p.drawLine(QPointF(gap, gap+span),      QPointF(gap, gap))
    p.drawLine(QPointF(gap, gap),           QPointF(gap+span, gap))
    p.drawLine(QPointF(size-gap, gap+span), QPointF(size-gap, gap))
    p.drawLine(QPointF(size-gap, gap),      QPointF(size-gap-span, gap))
    p.drawLine(QPointF(gap, size-gap-span), QPointF(gap, size-gap))
    p.drawLine(QPointF(gap, size-gap),      QPointF(gap+span, size-gap))
    p.drawLine(QPointF(size-gap, size-gap-span), QPointF(size-gap, size-gap))
    p.drawLine(QPointF(size-gap, size-gap),      QPointF(size-gap-span, size-gap))
    p.end()
    return QIcon(pix)
    
def make_keyboard_icon(color: str, size: int = 18) -> QIcon:

    pix = QPixmap(size, size)
    pix.fill(Qt.transparent)

    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing, True)

    pen = QPen(
        QColor(color),
        max(2, size // 10),
        Qt.SolidLine,
        Qt.RoundCap,
        Qt.RoundJoin
    )

    p.setPen(pen)
    p.setBrush(Qt.NoBrush)

    # keyboard outer shell
    rect = QRectF(
        size * 0.12,
        size * 0.22,
        size * 0.76,
        size * 0.56
    )

    p.drawRoundedRect(rect, 3, 3)

    # keys
    key_w = size * 0.09
    key_h = size * 0.09

    start_x = size * 0.22
    start_y = size * 0.34

    gap = size * 0.05

    for row in range(2):
        for col in range(5):

            x = start_x + col * (key_w + gap)
            y = start_y + row * (key_h + gap)

            p.drawRoundedRect(
                QRectF(x, y, key_w, key_h),
                1.5,
                1.5
            )

    # space bar
    p.drawRoundedRect(
        QRectF(
            size * 0.30,
            size * 0.58,
            size * 0.40,
            key_h
        ),
        1.5,
        1.5
    )

    p.end()

    return QIcon(pix)
    
def make_java_icon(color: str, size: int = 48) -> QIcon:
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing, True)

    accent = QColor(color)
    pen = QPen(accent, int(size * 0.08), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
    p.setPen(pen)
    p.setBrush(Qt.NoBrush)

    for i, offset in enumerate([-0.15, 0, 0.15]):
        path = QPainterPath()
        cx = size * 0.5 + offset * size
        top = size * 0.16 + i * size * 0.05
        path.moveTo(cx, top)
        path.cubicTo(cx + size*0.08, top + size*0.04, cx - size*0.08, top + size*0.10, cx, top + size*0.18)
        p.drawPath(path)

    cup_rect = QRectF(size*0.20, size*0.53, size*0.60, size*0.23)
    body_rect = QRectF(size*0.28, size*0.63, size*0.44, size*0.18)
    saucer_rect = QRectF(size*0.17, size*0.78, size*0.66, size*0.14)
    handle_rect = QRectF(size*0.68, size*0.62, size*0.18, size*0.22)
    p.drawArc(QRectF(int(cup_rect.x()), int(cup_rect.y()), int(cup_rect.width()), int(cup_rect.height())), 0, 16*180)
    p.drawArc(QRectF(int(body_rect.x()), int(body_rect.y()), int(body_rect.width()), int(body_rect.height())), 0, 16*180)
    p.drawArc(QRectF(int(saucer_rect.x()), int(saucer_rect.y()), int(saucer_rect.width()), int(saucer_rect.height())), 0, 16*180)
    p.drawArc(QRectF(int(handle_rect.x()), int(handle_rect.y()), int(handle_rect.width()), int(handle_rect.height())), int(16*40), int(16*175))
    p.end()
    return QIcon(pm)
    
def make_shield_icon(color, size=18):

    pix = QPixmap(size, size)
    pix.fill(Qt.transparent)

    painter = QPainter(pix)
    painter.setRenderHint(QPainter.Antialiasing)

    painter.setBrush(QColor(color))
    painter.setPen(Qt.NoPen)

    path = QPainterPath()

    w = size
    h = size

    path.moveTo(w * 0.5, h * 0.05)
    path.lineTo(w * 0.1, h * 0.25)
    path.lineTo(w * 0.1, h * 0.55)

    path.cubicTo(w * 0.1, h * 0.75, w * 0.3, h * 0.9, w * 0.5, h * 0.95)
    path.cubicTo(w * 0.7, h * 0.9, w * 0.9, h * 0.75, w * 0.9, h * 0.55)

    path.lineTo(w * 0.9, h * 0.25)
    path.closeSubpath()

    painter.drawPath(path)
    painter.end()

    return QIcon(pix)

def make_nuke_icon(hex_color: str, size: int) -> QIcon:
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing, True)
    accent = QColor(hex_color)
    black = QColor("#111412")
    cx, cy = size / 2, size / 2
    radius = size * 0.48
    border_width = int(size * 0.06)
    p.setPen(QPen(black, border_width))
    p.setBrush(QBrush(accent))
    p.drawEllipse(int(cx - radius), int(cy - radius), int(2 * radius), int(2 * radius))
    hub_r = size * 0.14
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QBrush(black))
    p.drawEllipse(int(cx - hub_r), int(cy - hub_r), int(2 * hub_r), int(2 * hub_r))
    p.setBrush(QBrush(black))
    for i in range(3):
        p.save()
        p.translate(cx, cy)
        p.rotate(i * 120)
        path = [
            QPointF(0, -hub_r * 1.35),
            QPointF(size * 0.18, -size * 0.35),
            QPointF(0, -radius),
            QPointF(-size * 0.18, -size * 0.35)
        ]
        polygon = QPolygonF(path)
        p.drawPolygon(polygon)
        p.restore()
    p.end()
    return QIcon(pm)
    
def detect_nav_platform():
    system = _platform.system()
    machine = _platform.machine().lower()

    if system == "Darwin":
        return "MacIntel"

    if system == "Windows":
        return "Win32"

    if system == "Linux":
        if "aarch64" in machine or "arm" in machine:
            return "Linux aarch64"
        if "x86_64" in machine or "amd64" in machine:
            return "Linux x86_64"
        return "Linux"

    return sys.platform


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

class HardenedWebPage(QWebEnginePage):
    def __init__(self, parent=None, profile=None, canvas_seed=None):
        view = parent
        if profile is not None:
            try: super().__init__(profile, view)
            except TypeError: super().__init__(view)
        else: super().__init__(view)
        self._canvas_seed = canvas_seed or (secrets.randbits(32) & 0xFFFFFFFF)
        self._parent_view = view
        prof = self.profile()
        self.interceptor = getattr(prof, "_darkelf_interceptor", None)
        self.inject_darkelf_letterboxing()
        self.hw_concurrency_spoof = secrets.choice([2, 4, 6, 8])
        self.inject_all_scripts()


    def inject_script(self, script_source, injection_point=None, subframes=True, name=None):
        scripts = self.scripts()
        # Remove old with same name if requested
        if name:
            for s in list(scripts.toList()):
                try:
                    if s.name() == name:
                        scripts.remove(s)
                except Exception as e:
                    print(e)
                    pass
        script_obj = QWebEngineScript()
        if name:
            script_obj.setName(name)
        script_obj.setSourceCode(script_source)
        script_obj.setInjectionPoint(injection_point or QWebEngineScript.DocumentCreation)
        script_obj.setRunsOnSubFrames(subframes)
        script_obj.setWorldId(QWebEngineScript.MainWorld)
        scripts.insert(script_obj)
        
    def inject_darkelf_letterboxing(self):
        script = """
        (() => {

            const detectPlatform = () => {
                try {
                    const p = navigator.platform.toLowerCase();
                    if (p.includes('mac')) return 'mac';
                    if (p.includes('win')) return 'windows';
                    if (p.includes('linux')) return 'linux';
                    return 'windows';
                } catch (e) {
                    return 'windows';
                }
            };

            const personas = [
                [1920,1080],
                [1536,864],
                [1440,900],
                [1366,768],
                [1280,720]
            ];

            const pickPersona = () => {
                try {
                    const p = personas[Math.floor(Math.random() * personas.length)];
                    return { width: p[0], height: p[1] };
                } catch(e) {
                    return { width: 1920, height: 1080 };
                }
            };

            const frameSizes = {
                windows: 140,
                mac: 80,
                linux: 120
            };

            const persona = pickPersona();

            const applyPatch = (win) => {
                try {

                    const platform = detectPlatform();
                    const frame = frameSizes[platform] || 140;

                    const width = persona.width;
                    const height = persona.height;

                    const safeDefine = (obj, key, getter) => {
                        try {
                            Object.defineProperty(obj, key, {
                                get: getter,
                                configurable: false
                            });
                        } catch(e) {}
                    };

                    safeDefine(win.screen, "width", () => width);
                    safeDefine(win.screen, "height", () => height);
                    safeDefine(win.screen, "availWidth", () => width);
                    safeDefine(win.screen, "availHeight", () => height);

                    safeDefine(win, "innerWidth", () => width);
                    safeDefine(win, "innerHeight", () => height);

                    safeDefine(win, "outerWidth", () => width);
                    safeDefine(win, "outerHeight", () => height + frame);

                } catch (e) {}
            };

            applyPatch(window);

            new MutationObserver((muts) => {
                for (const m of muts) {
                    m.addedNodes.forEach((node) => {
                        if (node.tagName === 'IFRAME') {
                            try {
                                const w = node.contentWindow;
                                applyPatch(w);
                            } catch (e) {}
                        }
                    });
                }
            }).observe(document, { childList: true, subtree: true });

            console.log('[DarkelfAI] Darkelf Letterboxing persona applied.');

        })();
        """

        self.inject_script(
            script,
            injection_point=QWebEngineScript.DocumentCreation,
            subframes=True
        )

    # --- Inject WebRTC block, geo override, and canvas noise all at DocumentCreation ---
    def stealth_webrtc_block(self):
        script = """
        (() => {
            const block = (target, key) => {
                try {
                    Object.defineProperty(target, key, {
                        get: () => undefined,
                        set: () => {},
                        configurable: false
                    });
                    delete target[key];
                } catch (e) {
                    // Silently ignore expected errors (e.g. non-configurable)
                }
            };

            const targets = [
                [window, 'RTCPeerConnection'],
                [window, 'webkitRTCPeerConnection'],
                [window, 'mozRTCPeerConnection'],
                [window, 'RTCDataChannel'],
                [navigator, 'mozRTCPeerConnection'],
                [navigator, 'mediaDevices']
            ];

            targets.forEach(([obj, key]) => block(obj, key));

            // Iframe defense
            new MutationObserver((muts) => {
                for (const m of muts) {
                    m.addedNodes.forEach((node) => {
                        if (node.tagName === 'IFRAME') {
                            try {
                                const w = node.contentWindow;
                                targets.forEach(([obj, key]) => block(w, key));
                                targets.forEach(([obj, key]) => block(w.navigator, key));
                            } catch (e) {}
                        }
                    });
                }
            }).observe(document, { childList: true, subtree: true });

            console.log('[DarkelfAI] WebRTC APIs neutralized.');
        })();
        """
        self.inject_script(script, injection_point=QWebEngineScript.DocumentCreation, subframes=True)
        
    def block_webrtc_sdp_logging(self):
        script = """
        (function() {
            if (!window.RTCPeerConnection) return;
            const OriginalRTCPeerConnection = window.RTCPeerConnection;
            window.RTCPeerConnection = function(...args) {
                const pc = new OriginalRTCPeerConnection(...args);
                const wrap = (method) => {
                    if (pc[method]) {
                        const original = pc[method].bind(pc);
                        pc[method] = async function(...mArgs) {
                            const result = await original(...mArgs);
                            if (result && result.sdp) {
                                result.sdp = result.sdp.replace(/(\\d{1,3}\\.){3}\\d{1,3}/g, "0.0.0.0");
                                result.sdp = result.sdp.replace(/ice-ufrag:.+\\r\\n/g, '');
                                result.sdp = result.sdp.replace(/ice-pwd:.+\\r\\n/g, '');
                            }
                            return result;
                        };
                    }
                };
                wrap("createOffer");
                wrap("createAnswer");
                return pc;
            };
        })();
        """
        self.inject_script(script, injection_point=QWebEngineScript.DocumentCreation, subframes=True)
        
    def inject_geolocation_override(self):
        script = """
        (function() {
            // Completely remove navigator.geolocation
            Object.defineProperty(navigator, "geolocation", {
                get: function () {
                    return undefined;
                },
                configurable: true
            });

            // Fake permissions API to return denied
            if (navigator.permissions && navigator.permissions.query) {
                const originalQuery = navigator.permissions.query;
                navigator.permissions.query = function(parameters) {
                    if (parameters.name === "geolocation") {
                        return Promise.resolve({ state: "denied" });
                    }
                    return originalQuery(parameters);
                };
            }
        })();
        """
        self.inject_script(script, injection_point=QWebEngineScript.DocumentCreation, subframes=True)

    def inject_canvas_protection(self):
        script = f"""
        (() => {{
            // Per-tab random seed, provided by Python
            const tabSeed = {self._canvas_seed};

            // Per-domain hash
            function hashString(str) {{
                let h = 2166136261;
                for (let i = 0; i < str.length; i++) {{
                    h ^= str.charCodeAt(i);
                    h = Math.imul(h, 16777619);
                }}
                return h >>> 0;
            }}
            const domainHash = hashString(location.hostname);

            // FINAL seed is combination of tabSeed and domainHash
            const seed = tabSeed ^ domainHash;

            function pixelNoise(seed, index) {{
                let x = seed ^ index;
                x = Math.imul(x ^ (x >>> 15), 0x85ebca6b);
                x = Math.imul(x ^ (x >>> 13), 0xc2b2ae35);
                x = x ^ (x >>> 16);
                return (x & 0xff);
            }}

            function applyNoise(imageData) {{
                const data = imageData.data;
                for (let i = 0; i < data.length; i++) {{
                    const n = (pixelNoise(seed, i) % 12) - 4;
                    data[i] = Math.min(255, Math.max(0, data[i] + n));
                }}
            }}

            function cloneImageData(ctx, src) {{
                const copy = ctx.createImageData(src.width, src.height);
                copy.data.set(src.data);
                return copy;
            }}

            function safePatch(proto, method, wrapper) {{
                const original = proto[method];
                Object.defineProperty(proto, method, {{
                    value: wrapper(original),
                    configurable: false,
                    writable: false
                }});
            }}

            // ---- Patch toDataURL ----
            safePatch(HTMLCanvasElement.prototype, 'toDataURL', function(original) {{
                return function() {{
                    try {{
                        const ctx = this.getContext('2d');
                        if (!ctx) return original.apply(this, arguments);

                        const w = this.width;
                        const h = this.height;
                        if (!w || !h) return original.apply(this, arguments);

                        const originalData = ctx.getImageData(0, 0, w, h);
                        const modifiedData = cloneImageData(ctx, originalData);
        
                        applyNoise(modifiedData);
                        ctx.putImageData(modifiedData, 0, 0);

                        const result = original.apply(this, arguments);

                        ctx.putImageData(originalData, 0, 0);

                        return result;
                    }} catch (e) {{
                        return original.apply(this, arguments);
                    }}
                }};
            }});

            // ---- Patch toBlob ----
            safePatch(HTMLCanvasElement.prototype, 'toBlob', function(original) {{
                return function(callback, type, quality) {{
                    try {{
                        const ctx = this.getContext('2d');
                        if (!ctx) return original.apply(this, arguments);

                        const w = this.width;
                        const h = this.height;
                        if (!w || !h) return original.apply(this, arguments);

                        const originalData = ctx.getImageData(0, 0, w, h);
                        const modifiedData = cloneImageData(ctx, originalData);
    
                        applyNoise(modifiedData);
                        ctx.putImageData(modifiedData, 0, 0);

                        original.call(this, function(blob) {{
                            ctx.putImageData(originalData, 0, 0);
                            callback(blob);
                        }}, type, quality);

                    }} catch (e) {{
                        return original.apply(this, arguments);
                    }}
                }};
            }});

            // ---- Patch getImageData (non-mutating/read) ----
            safePatch(CanvasRenderingContext2D.prototype, 'getImageData', function(original) {{
                return function(x, y, w, h) {{
                    const imageData = original.call(this, x, y, w, h);
                    applyNoise(imageData);
                    return imageData;
                }};
            }});

        }})();
        """
        self.inject_script(
            script,
            injection_point=QWebEngineScript.DocumentCreation,
            subframes=True)
                    
    def inject_fingerprint_hardware_protection(self):
        script = """
        (() => {
          // Always spoof deviceMemory as missing/undefined (shows N/A)
          try {
            Object.defineProperty(navigator, "deviceMemory", {
              get: () => undefined,
              configurable: true
            });
          } catch(e){}
          // Optional: continue randomizing hardwareConcurrency as before
          try {
            const cpuRand = Math.floor(Math.random() * 11) + 2;
            Object.defineProperty(navigator, "hardwareConcurrency", {
              get: () => cpuRand,
              configurable: true
            });
          } catch(e){}
        })();
        """
        self.inject_script(
            script,
            injection_point=QWebEngineScript.DocumentCreation,
            subframes=True)
                        
    def inject_webgl_fingerprint_per_domain(self):
        script = """
        (() => {
            function stringHash(s) {
                let h = 2166136261;
                for (let i = 0; i < s.length; i++) {
                    h ^= s.charCodeAt(i);
                    h += (h << 1) + (h << 4) + (h << 7) + (h << 8) + (h << 24);
                }
                return h >>> 0;
            }

            const SEED = stringHash(location.hostname);

            function seededRand(seed) {
                let a = seed + 0x6D2B79F5;
                a = Math.imul(a ^ a >>> 15, a | 1);
                a ^= a + Math.imul(a ^ a >>> 7, a | 61);
                return ((a ^ a >>> 14) >>> 0) / 4294967296;
            }

            // 🔥 REALISTIC GPU PROFILES
            const PLATFORM = navigator.platform.toLowerCase();

            const PROFILES = {
                mac: [
                    {
                        vendor: "Google Inc. (Apple)",
                        renderer: "ANGLE (Apple, ANGLE Metal Renderer: Apple M1, Unspecified Version)"
                    },
                    {
                        vendor: "Google Inc. (Apple)",
                        renderer: "ANGLE (Apple, ANGLE Metal Renderer: Apple M2, Unspecified Version)"
                    }
                ],
                win: [
                    {
                        vendor: "Google Inc. (Intel)",
                        renderer: "ANGLE (Intel, Intel(R) UHD Graphics 630 Direct3D11 vs_5_0 ps_5_0)"
                    },
                    {
                        vendor: "Google Inc. (NVIDIA)",
                        renderer: "ANGLE (NVIDIA, NVIDIA GeForce RTX 3060 Direct3D11 vs_5_0 ps_5_0)"
                    }
                ],
                linux: [
                    {
                        vendor: "Google Inc. (X.Org)",
                        renderer: "ANGLE (AMD, AMD Radeon RX 580 (POLARIS10), OpenGL 4.6)"
                    },
                    {
                        vendor: "Google Inc. (Mesa)",
                        renderer: "ANGLE (Intel, Mesa Intel(R) UHD Graphics 620 (KBL GT2), OpenGL 4.6)"
                    }
                ]
            };

            function pickProfile() {
                let list;

                if (PLATFORM.includes("mac")) list = PROFILES.mac;
                else if (PLATFORM.includes("win")) list = PROFILES.win;
                else list = PROFILES.linux;

                // deterministic per-domain but still realistic
                return list[SEED % list.length];
            }

            const PROFILE = pickProfile();

            function patchWebGL(ctxName) {
                let proto = window[ctxName] && window[ctxName].prototype;
                if (!proto) return;

                let _getParameter = proto.getParameter;

                proto.getParameter = function(param) {
                    switch (param) {
                        case 37445: return PROFILE.vendor;   // UNMASKED_VENDOR_WEBGL
                        case 37446: return PROFILE.renderer; // UNMASKED_RENDERER_WEBGL
                        case 7936:  return PROFILE.vendor;   // VENDOR
                        case 7937:  return PROFILE.renderer; // RENDERER
                        case 35724: return "WebGL GLSL ES 3.00 (OpenGL ES GLSL ES 3.0 Chromium)";
                        case 7938:  return "WebGL 2.0 (OpenGL ES 3.0 Chromium)";
                    }

                    return _getParameter.apply(this, arguments);
                };
            }

            patchWebGL('WebGLRenderingContext');
            patchWebGL('WebGL2RenderingContext');
        })();
        """
        self.inject_script(
            script,
            injection_point=QWebEngineScript.DocumentCreation,
            subframes=True)
            
    def inject_audio_randomized_defense(self):
        script = r"""
        (function() {

            function hashString(str) {
                let h = 2166136261 >>> 0;
                for (let i = 0; i < str.length; i++) {
                    h ^= str.charCodeAt(i);
                    h = Math.imul(h, 16777619);
                }
                return h >>> 0;
            }

            function mulberry32(a) {
                return function() {
                    var t = a += 0x6D2B79F5;
                    t = Math.imul(t ^ t >>> 15, t | 1);
                    t ^= t + Math.imul(t ^ t >>> 7, t | 61);
                    return ((t ^ t >>> 14) >>> 0) / 4294967296;
                }
            }

            const domain = location.hostname;
            const seed = hashString(domain);
            const rand = mulberry32(seed);

            const amplitude = 1e-7; // very small noise

            function perturb(data) {
                for (let i = 0; i < data.length; i++) {
                    data[i] += (rand() - 0.5) * amplitude;
                }
                return data;
            }

            const origGetChannelData = AudioBuffer.prototype.getChannelData;
            AudioBuffer.prototype.getChannelData = function() {
                const data = origGetChannelData.apply(this, arguments);
                return perturb(data);
            };

            if (AudioBuffer.prototype.copyFromChannel) {
                const origCopy = AudioBuffer.prototype.copyFromChannel;
                AudioBuffer.prototype.copyFromChannel = function(dest, channel, start) {
                    origCopy.apply(this, arguments);
                    perturb(dest);
                };
            }

        })();
        """
        self.inject_script(
            script,
            injection_point=QWebEngineScript.DocumentCreation,
            subframes=True)

    def inject_battery_defense(self):
        script = r"""
        if ("getBattery" in navigator) {
          navigator.getBattery = function() {
            return Promise.resolve({
              charging: true,
              chargingTime: 0,
              dischargingTime: Infinity,
              level: 1,
              addEventListener: function(){},
              removeEventListener: function(){},
              onchargingchange: null,
              onlevelchange: null
            });
          };
        }
        """
        self.inject_script(
            script,
            injection_point=QWebEngineScript.DocumentCreation,
            subframes=True)
            
    def inject_font_protection(self):
        script = r"""
        (function() {

            function hashString(str) {
                let h = 2166136261 >>> 0;
                for (let i = 0; i < str.length; i++) {
                    h ^= str.charCodeAt(i);
                    h = Math.imul(h, 16777619);
                }
                return h >>> 0;
            }

            function mulberry32(a) {
                return function() {
                    var t = a += 0x6D2B79F5;
                    t = Math.imul(t ^ t >>> 15, t | 1);
                    t ^= t + Math.imul(t ^ t >>> 7, t | 61);
                    return ((t ^ t >>> 14) >>> 0) / 4294967296;
                }
            }

            const seed = hashString(window.__darkelfSeed || location.hostname);

            const rand = mulberry32(seed);

            // ----- 1️⃣ Fake installed font set -----

            const commonFonts = [
                "Arial","Verdana","Tahoma","Times New Roman",
                "Courier New","Georgia","Trebuchet MS",
                "Comic Sans MS","Impact","Calibri"
            ];

            const fakeInstalled = new Set();

            commonFonts.forEach(font => {
                if (rand() > 0.4) { // randomized allowlist
                    fakeInstalled.add(font.toLowerCase());
                }
            });

            // Patch document.fonts.check()
            if (document.fonts && document.fonts.check) {
                const origCheck = document.fonts.check;
                document.fonts.check = function(str) {
                    const match = str.match(/^\d+px\s+["']?([^"']+)["']?/);
                    if (match) {
                        const font = match[1].toLowerCase();
                        return fakeInstalled.has(font);
                    }
                    return origCheck.apply(this, arguments);
                };
            }

            // ----- 2️⃣ Canvas text metric perturbation -----

            const amplitude = 0.01;

            const origMeasureText = CanvasRenderingContext2D.prototype.measureText;
            CanvasRenderingContext2D.prototype.measureText = function(text) {
                const metrics = origMeasureText.apply(this, arguments);

                const noise = (rand() - 0.5) * amplitude;

                // Proxy metrics object
                return new Proxy(metrics, {
                    get(target, prop) {
                        if (prop === "width") {
                            return target.width + noise;
                        }
                        return target[prop];
                    }
                });
            };

        })();
        """
        self.inject_script(
            script,
            injection_point=QWebEngineScript.DocumentCreation,
            subframes=True)
                                    
    def inject_resize_observer_suppressor(self):
        suppressor_js = """
        try {
          new ResizeObserver(() => {}).observe(document.body);
        } catch (e) {}
        window.addEventListener("error", function(e) {
          if (e && e.message && e.message.indexOf('ResizeObserver loop limit exceeded') > -1)
            e.preventDefault();
        }, true);
        """
        self.inject_script(suppressor_js, name="__darkelf_resize_observer_patch__")
                    
    def inject_hw_concurrency_spoof(self):
        script = """
        (() => {

            const values = [2,4,6,8];

            const hashHost = (host) => {
                let h = 0;
                for (let i = 0; i < host.length; i++) {
                    h = ((h << 5) - h) + host.charCodeAt(i);
                    h |= 0;
                }
                return Math.abs(h);
            };

            const getValue = () => {
                try {
                    const host = location.hostname || "default";
                    const idx = hashHost(host) % values.length;
                    return values[idx];
                } catch(e) {
                    return values[Math.floor(Math.random()*values.length)];
                }
            };

            const patch = (nav) => {
                try {

                    Object.defineProperty(nav, "hardwareConcurrency", {
                        get() { return getValue(); },
                        configurable: false,
                        enumerable: true
                    });

                    Object.defineProperty(Navigator.prototype, "hardwareConcurrency", {
                        get() { return getValue(); },
                        configurable: false,
                        enumerable: true
                    });

                } catch(e) {}
            };

            const apply = (win) => {
                try {

                    if (!win || win.__darkelf_hw_patch)
                        return;

                    win.__darkelf_hw_patch = true;

                    patch(win.navigator);

                } catch(e) {}
            };

            apply(window);

            new MutationObserver((muts) => {

                for (const m of muts) {

                    m.addedNodes.forEach((node) => {

                        if (!node.tagName)
                            return;

                        if (node.tagName.toLowerCase() === "iframe") {

                            try {
                                apply(node.contentWindow);
                            } catch(e) {}

                        }

                    });

                }

            }).observe(document,{childList:true,subtree:true});

            console.log("[DarkelfAI] hardwareConcurrency domain-randomized");

        })();
        """
        self.inject_script(script, injection_point=QWebEngineScript.DocumentCreation, subframes=True)

    def inject_iframe_environment_harmonizer(self):
        spoof = {
            "platform": detect_nav_platform(),
            "vendor": "Google Inc.",
            "userAgent": None,
            "deviceMemory": None,
            "languages": ["en-US", "en"],
            "language": "en-US",
            "maxTouchPoints": 0,
        }
        
        spoof_json = json.dumps(spoof)

        js = f"""
        (() => {{
          if (window.__darkelf_iframe_harmonizer) return;
          window.__darkelf_iframe_harmonizer = true;

          const SPOOF = {json.dumps(spoof)};
          try {{ SPOOF.userAgent = navigator.userAgent; }} catch(e) {{}}

          function def(obj, prop, getter) {{
            try {{
              Object.defineProperty(obj, prop, {{
                get: getter,
                configurable: true
              }});
            }} catch(e) {{}}
          }}

          function applyToWindow(w) {{
            if (!w || w.__darkelf_spoofed) return;

            try {{ w.__darkelf_spoofed = true; }} catch(e) {{}}

            try {{
              const nav = w.navigator;
              if (!nav) return;

              const proto = Object.getPrototypeOf(nav);

              def(proto,"platform",() => SPOOF.platform);
              def(proto,"vendor",() => SPOOF.vendor);
              def(proto,"userAgent",() => SPOOF.userAgent);
              def(proto,"deviceMemory",() => SPOOF.deviceMemory);
              def(proto,"languages",() => SPOOF.languages.slice());
              def(proto,"language",() => SPOOF.language);
              def(proto,"maxTouchPoints",() => SPOOF.maxTouchPoints);

            }} catch(e) {{}}
          }}

          applyToWindow(window);

        }})();
        """
        self.inject_script(js, injection_point=QWebEngineScript.DocumentCreation, subframes=True)
                
    def inject_stealth_chrome_environment(self):
        script = """
        (() => {

            // ---------- deterministic hash ----------
            const hashString = (str) => {
                let h = 0;
                for (let i = 0; i < str.length; i++) {
                    h = (h << 5) - h + str.charCodeAt(i);
                    h |= 0;
                }
                return Math.abs(h);
            };

            // ---------- seeded shuffle ----------
            const seededShuffle = (array, seed) => {
                let arr = array.slice();
                for (let i = arr.length - 1; i > 0; i--) {
                    seed = (seed * 9301 + 49297) % 233280;
                    const j = Math.floor((seed / 233280) * (i + 1));
                    [arr[i], arr[j]] = [arr[j], arr[i]];
                }
                return arr;
            };

            // ---------- PATCH: plugins ----------
            const patchPlugins = (nav, win) => {
                try {
                    if (!nav) return;

                    const host = (win.location && win.location.hostname) || "default";
                    const seed = hashString(host);

                    const basePlugins = [
                        { name: "Chrome PDF Plugin", filename: "internal-pdf-viewer" },
                        { name: "Chrome PDF Viewer", filename: "mhjfbmdgcfjbbpaeojofohoefgiehjai" },
                        { name: "Native Client", filename: "internal-nacl-plugin" }
                    ];

                    let plugins;

                    // 🔥 Modern Chrome behavior: sometimes empty
                    if (seed % 3 === 0) {
                        plugins = [];
                    } else {
                        plugins = seededShuffle(basePlugins, seed);

                        // Slight variation (2–3 plugins)
                        const cut = 2 + (seed % 2);
                        plugins = plugins.slice(0, cut);
                    }

                    // emulate PluginArray
                    plugins.length = plugins.length;
                    plugins.item = (i) => plugins[i];
                    plugins.namedItem = (name) =>
                        plugins.find(p => p.name === name);

                    Object.defineProperty(nav, 'plugins', {
                        get: () => plugins,
                        configurable: true
                    });

                    // keep mimeTypes consistent
                    Object.defineProperty(nav, 'mimeTypes', {
                        get: () => [],
                        configurable: true
                    });

                } catch (e) {}
            };

            const patchChromeRuntime = (win) => {
                try {
                    if (!win.chrome)
                        win.chrome = {};

                    if (!win.chrome.runtime) {
                        Object.defineProperty(win.chrome, 'runtime', {
                            get: () => ({}),
                            configurable: true
                        });
                    }
                } catch (e) {}
            };

            const patchPermissions = (nav) => {
                try {
                    if (nav.permissions && nav.permissions.query) {

                        const originalQuery = nav.permissions.query.bind(nav.permissions);

                        nav.permissions.query = function(parameters) {

                            if (parameters && parameters.name === 'notifications') {
                                return Promise.resolve({
                                    state: Notification.permission
                                });
                            }

                            return originalQuery(parameters);
                        };
                    }
                } catch (e) {}
            };

            const apply = (win) => {
                try {
                    if (!win || win.__darkelf_chrome_env)
                        return;

                    win.__darkelf_chrome_env = true;

                    patchPlugins(win.navigator, win); // ✅ updated
                    patchChromeRuntime(win);
                    patchPermissions(win.navigator);

                } catch (e) {}
            };

            // apply to main window
            apply(window);

            // observe iframes
            new MutationObserver((muts) => {
                for (const m of muts) {
                    m.addedNodes.forEach((node) => {
                        if (!node.tagName)
                            return;

                        if (node.tagName.toLowerCase() === "iframe") {
                            try {
                                const w = node.contentWindow;
                                apply(w);
                            } catch (e) {}
                        }
                    });
                }
            }).observe(document, { childList: true, subtree: true });

            console.log('[DarkelfAI] Chrome environment randomized per domain');

        })();
        """
        self.inject_script(script, injection_point=QWebEngineScript.DocumentCreation, subframes=True)
        
    def inject_youtube_js_spoof(self):
        script = """
        (() => {
            try {
                const host = location.hostname || "";

                const isYouTube =
                    host.includes("youtube.com") ||
                    host.includes("youtu.be") ||
                    host.includes("ytimg.com") ||
                    host.includes("googlevideo.com");

                if (!isYouTube) return;

                const UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko)";

                Object.defineProperty(navigator, "userAgent", {
                    get: () => UA,
                    configurable: true
                });

                Object.defineProperty(navigator, "appVersion", {
                    get: () => UA,
                    configurable: true
                });

                Object.defineProperty(navigator, "platform", {
                    get: () => "MacIntel",
                    configurable: true
                });

                Object.defineProperty(navigator, "vendor", {
                    get: () => "Apple Computer, Inc.",
                    configurable: true
                });

            } catch(e) {}
        })();
        """

        self.inject_script(
            script,
            injection_point=QWebEngineScript.DocumentCreation,
            subframes=True
        )
        
    def inject_global_chrome_spoof(self):
        system = platform.system()

        if system == "Darwin":
            platform_part = "Macintosh; Intel Mac OS X 10_15_7"

        elif system == "Windows":
            platform_part = "Windows NT 10.0; Win64; x64"

        elif system == "Linux":
            platform_part = "X11; Linux x86_64"

        else:
            platform_part = "X11; Linux x86_64"

        chrome_ua = (
            f"Mozilla/5.0 ({platform_part}) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/140.0.0.0 Safari/537.36"
        )

        # IMPORTANT:
        self.profile().setHttpUserAgent(chrome_ua)

        script = f"""
        (() => {{
            try {{
                const UA = "{chrome_ua}";

                Object.defineProperty(navigator, "userAgent", {{
                    get: () => UA,
                    configurable: true
                }});

                Object.defineProperty(navigator, "appVersion", {{
                    get: () => UA,
                    configurable: true
                }});

                Object.defineProperty(navigator, "vendor", {{
                    get: () => "Google Inc.",
                    configurable: true
                }});

                Object.defineProperty(navigator, "platform", {{
                    get: () => "{platform_part}",
                    configurable: true
                }});

            }} catch(e) {{}}
        }})();
        """

        self.inject_script(
            script,
            injection_point=QWebEngineScript.DocumentCreation,
            subframes=True
        )
        
    def inject_all_scripts(self):
        self.stealth_webrtc_block()
        self.block_webrtc_sdp_logging()
        self.inject_geolocation_override()
        self.inject_canvas_protection()
        self.inject_fingerprint_hardware_protection()
        self.inject_audio_randomized_defense()
        self.inject_battery_defense()
        self.inject_webgl_fingerprint_per_domain()
        self.inject_font_protection()
        self.inject_resize_observer_suppressor()
        self.inject_hw_concurrency_spoof()
        self.inject_iframe_environment_harmonizer()
        self.inject_stealth_chrome_environment()
        self.inject_youtube_js_spoof()
        self.inject_global_chrome_spoof()

    def acceptNavigationRequest(self, url, navtype, isMainFrame):
        if url.scheme() == "file":
            QMessageBox.warning(None, "Navigation blocked", "File URLs are blocked for privacy.")
            return False
        return super().acceptNavigationRequest(url, navtype, isMainFrame)

    def createWindow(self, _type):
        parent_view = getattr(self, "_parent_view", None)
        main_window = parent_view.window() if parent_view else None

        # If this page belongs to the main browser window
        if isinstance(main_window, DarkelfBrowser):

            # Create a proper Darkelf tab
            main_window._add_tab()

            # Return the page of the new tab
            view = main_window.tabs.currentWidget()
            return view.page()

        # fallback if not inside the main window
        view = QWebEngineView(parent_view)

        try:
            page = HardenedWebPage(view, self.profile())
        except TypeError:
            page = HardenedWebPage(view)

        view.setPage(page)
        page._parent_view = view

        try:
            page.fullScreenRequested.connect(view.window().handle_fullscreen)
        except Exception as e:
            print(e)
            pass

        view.show()

        if not hasattr(self, "_spawned_views"):
            self._spawned_views = []

        self._spawned_views.append(view)

        return page

class DownloadItem(QWidget):

    def __init__(self, download):
        super().__init__()

        self.download = download

        layout = QHBoxLayout(self)

        self.label = QLabel(download.downloadFileName())
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.cancel = QPushButton("Cancel")

        layout.addWidget(self.label)
        layout.addWidget(self.progress)
        layout.addWidget(self.cancel)

        self.cancel.clicked.connect(self._handle_click)

        download.receivedBytesChanged.connect(self.update_progress)
        download.totalBytesChanged.connect(self.update_progress)
        download.stateChanged.connect(self.handle_state)

    def update_progress(self):
        total = self.download.totalBytes()
        received = self.download.receivedBytes()

        if total <= 0:
            # Unknown file size → show animated busy bar
            self.progress.setRange(0, 0)
        else:
            percent = int((received / total) * 100)
            self.progress.setRange(0, 100)
            self.progress.setValue(percent)

    def handle_state(self, state):

        if state == QWebEngineDownloadRequest.DownloadCompleted:
            self.progress.setValue(100)
            self.cancel.setText("Done")

        elif state == QWebEngineDownloadRequest.DownloadCancelled:
            self.cancel.setText("Remove")

        elif state == QWebEngineDownloadRequest.DownloadInterrupted:
            self.cancel.setText("Failed")
            
    def _handle_click(self):

        state = self.download.state()

        if state == QWebEngineDownloadRequest.DownloadInProgress:
            self.download.cancel()
        else:
            self.setParent(None)
            self.deleteLater()

class DownloadShelf(QWidget):

    def __init__(self):
        super().__init__()

        self.layout = QVBoxLayout(self)

    def add_download(self, download):

        item = DownloadItem(download)
        self.layout.addWidget(item)

        item.destroyed.connect(self._check_empty)

    def _check_empty(self):

        if self.layout.count() == 0:
            self.hide()
            
def create_color_palette_menu(parent, callback):

    menu = QMenu(parent)

    # palette widget INSIDE the menu
    palette = QWidget(menu)

    grid = QGridLayout(palette)
    grid.setSpacing(2)
    grid.setContentsMargins(4,4,4,4)

    colors = [
        "#34C759",
        "#444444","#666666","#999999",
        "#ff4d4f","#ff7a45","#ffa940",
        "#ffd666","#73d13d","#36cfc9","#40a9ff",
        "#597ef7","#9254de","#f759ab","#bfbfbf",
        "#FFFFFF",   # white
        "#FFC0CB",   # baby pink
        "#00BFA6",   # teal
        "#FF6F61",   # coral
        "#8BC34A",   # light green
        "#FFB6C1",   # light pink
        "#FFD700",   # gold
        "#7B68EE",   # medium purple
        "#20B2AA"    # light sea green
    ]

    row = 0
    col = 0

    for color_hex in colors:

        btn = QPushButton()
        btn.setFixedSize(20,20)

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

        # important: capture color safely
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
    def __init__(self, profile, mini_ai, engine):
        super().__init__()
        
        self.accent_color = "#A855F7"

        self.setWindowTitle("")
        self.resize(1200, 800)

        # ✅ macOS FIX (PUT HERE)
        self.setUnifiedTitleAndToolBarOnMac(True)

        self.shared_profile = profile
        print("OffTheRecord:", self.shared_profile.isOffTheRecord())

        # ✅ SET THESE FIRST (before ANY use)
        self.easy = engine
        self.mini_ai = mini_ai
        self.mini_ai.ui = self

        print("Loaded network rules:", len(self.easy.network_rules))

        # -----------------------------
        # TABS
        # -----------------------------
        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.setMovable(True)
        self.tabs.setDocumentMode(False)  # 🔥 IMPORTANT

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
        self._download_dir = _safe_download_dir()
        self._downloaded_files: list[str] = []
        self._hook_secure_downloads()

        QApplication.instance().aboutToQuit.connect(self._wipe_download_traces)

        # -----------------------------
        # HOTKEYS
        # -----------------------------
        self.setup_hotkeys()

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
        self.zoom_in_action.setIcon(make_zoom_icon("+", c, 20))
        self.zoom_out_action.setIcon(make_zoom_icon("-", c, 20))
        self.full_action.setIcon(make_fullscreen_icon(c, 20))
        self.addtab_action.setIcon(make_icon(c, 20))
        self.java_action.setIcon(make_java_icon(c, 18))
        self.miniai_action.setIcon(make_shield_icon(c, 18))
        self.hotkey_action.setIcon(make_keyboard_icon(color.name(), 18))

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

                <div class="row">
                    <div class="desc">
                        Cursor can't be active in URL bar
                    </div>

                    <div class="key">
                        Hotkeys Disabled
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
        
        # Find on page
        find_action = QAction(self)
        find_action.setShortcut("Ctrl+F")
        find_action.triggered.connect(self.show_find_bar)
        self.addAction(find_action)

        # Find next match
        find_next_action = QAction(self)
        find_next_action.setShortcut("Ctrl+G")
        find_next_action.triggered.connect(self.find_next)
        self.addAction(find_next_action)
        
        # Focus URL
        focus_url_action = QAction(self)

        focus_url_action.setShortcut("Ctrl+L")

        focus_url_action.triggered.connect(
            lambda: self.addr.setFocus()
        )

        self.addAction(focus_url_action)


        # Next tab
        next_tab_action = QAction(self)

        next_tab_action.setShortcuts([
            "Ctrl+Tab",
            "Meta+]"
        ])

        next_tab_action.triggered.connect(
            lambda: self.tabs.setCurrentIndex(
                (self.tabs.currentIndex() + 1)
                % self.tabs.count()
            )
        )

        self.addAction(next_tab_action)


        # Previous tab
        prev_tab_action = QAction(self)

        prev_tab_action.setShortcuts([
            "Ctrl+Shift+Tab",
            "Meta+["
        ])

        prev_tab_action.triggered.connect(
            lambda: self.tabs.setCurrentIndex(
                (self.tabs.currentIndex() - 1)
                % self.tabs.count()
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
