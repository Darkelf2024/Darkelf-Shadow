import sys
import platform as _platform

from PySide6.QtCore import Qt, QPointF, QRectF

from PySide6.QtGui import (
    QIcon,
    QPixmap,
    QPainter,
    QColor,
    QPen,
    QBrush,
    QPolygonF,
    QPainterPath,
)

# --- Custom Icon helpers (ported from fixed2) ---
def make_icon(color=None, size=24):

    if color is None:
        color = "#A855F7"

    pix = QPixmap(size * 2, size * 2)
    pix.setDevicePixelRatio(2)
    pix.fill(Qt.transparent)

    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing)

    p.setBrush(QColor(color))
    p.setPen(Qt.PenStyle.NoPen)

    p.drawEllipse(4, 4, size-8, size-8)

    p.end()
    return QIcon(pix)

def make_nav_arrow_icon(direction: str, color: str, size: int) -> QIcon:

    pix = QPixmap(size * 2, size * 2)
    pix.setDevicePixelRatio(2)
    pix.fill(Qt.transparent)

    p = QPainter(pix)

    # crisp for geometric icons
    p.setRenderHint(QPainter.Antialiasing, False)

    p.setPen(Qt.NoPen)
    p.setBrush(QColor(color))

    cx = size / 2
    cy = size / 2

    length = size * 0.32
    thickness = size * 0.16

    if direction == "left":

        points = [
            QPointF(cx + thickness, cy - length),
            QPointF(cx - length, cy),
            QPointF(cx + thickness, cy + length)
        ]

    elif direction == "right":

        points = [
            QPointF(cx - thickness, cy - length),
            QPointF(cx + length, cy),
            QPointF(cx - thickness, cy + length)
        ]

    else:
        points = []

    if points:
        p.drawPolygon(QPolygonF(points))

    p.end()

    return QIcon(pix)

def make_reload_icon(color: str, size: int) -> QIcon:

    pix = QPixmap(size * 2, size * 2)
    pix.setDevicePixelRatio(2)
    pix.fill(Qt.transparent)

    p = QPainter(pix)

    p.setRenderHint(QPainter.Antialiasing, True)

    pen_width = max(2, int(size * 0.11))

    pen = QPen(
        QColor(color),
        pen_width,
        Qt.SolidLine,
        Qt.RoundCap,
        Qt.RoundJoin
    )

    p.setPen(pen)
    p.setBrush(Qt.NoBrush)

    margin = size * 0.18

    rect = QRectF(
        margin,
        margin,
        size - margin * 2,
        size - margin * 2
    )

    # standard reload arc
    p.drawArc(
        rect,
        45 * 16,
        300 * 16
    )

    # integrated arrow head
    tip_x = size * 0.76
    tip_y = size * 0.33

    arrow = QPolygonF([
        QPointF(tip_x, tip_y),
        QPointF(tip_x - size * 0.14, tip_y + size * 0.02),
        QPointF(tip_x - size * 0.03, tip_y + size * 0.14)
    ])

    p.setBrush(QColor(color))
    p.setPen(Qt.NoPen)

    p.drawPolygon(arrow)

    p.end()

    return QIcon(pix)

def make_house_icon(color: str, size: int) -> QIcon:

    pix = QPixmap(size * 2, size * 2)
    pix.setDevicePixelRatio(2)
    pix.fill(Qt.transparent)

    p = QPainter(pix)

    p.setRenderHint(QPainter.Antialiasing, True)

    c = QColor(color)

    linew = max(3, int(size * 0.13))

    p.setPen(QPen(
        c,
        linew,
        Qt.SolidLine,
        Qt.RoundCap,
        Qt.RoundJoin
    ))

    p.setBrush(Qt.NoBrush)

    cx = size / 2
    cy = size / 2

    scale = size / 26.0

    roof_w = 12 * scale
    roof_h = 8 * scale

    wall_w = 10 * scale
    wall_h = 9 * scale

    path = QPainterPath()

    path.moveTo(cx - roof_w, cy)
    path.lineTo(cx, cy - roof_h)
    path.lineTo(cx + roof_w, cy)

    path.lineTo(cx + wall_w, cy)
    path.lineTo(cx + wall_w, cy + wall_h)

    path.lineTo(cx - wall_w, cy + wall_h)
    path.lineTo(cx - wall_w, cy)

    path.closeSubpath()

    p.drawPath(path)

    p.end()

    return QIcon(pix)
    
def make_keyboard_icon(color: str, size: int = 18) -> QIcon:

    pix = QPixmap(size * 2, size * 2)
    pix.setDevicePixelRatio(2)
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

    pix = QPixmap(size * 2, size * 2)
    pix.setDevicePixelRatio(2)
    pix.fill(Qt.transparent)

    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing, True)

    accent = QColor(color)

    pen = QPen(
        accent,
        int(size * 0.08),
        Qt.PenStyle.SolidLine,
        Qt.PenCapStyle.RoundCap,
        Qt.PenJoinStyle.RoundJoin
    )

    p.setPen(pen)
    p.setBrush(Qt.NoBrush)

    for i, offset in enumerate([-0.15, 0, 0.15]):

        path = QPainterPath()

        cx = size * 0.5 + offset * size
        top = size * 0.16 + i * size * 0.05

        path.moveTo(cx, top)

        path.cubicTo(
            cx + size * 0.08,
            top + size * 0.04,
            cx - size * 0.08,
            top + size * 0.10,
            cx,
            top + size * 0.18
        )

        p.drawPath(path)

    cup_rect = QRectF(size*0.20, size*0.53, size*0.60, size*0.23)
    body_rect = QRectF(size*0.28, size*0.63, size*0.44, size*0.18)
    saucer_rect = QRectF(size*0.17, size*0.78, size*0.66, size*0.14)
    handle_rect = QRectF(size*0.68, size*0.62, size*0.18, size*0.22)

    p.drawArc(cup_rect, 0, 16 * 180)
    p.drawArc(body_rect, 0, 16 * 180)
    p.drawArc(saucer_rect, 0, 16 * 180)
    p.drawArc(handle_rect, 16 * 40, 16 * 175)

    p.end()

    return QIcon(pix)
    
def make_shield_icon(color, size=18):

    pix = QPixmap(size * 2, size * 2)
    pix.setDevicePixelRatio(2)
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

    pix = QPixmap(size * 2, size * 2)
    pix.setDevicePixelRatio(2)
    pix.fill(Qt.transparent)

    p = QPainter(pix)

    # turn AA back on for circles
    p.setRenderHint(QPainter.Antialiasing, True)

    accent = QColor(hex_color)
    black = QColor("#111412")

    # IMPORTANT FIX
    cx = size / 2
    cy = size / 2

    radius = size * 0.42
    border_width = max(2, int(size * 0.08))

    p.setPen(QPen(black, border_width))
    p.setBrush(QBrush(accent))

    p.drawEllipse(
        QRectF(
            cx - radius,
            cy - radius,
            radius * 2,
            radius * 2
        )
    )

    hub_r = size * 0.12

    p.setPen(Qt.NoPen)
    p.setBrush(QBrush(black))

    p.drawEllipse(
        QRectF(
            cx - hub_r,
            cy - hub_r,
            hub_r * 2,
            hub_r * 2
        )
    )

    # radiation blades
    blade_len = size * 0.30
    blade_w = size * 0.11

    p.setBrush(QBrush(black))
    p.setPen(Qt.NoPen)

    for i in range(3):

        p.save()

        p.translate(cx, cy)
        p.rotate(i * 120)

        polygon = QPolygonF([
            QPointF(-blade_w, -hub_r * 1.2),
            QPointF(blade_w,  -hub_r * 1.2),
            QPointF(blade_w * 0.55, -blade_len),
            QPointF(-blade_w * 0.55, -blade_len),
        ])

        p.drawPolygon(polygon)

        p.restore()
        
    p.end()

    return QIcon(pix)
    
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
