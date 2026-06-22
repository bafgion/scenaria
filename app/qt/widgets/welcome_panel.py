"""Minimal start page with quick start and recents."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QEvent, Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from app.qt.theme import COLOR_MUTED, COLOR_PRIMARY, COLOR_SUCCESS, COLOR_TEXT
from app.brand import BRAND_NAME

_CHECKLIST_STEPS = (
    (1, "Открыть проект"),
    (2, "Записать сценарий"),
    (3, "Запустить тест"),
)


class _WelcomeScrollBody(QWidget):
    """Scroll content: compact card, vertically centered when space allows."""

    def __init__(self, scroll: QScrollArea, card: QWidget, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._scroll = scroll
        self._card = card
        self.setProperty("role", "welcome-scroll-body")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(0)
        layout.addStretch(1)

        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.addStretch(1)
        row.addWidget(card, 0, Qt.AlignmentFlag.AlignTop)
        row.addStretch(1)
        layout.addLayout(row, 0)
        layout.addStretch(1)

    def sync_height(self) -> None:
        viewport = self._scroll.viewport()
        if viewport is None:
            return
        margins = self.layout().contentsMargins()
        content_h = self._card.sizeHint().height() + margins.top() + margins.bottom()
        viewport_h = max(0, viewport.height())
        height = max(content_h, viewport_h)
        width = max(0, viewport.width())
        if self.minimumHeight() != height or self.width() != width:
            self.setMinimumHeight(height)
            self.resize(width, height)

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        self.sync_height()


class WelcomePanel(QWidget):
    open_project = Signal()
    create_feature = Signal()
    open_feature = Signal()
    open_recent_feature = Signal(object)
    open_recent_project = Signal(object)
    quick_start = Signal(str)
    insert_template = Signal()
    open_examples = Signal()
    checklist_step_clicked = Signal(int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setProperty("role", "welcome")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        scroll = QScrollArea(self)
        scroll.setProperty("role", "welcome-scroll")
        scroll.setWidgetResizable(False)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        card = QWidget()
        card.setProperty("role", "welcome-card")
        card.setMaximumWidth(520)
        card.setMinimumWidth(280)
        card.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(6)

        title = QLabel(BRAND_NAME)
        title.setStyleSheet("font-size: 18pt; font-weight: 300;")
        layout.addWidget(title)

        self._checklist_box = QWidget(card)
        self._checklist_box.setProperty("role", "welcome-checklist")
        checklist_layout = QVBoxLayout(self._checklist_box)
        checklist_layout.setContentsMargins(0, 4, 0, 8)
        checklist_layout.setSpacing(2)
        self._checklist_rows: dict[int, QLabel] = {}
        for step_id, label in _CHECKLIST_STEPS:
            row = QLabel()
            row.setTextFormat(Qt.TextFormat.RichText)
            row.setOpenExternalLinks(False)
            row.linkActivated.connect(
                lambda _href, sid=step_id: self.checklist_step_clicked.emit(sid)
            )
            checklist_layout.addWidget(row)
            self._checklist_rows[step_id] = row
        layout.addWidget(self._checklist_box)

        self._subtitle = QLabel("1. Откройте сайт → 2. Запишите → 3. Запустите тест")
        self._subtitle.setProperty("muted", True)
        self._subtitle.setStyleSheet(f"color: {COLOR_MUTED}; margin-bottom: 8px;")
        self._subtitle.hide()
        layout.addWidget(self._subtitle)

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

        self._scroll_body = _WelcomeScrollBody(scroll, card)
        scroll.setWidget(self._scroll_body)
        outer.addWidget(scroll)
        self._scroll = scroll
        scroll.viewport().installEventFilter(self)

    def eventFilter(self, obj, event) -> bool:  # noqa: N802
        if obj is self._scroll.viewport() and event.type() == QEvent.Type.Resize:
            self._scroll_body.sync_height()
        return super().eventFilter(obj, event)

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        self._scroll_body.sync_height()

    def showEvent(self, event) -> None:  # noqa: N802
        super().showEvent(event)
        self._scroll_body.sync_height()

    def _emit_quick_start(self) -> None:
        self.quick_start.emit(self._quick_url.text().strip())

    def quick_url(self) -> str:
        return self._quick_url.text().strip()

    def update_checklist(
        self,
        *,
        project_open: bool,
        recorded: bool,
        played_success: bool,
        dismissed: bool,
    ) -> None:
        if dismissed:
            self._checklist_box.hide()
            self._subtitle.hide()
            self._scroll_body.sync_height()
            return
        self._checklist_box.show()
        self._subtitle.hide()
        done_flags = (project_open, recorded, played_success)
        current_index = next((i for i, done in enumerate(done_flags) if not done), len(done_flags) - 1)
        for index, (step_id, label) in enumerate(_CHECKLIST_STEPS):
            row = self._checklist_rows[step_id]
            if done_flags[index]:
                icon = "✓"
                color = COLOR_SUCCESS
                weight = "normal"
                clickable = False
            elif index == current_index:
                icon = "→"
                color = COLOR_TEXT
                weight = "600"
                clickable = True
            else:
                icon = "○"
                color = COLOR_MUTED
                weight = "normal"
                clickable = False
            text = f'{icon} <span style="color:{color}; font-weight:{weight};">{label}</span>'
            if clickable:
                text = f'<a href="#" style="text-decoration:none; color:{color};">{text}</a>'
            row.setText(text)
        self._scroll_body.sync_height()

    def refresh_recents(self, features: list[Path], projects: list[Path]) -> None:
        self._fill_recents(self._recent_features_box, "Недавние файлы", features, self.open_recent_feature)
        self._fill_recents(self._recent_projects_box, "Недавние проекты", projects, self.open_recent_project)
        self._scroll_body.sync_height()

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
