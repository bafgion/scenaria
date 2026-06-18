"""Play results output."""

from __future__ import annotations

from PySide6.QtWidgets import QHBoxLayout, QPlainTextEdit, QPushButton, QVBoxLayout, QWidget

from app.qt.fonts import editor_font
from app.run_display import format_duration


class ResultsPanel(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._on_jump = None
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        header = QHBoxLayout()
        header.setContentsMargins(8, 4, 8, 0)
        header.addStretch()
        self.jump_btn = QPushButton("К ошибке")
        self.jump_btn.hide()
        self.jump_btn.clicked.connect(self._jump)
        header.addWidget(self.jump_btn)
        layout.addLayout(header)

        self.editor = QPlainTextEdit()
        self.editor.setReadOnly(True)
        self.editor.setProperty("role", "mono-panel")
        self.editor.setFont(editor_font())
        layout.addWidget(self.editor)

    def set_jump_handler(self, handler) -> None:
        self._on_jump = handler

    def _jump(self) -> None:
        if self._on_jump:
            self._on_jump()

    def show_results(self, payload: dict, *, has_failed_step: bool) -> None:
        duration_ms = int(payload.get("duration_ms", 0))
        lines = [
            f"Длительность: {format_duration(duration_ms)}",
            str(payload.get("comparison", "")),
        ]
        suite_cases = payload.get("suite_cases")
        if suite_cases:
            lines.append("")
            lines.append("Детали:")
            for case in suite_cases:
                path = case.get("path")
                label = path.name if hasattr(path, "name") else str(case.get("name", "?"))
                if case.get("success"):
                    lines.append(f"  OK  {label}")
                else:
                    brief = str(case.get("message", "")).splitlines()[0][:120]
                    lines.append(f"  FAIL {label}: {brief}")
        lines.extend(["", "Журнал:", *list(payload.get("log_lines", []))])
        self.editor.setPlainText("\n".join(lines))
        self.jump_btn.setVisible(has_failed_step and not suite_cases)
