"""Vector icons drawn with QPainter (consistent IDE style)."""

from __future__ import annotations

import math
from functools import lru_cache
from typing import Callable

from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QColor, QIcon, QPainter, QPainterPath, QPen, QPixmap

from app.qt.theme import COLOR_MUTED, COLOR_RECORDING, COLOR_SUCCESS, COLOR_TEXT

DrawFn = Callable[[QPainter, int, QColor], None]

SIZE_SM = 16
SIZE_MD = 20
SIZE_TB = 16
TOOLBAR_BTN = 28
_STROKE = 1.5
_ICON_PAD = 3


def _inner(size: int) -> int:
    return size - 2 * _ICON_PAD


def _stroke_pen(color: QColor, width: float = _STROKE) -> QPen:
    return QPen(
        color,
        width,
        Qt.PenStyle.SolidLine,
        Qt.PenCapStyle.RoundCap,
        Qt.PenJoinStyle.RoundJoin,
    )


def _make_icon(draw: DrawFn, size: int, color: QColor, *, padded: bool = False) -> QIcon:
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance()
    dpr = float(app.devicePixelRatio()) if app is not None else 1.0
    px = max(1, int(round(size * dpr)))
    pixmap = QPixmap(px, px)
    pixmap.setDevicePixelRatio(dpr)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    if padded:
        painter.translate(_ICON_PAD, _ICON_PAD)
        draw(painter, _inner(size), color)
    else:
        draw(painter, size, color)
    painter.end()
    return QIcon(pixmap)


@lru_cache(maxsize=256)
def _cached(name: str, color_hex: str, size: int, padded: bool) -> QIcon:
    color = QColor(color_hex)
    drawers: dict[str, DrawFn] = {
        "explorer": _draw_explorer,
        "panel": _draw_panel,
        "plus": _draw_plus,
        "close": _draw_close,
        "save": _draw_save,
        "feature": _draw_feature,
        "play": _draw_play,
        "stop": _draw_stop,
        "record": _draw_record,
        "pause": _draw_pause,
        "browser": _draw_browser,
        "browser_focus": _draw_browser_focus,
        "validate": _draw_validate,
        "apply": _draw_apply,
        "check": _draw_check,
        "url": _draw_url,
        "undo": _draw_undo,
        "log": _draw_log,
        "results": _draw_results,
        "quick_record": _draw_quick_record,
        "picker": _draw_picker,
        "search": _draw_search,
        "folder_missing": _draw_folder_missing,
    }
    return _make_icon(drawers[name], size, color, padded=padded)


def icon(name: str, *, color: str | None = None, size: int = SIZE_SM) -> QIcon:
    return _cached(name, color or COLOR_MUTED, size, False)


def toolbar_icon(name: str, *, size: int = SIZE_TB) -> QIcon:
    """Toolbar icons — brighter than sidebar defaults for readability."""
    return _cached(name, COLOR_TEXT, size, True)


def icon_size(size: int = SIZE_TB) -> QSize:
    return QSize(size, size)


# Lucide "house" icon (MIT) — https://lucide.dev/icons/house
_LUCIDE_HOUSE_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" '
    'stroke="{stroke}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
    '<path d="M15 21v-8a1 1 0 0 0-1-1h-4a1 1 0 0 0-1 1v8"/>'
    '<path d="M3 10a2 2 0 0 1 .709-1.528l7-5.999a2 2 0 0 1 2.582 0l7 5.999'
    'A2 2 0 0 1 21 10v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>'
    "</svg>"
)


@lru_cache(maxsize=32)
def _svg_icon(svg_template: str, color_hex: str, size: int) -> QIcon:
    from PySide6.QtSvg import QSvgRenderer
    from PySide6.QtWidgets import QApplication

    svg = svg_template.format(stroke=color_hex)
    renderer = QSvgRenderer(svg.encode("utf-8"))
    app = QApplication.instance()
    dpr = float(app.devicePixelRatio()) if app is not None else 1.0
    px = max(1, int(round(size * dpr)))
    pixmap = QPixmap(px, px)
    pixmap.setDevicePixelRatio(dpr)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    renderer.render(painter)
    painter.end()
    return QIcon(pixmap)


def _draw_explorer(p: QPainter, size: int, color: QColor) -> None:
    pen = QPen(color, 1.4)
    p.setPen(pen)
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawRoundedRect(3, 7, size - 6, size - 9, 1.5, 1.5)
    path = QPainterPath()
    path.moveTo(3, 7)
    path.lineTo(6, 4)
    path.lineTo(11, 4)
    path.lineTo(13, 7)
    p.drawPath(path)


def _draw_panel(p: QPainter, size: int, color: QColor) -> None:
    pen = QPen(color, 1.3)
    p.setPen(pen)
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawRect(3, 3, size - 6, size - 6)
    p.drawLine(3, size - 7, size - 3, size - 7)
    fill = QColor(color)
    fill.setAlpha(90)
    p.fillRect(4, size - 6, size - 7, 4, fill)


def _draw_plus(p: QPainter, size: int, color: QColor) -> None:
    pen = QPen(color, 1.8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
    p.setPen(pen)
    c = size / 2
    p.drawLine(c, 4, c, size - 4)
    p.drawLine(4, c, size - 4, c)


def _draw_close(p: QPainter, size: int, color: QColor) -> None:
    pen = QPen(color, 1.6, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
    p.setPen(pen)
    margin = 4
    p.drawLine(margin, margin, size - margin, size - margin)
    p.drawLine(size - margin, margin, margin, size - margin)


def _draw_save(p: QPainter, size: int, color: QColor) -> None:
    pen = _stroke_pen(color)
    p.setPen(pen)
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawRect(1, 0, size - 2, size - 1)
    p.drawRect(2, 0, size - 5, 2)
    p.drawLine(2, size - 3, size - 2, size - 3)
    p.drawLine(2, size - 1, size - 2, size - 1)


def _draw_feature(p: QPainter, size: int, color: QColor) -> None:
    """`.feature` file — document with folded corner and Gherkin lines."""
    pen = _stroke_pen(color, 1.4)
    p.setPen(pen)
    p.setBrush(Qt.BrushStyle.NoBrush)
    fold = 2
    body_w = size - fold - 1
    p.drawRect(1, 0, body_w, size - 1)
    fold_path = QPainterPath()
    fold_path.moveTo(1 + body_w, 0)
    fold_path.lineTo(size - 1, fold)
    fold_path.lineTo(1 + body_w, fold)
    fold_path.closeSubpath()
    p.drawPath(fold_path)
    line_pen = QPen(color, 1.2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
    p.setPen(line_pen)
    for index, y in enumerate((int(size * 0.42), int(size * 0.62), int(size * 0.82))):
        right = size - 2 if index < 2 else size - 3
        p.drawLine(2, y, right, y)


def _draw_play(p: QPainter, size: int, color: QColor) -> None:
    path = QPainterPath()
    path.moveTo(1, 0)
    path.lineTo(size - 1, size / 2)
    path.lineTo(1, size)
    path.closeSubpath()
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(color)
    p.drawPath(path)


def _draw_stop(p: QPainter, size: int, color: QColor) -> None:
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(color)
    inset = 0
    p.drawRoundedRect(inset, inset, size - inset * 2, size - inset * 2, 1.5, 1.5)


def _draw_record(p: QPainter, size: int, color: QColor) -> None:
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(color)
    inset = 1
    p.drawEllipse(inset, inset, size - inset * 2, size - inset * 2)


def _draw_pause(p: QPainter, size: int, color: QColor) -> None:
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(color)
    bar_w = 2
    gap = 2
    height = size
    center = size / 2
    left_x = int(center - gap / 2 - bar_w)
    right_x = int(center + gap / 2)
    p.drawRect(left_x, 0, bar_w, height)
    p.drawRect(right_x, 0, bar_w, height)


def _draw_browser(p: QPainter, size: int, color: QColor) -> None:
    """Browser window with title bar and content lines (not a globe/crosshair)."""
    pen = _stroke_pen(color, 1.3)
    p.setPen(pen)
    p.setBrush(Qt.BrushStyle.NoBrush)
    w = size - 1
    h = size - 1
    p.drawRoundedRect(0, 0, w, h, 1.4, 1.4)
    bar_h = max(2, round(h * 0.34))
    p.drawLine(0, bar_h, w, bar_h)
    line_pen = QPen(color, 1.1, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
    p.setPen(line_pen)
    y1 = bar_h + 2
    y2 = min(h - 1, bar_h + 4)
    if y1 < h:
        p.drawLine(2, y1, w - 2, y1)
    if y2 < h and y2 > y1:
        p.drawLine(2, y2, w - 3, y2)


def _draw_browser_focus(p: QPainter, size: int, color: QColor) -> None:
    """Browser window with corner arrow — bring to front."""
    _draw_browser(p, size, color)
    pen = QPen(color, 1.4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
    p.setPen(pen)
    p.drawLine(1, size - 1, 6, size - 6)
    p.drawLine(6, size - 6, 6, size - 3)
    p.drawLine(6, size - 6, 3, size - 6)


def _draw_validate(p: QPainter, size: int, color: QColor) -> None:
    pen = _stroke_pen(color)
    p.setPen(pen)
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawEllipse(0, 0, size, size)
    p.drawLine(2, int(size / 2), int(size / 2) - 1, size - 2)
    p.drawLine(int(size / 2) - 1, size - 2, size - 2, 2)


def _draw_apply(p: QPainter, size: int, color: QColor) -> None:
    pen = _stroke_pen(color)
    p.setPen(pen)
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawRect(1, 0, size - 2, size - 1)
    p.drawLine(2, size - 3, 4, size - 1)
    p.drawLine(4, size - 1, size - 2, 2)


def _draw_check(p: QPainter, size: int, color: QColor) -> None:
    pen = _stroke_pen(color, 1.6)
    p.setPen(pen)
    p.drawLine(1, int(size / 2) + 1, int(size / 2) - 1, size - 1)
    p.drawLine(int(size / 2) - 1, size - 1, size - 1, 1)


def _draw_url(p: QPainter, size: int, color: QColor) -> None:
    pen = _stroke_pen(color)
    p.setPen(pen)
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawArc(0, 1, size - 2, size - 2, 35 * 16, 200 * 16)
    p.drawLine(size - 3, 0, size - 1, 0)
    p.drawLine(size - 1, 0, size - 1, 2)


def _draw_undo(p: QPainter, size: int, color: QColor) -> None:
    """Counter-clockwise undo arc with arrowhead on the left."""
    pen = _stroke_pen(color, 1.5)
    p.setPen(pen)
    p.setBrush(Qt.BrushStyle.NoBrush)

    pad = 1.0
    x = y = pad
    w = h = size - 2 * pad
    cx = x + w / 2
    cy = y + h / 2
    rx = w / 2
    ry = h / 2

    start_deg = 180.0
    sweep = 285.0

    path = QPainterPath()
    path.arcMoveTo(x, y, w, h, start_deg)
    path.arcTo(x, y, w, h, start_deg, sweep)
    p.drawPath(path)

    angle = math.radians(start_deg)
    tip_x = cx + rx * math.cos(angle)
    tip_y = cy - ry * math.sin(angle)

    arrow = QPainterPath()
    arrow.moveTo(tip_x - 2.8, tip_y)
    arrow.lineTo(tip_x + 0.2, tip_y - 2.2)
    arrow.lineTo(tip_x + 0.2, tip_y + 2.2)
    arrow.closeSubpath()
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(color)
    p.drawPath(arrow)


def _draw_log(p: QPainter, size: int, color: QColor) -> None:
    pen = _stroke_pen(color)
    p.setPen(pen)
    step = max(2, size // 4)
    y = step
    while y < size - 1:
        p.drawLine(1, y, size - 1, y)
        y += step


def _draw_results(p: QPainter, size: int, color: QColor) -> None:
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(color)
    bar_w = 2
    gap = 2
    heights = (int(size * 0.35), int(size * 0.55), int(size * 0.85))
    total_w = bar_w * len(heights) + gap * (len(heights) - 1)
    x = (size - total_w) / 2
    bottom = size
    for height in heights:
        p.drawRect(int(x), int(bottom - height), bar_w, height)
        x += bar_w + gap


def _draw_quick_record(p: QPainter, size: int, color: QColor) -> None:
    """Browser window with a red REC dot — one-click open + record."""
    w = size - 0.5
    h = size - 0.5
    pen = _stroke_pen(color, 1.25)
    p.setPen(pen)
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawRoundedRect(0, 0, w, h, 1.3, 1.3)
    bar_h = max(2, round(h * 0.32))
    p.drawLine(0, bar_h, w, bar_h)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor(COLOR_RECORDING))
    cx = w / 2
    cy = bar_h + (h - bar_h) / 2
    r = max(1.6, min(2.4, (h - bar_h) / 2 - 0.6))
    p.drawEllipse(int(cx - r), int(cy - r), int(r * 2), int(r * 2))


def _draw_picker(p: QPainter, size: int, color: QColor) -> None:
    """Corner brackets + pointer — pick element on page (DevTools-style)."""
    pen = _stroke_pen(color, 1.45)
    p.setPen(pen)
    inset = 0.5
    edge = size - 1.5
    arm = max(2.5, size * 0.28)
    # top-left
    p.drawLine(int(inset), int(inset), int(inset + arm), int(inset))
    p.drawLine(int(inset), int(inset), int(inset), int(inset + arm))
    # top-right
    p.drawLine(int(edge - arm), int(inset), int(edge), int(inset))
    p.drawLine(int(edge), int(inset), int(edge), int(inset + arm))
    # bottom-left
    p.drawLine(int(inset), int(edge - arm), int(inset), int(edge))
    p.drawLine(int(inset), int(edge), int(inset + arm), int(edge))
    # bottom-right
    p.drawLine(int(edge - arm), int(edge), int(edge), int(edge))
    p.drawLine(int(edge), int(edge - arm), int(edge), int(edge))
    # pointer at bottom center
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(color)
    cx = size / 2
    tip_y = size - 0.5
    pointer = QPainterPath()
    pointer.moveTo(cx, tip_y)
    pointer.lineTo(cx - 2.2, tip_y - 4.2)
    pointer.lineTo(cx - 0.6, tip_y - 4.2)
    pointer.lineTo(cx - 0.6, tip_y - 6.8)
    pointer.lineTo(cx + 0.6, tip_y - 6.8)
    pointer.lineTo(cx + 0.6, tip_y - 4.2)
    pointer.lineTo(cx + 2.2, tip_y - 4.2)
    pointer.closeSubpath()
    p.drawPath(pointer)


def _draw_search(p: QPainter, size: int, color: QColor) -> None:
    pen = _stroke_pen(color, 1.4)
    p.setPen(pen)
    p.setBrush(Qt.BrushStyle.NoBrush)
    radius = size * 0.28
    center = size * 0.4
    p.drawEllipse(int(center - radius), int(center - radius), int(radius * 2), int(radius * 2))
    p.drawLine(int(center + radius * 0.65), int(center + radius * 0.65), size - 2, size - 2)


def _draw_folder_missing(p: QPainter, size: int, color: QColor) -> None:
    pen = QPen(color, 1.4)
    p.setPen(pen)
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawRoundedRect(2, 8, size - 4, size - 10, 1.5, 1.5)
    path = QPainterPath()
    path.moveTo(2, 8)
    path.lineTo(5, 5)
    path.lineTo(10, 5)
    path.lineTo(12, 8)
    p.drawPath(path)
    warn = QColor(color)
    warn.setAlpha(200)
    p.setPen(_stroke_pen(warn, 1.6))
    p.drawLine(5, size - 4, size - 5, size - 12)
    p.drawLine(size - 5, size - 4, 5, size - 12)


# Semantic shortcuts
def explorer_icon(*, active: bool = False) -> QIcon:
    return icon("explorer", color=COLOR_TEXT if active else COLOR_MUTED, size=SIZE_MD)


def panel_icon(*, active: bool = False) -> QIcon:
    return icon("panel", color=COLOR_TEXT if active else COLOR_MUTED, size=SIZE_MD)


def welcome_tab_icon() -> QIcon:
    return _svg_icon(_LUCIDE_HOUSE_SVG, COLOR_TEXT, 16)


def play_icon() -> QIcon:
    return _cached("play", COLOR_SUCCESS, SIZE_TB, True)


def stop_icon() -> QIcon:
    return _cached("stop", COLOR_RECORDING, SIZE_TB, True)


def pause_icon() -> QIcon:
    return _cached("pause", COLOR_TEXT, SIZE_TB, True)


def record_icon() -> QIcon:
    return _cached("record", COLOR_RECORDING, SIZE_TB, True)


def quick_record_icon() -> QIcon:
    """Browser frame + red dot (outline uses toolbar text color)."""
    return _cached("quick_record", COLOR_TEXT, SIZE_TB, True)


def scenario_file_icon(*, size: int = SIZE_TB) -> QIcon:
    return _cached("feature", COLOR_MUTED, size, True)


_EMPTY_ICON_NAMES: dict[str, str] = {
    "no_project": "explorer",
    "missing": "folder_missing",
    "no_files": "feature",
    "no_match": "search",
}


def catalog_empty_icon(kind: str, *, size: int = 32) -> QIcon:
    name = _EMPTY_ICON_NAMES.get(kind, "explorer")
    return _cached(name, COLOR_TEXT, size, True)
