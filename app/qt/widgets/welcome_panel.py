"""Minimal start page with quick start and recents."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QLineEdit, QPushButton, QVBoxLayout, QWidget

from app.qt.theme import COLOR_MUTED, COLOR_PRIMARY, COLOR_SUCCESS, COLOR_TEXT
from app.brand import BRAND_NAME

_CHECKLIST_STEPS = (
    (1, "Открыть проект"),
    (2, "Записать сценарий"),
    (3, "Запустить тест"),
)


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

        outer.addWidget(card, 0, Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
        outer.addStretch(2)

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
