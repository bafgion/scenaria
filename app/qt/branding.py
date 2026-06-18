"""Application branding assets and window icon."""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QIcon, QImage, QPixmap
from PySide6.QtWidgets import QApplication

from app.paths import app_root, bundled_root
from app.brand import BRAND_DESCRIPTION, BRAND_NAME, BRAND_TAGLINE

_BRANDING_REL = Path("assets") / "branding"
_ICON_SIZES = (16, 20, 24, 32, 48, 64, 128, 256)
_cached_icon: QIcon | None = None


def branding_dir() -> Path:
    candidates = [
        bundled_root() / _BRANDING_REL,
        Path(__file__).resolve().parent.parent.parent / _BRANDING_REL,
        app_root() / _BRANDING_REL,
    ]
    for path in candidates:
        if path.is_dir():
            return path
    return candidates[0]


_MASTER_PNG = "icon-variant-b-monogram-su.png"
_SQUARE_PNG = "app-icon-square.png"
_MARK_PNG = "app-icon-mark.png"
_ICON_FALLBACK = "app.ico"


def _artwork_path() -> Path | None:
    folder = branding_dir()
    for name in (_SQUARE_PNG, _MASTER_PNG):
        path = folder / name
        if path.is_file():
            return path
    return None


def _scale_image(image: QImage, size: int) -> QPixmap:
    return QPixmap.fromImage(
        image.scaled(
            QSize(size, size),
            Qt.AspectRatioMode.IgnoreAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
    )


def _build_png_icon(path: Path) -> QIcon | None:
    image = QImage(str(path))
    if image.isNull():
        return None
    icon = QIcon()
    for size in _ICON_SIZES:
        pixmap = _scale_image(image, size)
        if pixmap.isNull():
            return None
        icon.addPixmap(pixmap)
    return icon


def app_icon() -> QIcon:
    global _cached_icon
    if _cached_icon is not None and not _cached_icon.isNull():
        return _cached_icon

    folder = branding_dir()
    fallback = folder / _ICON_FALLBACK
    if sys.platform == "win32" and fallback.is_file():
        ico = QIcon(str(fallback))
        if not ico.isNull():
            _cached_icon = ico
            return _cached_icon

    artwork = _artwork_path()
    if artwork is not None:
        png_icon = _build_png_icon(artwork)
        if png_icon is not None and not png_icon.isNull():
            _cached_icon = png_icon
            return _cached_icon

    fallback = folder / _ICON_FALLBACK
    if fallback.is_file():
        _cached_icon = QIcon(str(fallback))
        return _cached_icon

    _cached_icon = QIcon()
    return _cached_icon


def brand_mark_pixmap(size: int = 96) -> QPixmap:
    folder = branding_dir()
    for name in (_MARK_PNG, _SQUARE_PNG, _MASTER_PNG):
        path = folder / name
        if not path.is_file():
            continue
        image = QImage(str(path))
        if image.isNull():
            continue
        return _scale_image(image, size)
    return QPixmap()


def apply_app_branding(app: QApplication) -> None:
    icon = app_icon()
    if not icon.isNull():
        app.setWindowIcon(icon)
    app.setApplicationName(BRAND_NAME)
    app.setApplicationDisplayName(BRAND_NAME)


def apply_window_icon(window) -> None:
    icon = app_icon()
    if not icon.isNull():
        window.setWindowIcon(icon)


def about_text() -> str:
    return f"{BRAND_DESCRIPTION}\n{BRAND_TAGLINE}"
