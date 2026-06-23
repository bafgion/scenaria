"""Compact, collapsible Gherkin step hints."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QHBoxLayout, QToolButton, QVBoxLayout, QWidget

from app.gherkin_snippets import STEP_SNIPPETS
from app.qt.labels import caption_label
from app.qt.theme import COLOR_MUTED
from app.scenario_hints import hover_menu_gherkin_example


class GherkinHintsBar(QWidget):
    insert_template_clicked = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setProperty("role", "gherkin-hints")

        root = QVBoxLayout(self)
        root.setContentsMargins(6, 2, 6, 2)
        root.setSpacing(0)

        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(4)

        self._summary = caption_label(
            "Шаги сценария · для выпадающего меню: «навожу» перед «нажимаю» · Ctrl+Space"
        )
        row.addWidget(self._summary, stretch=1)

        template_btn = QToolButton()
        template_btn.setText("Шаблон")
        template_btn.setAutoRaise(True)
        template_btn.setProperty("toolbar", True)
        template_btn.setToolTip("Вставить шаблон сценария")
        template_btn.clicked.connect(self.insert_template_clicked.emit)
        row.addWidget(template_btn)

        self._toggle = QToolButton()
        self._toggle.setText("Справка")
        self._toggle.setAutoRaise(True)
        self._toggle.setProperty("toolbar", True)
        self._toggle.setToolTip("Показать примеры шагов")
        self._toggle.clicked.connect(self._toggle_details)
        row.addWidget(self._toggle)

        root.addLayout(row)

        details_lines = [
            f"<b>{s.label}</b> — {s.description} &nbsp; <span style='color:{COLOR_MUTED}'>{s.insert}</span>"
            for s in STEP_SNIPPETS
        ]
        details_lines.append(
            "<b>hover-меню</b> — пример:<br>"
            f"<span style='color:{COLOR_MUTED}'>{hover_menu_gherkin_example().replace(chr(10), '<br>')}</span>"
        )
        self._details = caption_label("<br>".join(details_lines))
        self._details.setTextFormat(Qt.TextFormat.RichText)
        self._details.setWordWrap(True)
        self._details.setProperty("padding", "top")
        self._details.setVisible(False)
        root.addWidget(self._details)

    def _toggle_details(self) -> None:
        visible = not self._details.isVisible()
        self._details.setVisible(visible)
        self._toggle.setText("Скрыть" if visible else "Справка")
