#!/usr/bin/env python3
"""
Generate the Darkelf Shadow app logo and export it for every target:

  app/frontend/assets/darkelf.png   (512, window/taskbar + Linux)
  app/frontend/assets/darkelf.ico   (multi-res, Windows exe + installer)

Run from repo root:
  python tools/make_icons.py
"""
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt, QRectF, QPointF
from PySide6.QtGui import (
    QGuiApplication, QPixmap, QPainter, QColor, QPen, QBrush,
    QPainterPath, QPolygonF, QLinearGradient,
)

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
ASSETS = os.path.join(ROOT, "app", "frontend", "assets")


def render(size: int) -> QPixmap:
    s = size
    pix = QPixmap(s, s)
    pix.fill(Qt.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing, True)

    def sc(v):  # scale from a 256 design grid
        return v * s / 256.0

    # --- dark rounded tile ---
    tile = QRectF(sc(8), sc(8), sc(240), sc(240))
    g = QLinearGradient(0, 0, 0, s)
    g.setColorAt(0.0, QColor("#16121f"))
    g.setColorAt(1.0, QColor("#0a0b10"))
    p.setPen(Qt.NoPen)
    p.setBrush(g)
    p.drawRoundedRect(tile, sc(56), sc(56))
    p.setBrush(Qt.NoBrush)
    p.setPen(QPen(QColor("#2a2040"), sc(2)))
    p.drawRoundedRect(tile, sc(56), sc(56))

    cx = sc(128)

    # --- shield ---
    path = QPainterPath()
    path.moveTo(cx, sc(48))
    path.lineTo(sc(56), sc(84))
    path.lineTo(sc(56), sc(140))
    path.cubicTo(sc(56), sc(182), sc(92), sc(208), cx, sc(222))
    path.cubicTo(sc(164), sc(208), sc(200), sc(182), sc(200), sc(140))
    path.lineTo(sc(200), sc(84))
    path.closeSubpath()

    sg = QLinearGradient(sc(56), sc(48), sc(200), sc(222))
    sg.setColorAt(0.0, QColor("#C084FC"))
    sg.setColorAt(1.0, QColor("#7C3AED"))
    p.setPen(Qt.NoPen)
    p.setBrush(sg)
    p.drawPath(path)

    # subtle top highlight edge
    p.setPen(QPen(QColor(233, 213, 255, 150), sc(2)))
    p.setBrush(Qt.NoBrush)
    p.drawPath(path)

    # --- keyhole (negative space, tile-dark) ---
    p.setPen(Qt.NoPen)
    p.setBrush(QColor("#0a0b10"))
    kcx, kcy, r = cx, sc(118), sc(20)
    p.drawEllipse(QPointF(kcx, kcy), r, r)
    stem = QPolygonF([
        QPointF(kcx - sc(11), kcy + sc(8)),
        QPointF(kcx + sc(11), kcy + sc(8)),
        QPointF(kcx + sc(18), kcy + sc(58)),
        QPointF(kcx - sc(18), kcy + sc(58)),
    ])
    p.drawPolygon(stem)

    p.end()
    return pix


def render_mark(size: int) -> QPixmap:
    """Just the shield shape with a see-through keyhole cutout (no tile)."""
    s = size
    pix = QPixmap(s, s)
    pix.fill(Qt.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing, True)

    def sc(v):
        return v * s / 256.0

    # Shield fills most of the canvas (mark has no surrounding tile).
    cx = sc(128)
    path = QPainterPath()
    path.moveTo(cx, sc(20))
    path.lineTo(sc(34), sc(64))
    path.lineTo(sc(34), sc(146))
    path.cubicTo(sc(34), sc(204), sc(86), sc(236), cx, sc(250))
    path.cubicTo(sc(170), sc(236), sc(222), sc(204), sc(222), sc(146))
    path.lineTo(sc(222), sc(64))
    path.closeSubpath()

    sg = QLinearGradient(sc(34), sc(20), sc(222), sc(250))
    sg.setColorAt(0.0, QColor("#C084FC"))
    sg.setColorAt(1.0, QColor("#7C3AED"))
    p.setPen(Qt.NoPen)
    p.setBrush(sg)
    p.drawPath(path)

    p.setPen(QPen(QColor(233, 213, 255, 170), sc(2)))
    p.setBrush(Qt.NoBrush)
    p.drawPath(path)

    # Punch the keyhole transparent (true cutout).
    p.setCompositionMode(QPainter.CompositionMode_Clear)
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(0, 0, 0, 255))
    kcx, kcy, r = cx, sc(118), sc(24)
    p.drawEllipse(QPointF(kcx, kcy), r, r)
    stem = QPolygonF([
        QPointF(kcx - sc(13), kcy + sc(10)),
        QPointF(kcx + sc(13), kcy + sc(10)),
        QPointF(kcx + sc(21), kcy + sc(70)),
        QPointF(kcx - sc(21), kcy + sc(70)),
    ])
    p.drawPolygon(stem)
    p.setCompositionMode(QPainter.CompositionMode_SourceOver)

    p.end()
    return pix


def main() -> int:
    QGuiApplication(sys.argv)
    os.makedirs(ASSETS, exist_ok=True)

    master = render(512)
    png_path = os.path.join(ASSETS, "darkelf.png")
    master.save(png_path, "PNG")
    print("wrote", png_path)

    # Multi-resolution ICO via Pillow (best ICO writer).
    from PIL import Image
    ico_path = os.path.join(ASSETS, "darkelf.ico")
    img = Image.open(png_path).convert("RGBA")
    img.save(ico_path, sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    print("wrote", ico_path)

    # A couple of fixed sizes for Linux hicolor.
    for sz in (256, 128):
        render(sz).save(os.path.join(ASSETS, f"darkelf-{sz}.png"), "PNG")
        print("wrote", os.path.join(ASSETS, f"darkelf-{sz}.png"))

    # Cutout mark (shield shape only, transparent) — used for the window /
    # taskbar icon where it pops against a dark taskbar.
    mark_png = os.path.join(ASSETS, "darkelf-mark.png")
    render_mark(512).save(mark_png, "PNG")
    print("wrote", mark_png)
    for sz in (256, 128):
        render_mark(sz).save(os.path.join(ASSETS, f"darkelf-mark-{sz}.png"), "PNG")
    mark_ico = os.path.join(ASSETS, "darkelf-mark.ico")
    Image.open(mark_png).convert("RGBA").save(
        mark_ico, sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    )
    print("wrote", mark_ico)

    return 0


if __name__ == "__main__":
    sys.exit(main())
