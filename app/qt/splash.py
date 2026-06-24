"""Photoshop-style startup splash for Scenaria."""

from __future__ import annotations

import math

from PySide6.QtCore import QEasingCurve, QEventLoop, QPropertyAnimation, Qt, QTimer
from PySide6.QtGui import (
    QColor,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QRadialGradient,
)
from PySide6.QtWidgets import (
    QApplication,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from app.brand import BRAND_NAME, BRAND_TAGLINE
from app.qt.branding import brand_mark_pixmap
from app.qt.theme import COLOR_BRAND_ACCENT, COLOR_BRAND_GHERKIN, COLOR_MUTED, COLOR_TEXT
from app.version import app_version

_PANEL_W = 540
_PANEL_H = 372
_SHADOW_PAD = 14
_CORNER = 12

_SPLASH_STYLESHEET = f"""
QLabel[role="splash-title"] {{
    color: #f5f5f5;
    font-size: 30pt;
    font-weight: 300;
    letter-spacing: 2px;
}}
QLabel[role="splash-version"] {{
    color: {COLOR_MUTED};
    font-size: 8pt;
    letter-spacing: 1.6px;
}}
QLabel[role="splash-tagline"] {{
    color: #6e6e6e;
    font-size: 8pt;
}}
QLabel[role="splash-status"] {{
    color: {COLOR_TEXT};
    font-size: 8.5pt;
}}
QLabel[role="splash-percent"] {{
    color: {COLOR_MUTED};
    font-size: 8.5pt;
}}
QProgressBar {{
    background: transparent;
    border: none;
    min-height: 5px;
    max-height: 5px;
}}
QProgressBar::chunk {{
    background: transparent;
    border-radius: 2px;
}}
"""


class _GlowLogo(QWidget):
    """Brand mark on a soft radial halo."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedSize(128, 128)
        self._phase = 0.0
        self._mark = brand_mark_pixmap(72)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(40)

    def _tick(self) -> None:
        self._phase = (self._phase + 0.07) % (2 * math.pi)
        self.update()

    def stop_animation(self) -> None:
        self._timer.stop()

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        center = self.rect().center()
        pulse = 0.5 + 0.5 * math.sin(self._phase)
        radius = 54 + pulse * 4

        halo = QRadialGradient(center, radius)
        halo.setColorAt(0.0, QColor(94, 200, 242, int(55 + pulse * 25)))
        halo.setColorAt(0.45, QColor(9, 71, 113, int(40 + pulse * 15)))
        halo.setColorAt(1.0, QColor(9, 71, 113, 0))
        painter.setBrush(halo)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(center, int(radius), int(radius))

        ring = QRadialGradient(center, 46)
        ring.setColorAt(0.85, QColor(255, 255, 255, 0))
        ring.setColorAt(0.95, QColor(94, 200, 242, 35))
        ring.setColorAt(1.0, QColor(94, 200, 242, 0))
        painter.setBrush(ring)
        painter.drawEllipse(center, 46, 46)

        if not self._mark.isNull():
            x = (self.width() - self._mark.width()) // 2
            y = (self.height() - self._mark.height()) // 2
            painter.drawPixmap(x, y, self._mark)


class _SplashProgress(QWidget):
    """Thin gradient progress track with glow on the leading edge."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedHeight(5)
        self._value = 0

    def progress_value(self) -> int:
        return self._value

    def set_progress_value(self, value: int) -> None:
        self._value = max(0, min(100, int(value)))
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        track = self.rect().adjusted(0, 1, 0, -1)
        track_path = QPainterPath()
        track_path.addRoundedRect(track, 2, 2)
        painter.fillPath(track_path, QColor("#2a2a2a"))

        if self._value <= 0:
            return

        fill_w = max(6, int(track.width() * self._value / 100))
        fill = track.adjusted(0, 0, -(track.width() - fill_w), 0)
        fill_path = QPainterPath()
        fill_path.addRoundedRect(fill, 2, 2)

        gradient = QLinearGradient(fill.left(), 0, fill.right(), 0)
        gradient.setColorAt(0.0, QColor(COLOR_BRAND_ACCENT))
        gradient.setColorAt(0.55, QColor("#4db8e8"))
        gradient.setColorAt(1.0, QColor(COLOR_BRAND_GHERKIN))
        painter.fillPath(fill_path, gradient)

        glow = QLinearGradient(fill.right() - 18, 0, fill.right(), 0)
        glow.setColorAt(0.0, QColor(255, 255, 255, 0))
        glow.setColorAt(1.0, QColor(255, 255, 255, 90))
        painter.fillPath(fill_path, glow)


class ScenariaSplash(QWidget):
    """Frameless branded splash with status line and progress."""

    def __init__(self) -> None:
        super().__init__(
            None,
            Qt.WindowType.SplashScreen
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint,
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setFixedSize(_PANEL_W + _SHADOW_PAD * 2, _PANEL_H + _SHADOW_PAD * 2)
        self.setStyleSheet(_SPLASH_STYLESHEET)

        panel = QWidget(self)
        panel.setObjectName("splashPanel")
        panel.setGeometry(_SHADOW_PAD, _SHADOW_PAD, _PANEL_W, _PANEL_H)
        panel.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

        root = QVBoxLayout(panel)
        root.setContentsMargins(0, 4, 0, 0)
        root.setSpacing(0)

        body = QVBoxLayout()
        body.setContentsMargins(40, 30, 40, 26)
        body.setSpacing(0)

        logo_row = QHBoxLayout()
        logo_row.addStretch(1)
        self._logo = _GlowLogo(panel)
        logo_row.addWidget(self._logo)
        logo_row.addStretch(1)
        body.addLayout(logo_row)
        body.addSpacing(10)

        title = QLabel(BRAND_NAME.upper(), alignment=Qt.AlignmentFlag.AlignCenter)
        title.setProperty("role", "splash-title")
        body.addWidget(title)

        version = QLabel(f"VERSION {app_version()}", alignment=Qt.AlignmentFlag.AlignCenter)
        version.setProperty("role", "splash-version")
        body.addWidget(version)
        body.addSpacing(34)

        status_row = QHBoxLayout()
        status_row.setSpacing(12)
        self._status = QLabel("Запуск…")
        self._status.setProperty("role", "splash-status")
        status_row.addWidget(self._status, 1)
        self._percent = QLabel("0%")
        self._percent.setProperty("role", "splash-percent")
        self._percent.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        status_row.addWidget(self._percent)
        body.addLayout(status_row)
        body.addSpacing(10)

        self._progress = _SplashProgress(panel)
        body.addWidget(self._progress)
        body.addSpacing(18)

        tagline = QLabel(BRAND_TAGLINE, alignment=Qt.AlignmentFlag.AlignCenter)
        tagline.setProperty("role", "splash-tagline")
        body.addWidget(tagline)

        root.addLayout(body, 1)

        self._panel = panel
        self._fade_animation: QPropertyAnimation | None = None

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        panel_rect = self.rect().adjusted(_SHADOW_PAD, _SHADOW_PAD, -_SHADOW_PAD, -_SHADOW_PAD)
        for spread, alpha in ((10, 28), (6, 42), (3, 58)):
            shadow = panel_rect.adjusted(-spread, -spread + 2, spread, spread + 4)
            path = QPainterPath()
            path.addRoundedRect(shadow, _CORNER + spread // 2, _CORNER + spread // 2)
            painter.fillPath(path, QColor(0, 0, 0, alpha))

        panel_path = QPainterPath()
        panel_path.addRoundedRect(panel_rect, _CORNER, _CORNER)

        bg = QLinearGradient(panel_rect.topLeft(), panel_rect.bottomLeft())
        bg.setColorAt(0.0, QColor("#2b2f33"))
        bg.setColorAt(0.42, QColor("#1f2124"))
        bg.setColorAt(1.0, QColor("#141618"))
        painter.fillPath(panel_path, bg)

        sheen = QLinearGradient(panel_rect.topLeft(), panel_rect.topRight())
        sheen.setColorAt(0.0, QColor(255, 255, 255, 0))
        sheen.setColorAt(0.5, QColor(255, 255, 255, 10))
        sheen.setColorAt(1.0, QColor(255, 255, 255, 0))
        top_band = panel_rect.adjusted(1, 1, -1, -panel_rect.height() + 90)
        painter.fillRect(top_band, sheen)

        accent_rect = panel_rect.adjusted(0, 0, 0, -(panel_rect.height() - 4))
        accent_grad = QLinearGradient(accent_rect.topLeft(), accent_rect.topRight())
        accent_grad.setColorAt(0.0, QColor("#3aa8d8"))
        accent_grad.setColorAt(0.45, QColor(COLOR_BRAND_ACCENT))
        accent_grad.setColorAt(1.0, QColor(COLOR_BRAND_GHERKIN))
        accent_path = QPainterPath()
        accent_path.addRoundedRect(accent_rect, _CORNER, _CORNER)
        clip = QPainterPath()
        clip.addRect(accent_rect)
        painter.fillPath(accent_path.intersected(clip), accent_grad)

        painter.setPen(QPen(QColor(255, 255, 255, 18), 1))
        painter.drawPath(panel_path)

        line_y = panel_rect.bottom() - 58
        painter.setPen(QPen(QColor(255, 255, 255, 12), 1))
        painter.drawLine(
            panel_rect.left() + 40,
            line_y,
            panel_rect.right() - 40,
            line_y,
        )

    def progress(self) -> int:
        return self._progress.progress_value()

    def set_stage(self, message: str, progress: int) -> None:
        self._status.setText(message)
        target = max(0, min(100, progress))
        self._percent.setText(f"{target}%")
        self._progress.set_progress_value(target)

        app = QApplication.instance()
        if app is not None:
            app.processEvents()

    def show_centered(self) -> None:
        screen = QApplication.primaryScreen()
        if screen is not None:
            geo = screen.availableGeometry()
            self.move(
                geo.x() + (geo.width() - self.width()) // 2,
                geo.y() + (geo.height() - self.height()) // 2,
            )
        self.show()
        self.raise_()
        self.activateWindow()

    def dismiss(self, *, fade_ms: int = 320) -> None:
        self._logo.stop_animation()
        effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(effect)
        animation = QPropertyAnimation(effect, b"opacity", self)
        animation.setDuration(fade_ms)
        animation.setStartValue(1.0)
        animation.setEndValue(0.0)
        animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        loop = QEventLoop()
        animation.finished.connect(loop.quit)
        animation.finished.connect(self.close)
        animation.start()
        self._fade_animation = animation
        loop.exec()
        self._fade_animation = None
