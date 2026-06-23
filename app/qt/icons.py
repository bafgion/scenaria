"""IDE icons via Lucide SVG (MIT) — https://lucide.dev"""

from __future__ import annotations

from functools import lru_cache

from PySide6.QtCore import QRectF, QSize, Qt
from PySide6.QtGui import QIcon, QPainter, QPixmap

from app.qt.lucide_svgs import LUCIDE_BODIES, lucide_template
from app.qt.theme import COLOR_MUTED, COLOR_RECORDING, COLOR_SUCCESS, COLOR_TEXT

SIZE_SM = 16
SIZE_MD = 20
SIZE_TB = 16
TOOLBAR_BTN = 28
_ICON_PAD = 3


def _inner(size: int) -> int:
    return size - 2 * _ICON_PAD


@lru_cache(maxsize=512)
def _svg_icon(svg_template: str, color_hex: str, size: int, padded: bool) -> QIcon:
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
    draw_size = float(_inner(size) if padded else size)
    offset = float(_ICON_PAD if padded else 0)
    renderer.render(painter, QRectF(offset, offset, draw_size, draw_size))
    painter.end()
    return QIcon(pixmap)


@lru_cache(maxsize=512)
def _cached(name: str, color_hex: str, size: int, padded: bool) -> QIcon:
    body = LUCIDE_BODIES[name]
    return _svg_icon(lucide_template(body), color_hex, size, padded)


def icon(name: str, *, color: str | None = None, size: int = SIZE_SM) -> QIcon:
    return _cached(name, color or COLOR_MUTED, size, False)


def toolbar_icon(name: str, *, size: int = SIZE_TB) -> QIcon:
    """Toolbar icons — brighter than sidebar defaults for readability."""
    return _cached(name, COLOR_TEXT, size, True)


def icon_size(size: int = SIZE_TB) -> QSize:
    return QSize(size, size)


def explorer_icon(*, active: bool = False) -> QIcon:
    return icon("explorer", color=COLOR_TEXT if active else COLOR_MUTED, size=SIZE_MD)


def panel_icon(*, active: bool = False) -> QIcon:
    return icon("panel", color=COLOR_TEXT if active else COLOR_MUTED, size=SIZE_MD)


def welcome_tab_icon() -> QIcon:
    return _cached("house", COLOR_TEXT, 16, False)


def play_icon() -> QIcon:
    return _cached("play", COLOR_SUCCESS, SIZE_TB, True)


def stop_icon() -> QIcon:
    return _cached("stop", COLOR_RECORDING, SIZE_TB, True)


def pause_icon() -> QIcon:
    return _cached("pause", COLOR_TEXT, SIZE_TB, True)


def record_icon() -> QIcon:
    return _cached("record", COLOR_RECORDING, SIZE_TB, True)


def quick_record_icon() -> QIcon:
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
