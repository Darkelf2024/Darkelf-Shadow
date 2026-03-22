# --- Custom Icon helpers (ported from fixed2) ---
def make_icon(color=None, size=24):

    if color is None:
        color = "#34C759"

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
