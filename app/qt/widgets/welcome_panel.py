"""Minimal start page with quick start and recents."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QLineEdit, QPushButton, QVBoxLayout, QWidget

from app.qt.theme import COLOR_MUTED, COLOR_PRIMARY
from app.brand import BRAND_NAME


class WelcomePanel(QWidget):
    open_project = Signal()
    create_feature = Signal()
    open_feature = Signal()
    open_recent_feature = Signal(object)
    open_recent_project = Signal(object)
    quick_start = Signal(str)
    insert_template = Signal()
    open_examples = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setProperty("role", "welcome")

        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 24, 24, 24)
        outer.setSpacing(0)
        outer.addStretch(1)

        card = QWidget(self)
        card.setProperty("role", "welcome-card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(6)

        title = QLabel(BRAND_NAME)
        title.setStyleSheet("font-size: 18pt; font-weight: 300;")
        layout.addWidget(title)

        subtitle = QLabel("1. Откройте сайт → 2. Запишите → 3. Запустите тест")
        subtitle.setProperty("muted", True)
        subtitle.setStyleSheet(f"color: {COLOR_MUTED}; margin-bottom: 8px;")
        layout.addWidget(subtitle)

        quick_row = QHBoxLayout()
        self._quick_url = QLineEdit()
        self._quick_url.setPlaceholderText("https://site.com")
        quick_row.addWidget(self._quick_url, stretch=1)
        quick_btn = QPushButton("Быстрый старт")
        quick_btn.setProperty("primary", True)
        quick_btn.setToolTip("Открыть браузер и начать запись")
        quick_btn.clicked.connect(self._emit_quick_start)
        quick_row.addWidget(quick_btn)
        layout.addLayout(quick_row)

        layout.addSpacing(12)
        section = QLabel("Начало работы")
        section.setStyleSheet("font-weight: 600; margin-top: 8px;")
        layout.addWidget(section)

        for text, handler in (
            ("Открыть примеры сценариев", self.open_examples.emit),
            ("Открыть папку…", self.open_project.emit),
            ("Новый сценарий", self.create_feature.emit),
            ("Открыть файл…", self.open_feature.emit),
            ("Вставить шаблон сценария", self.insert_template.emit),
        ):
            link = QLabel(f'<a href="#">{text}</a>')
            link.setTextFormat(Qt.TextFormat.RichText)
            link.setOpenExternalLinks(False)
            link.setStyleSheet(f"QLabel a {{ color: {COLOR_PRIMARY}; text-decoration: none; }}")
            link.linkActivated.connect(lambda _href, fn=handler: fn())
            layout.addWidget(link)

        self._recent_features_box = QVBoxLayout()
        self._recent_projects_box = QVBoxLayout()
        layout.addLayout(self._recent_features_box)
        layout.addLayout(self._recent_projects_box)

        outer.addWidget(card, 0, Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
        outer.addStretch(2)

    def _emit_quick_start(self) -> None:
        self.quick_start.emit(self._quick_url.text().strip())

    def refresh_recents(self, features: list[Path], projects: list[Path]) -> None:
        self._fill_recents(self._recent_features_box, "Недавние файлы", features, self.open_recent_feature)
        self._fill_recents(self._recent_projects_box, "Недавние проекты", projects, self.open_recent_project)

    def _fill_recents(self, box: QVBoxLayout, title: str, paths: list[Path], signal) -> None:
        while box.count():
            item = box.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        if not paths:
            return
        label = QLabel(title)
        label.setStyleSheet(f"color: {COLOR_MUTED}; font-weight: 600; margin-top: 12px;")
        box.addWidget(label)
        for path in paths[:6]:
            link = QLabel(f'<a href="#">{path.name}</a>')
            link.setToolTip(str(path))
            link.setTextFormat(Qt.TextFormat.RichText)
            link.setOpenExternalLinks(False)
            link.setStyleSheet(f"QLabel a {{ color: {COLOR_PRIMARY}; text-decoration: none; }}")
            link.linkActivated.connect(lambda _href, p=path: signal.emit(p))
            box.addWidget(link)
