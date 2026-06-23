"""Structured play failure panel."""

from __future__ import annotations

from PySide6.QtWidgets import QHBoxLayout, QLabel, QPlainTextEdit, QPushButton, QVBoxLayout, QWidget

from app.qt.labels import caption_label


class ErrorPanel(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._on_jump = None
        self._on_retry = None
        self._screenshot_path: str | None = None
        self._trace_path: str | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        self._title = QLabel("Ошибка теста")
        self._title.setProperty("role", "error-title")
        layout.addWidget(self._title)

        self._step_label = QLabel("")
        layout.addWidget(self._step_label)

        self._selector_label = caption_label("")
        self._selector_label.setWordWrap(True)
        layout.addWidget(self._selector_label)

        self._message = QPlainTextEdit()
        self._message.setReadOnly(True)
        self._message.setMaximumHeight(120)
        layout.addWidget(self._message)

        buttons = QHBoxLayout()
        self._jump_btn = QPushButton("Перейти к шагу")
        self._jump_btn.clicked.connect(self._jump)
        buttons.addWidget(self._jump_btn)

        self._retry_btn = QPushButton("Повторить тест")
        self._retry_btn.clicked.connect(self._retry)
        buttons.addWidget(self._retry_btn)

        self._shot_btn = QPushButton("Скриншот")
        self._shot_btn.clicked.connect(self._open_screenshot)
        buttons.addWidget(self._shot_btn)

        self._trace_btn = QPushButton("Trace")
        self._trace_btn.clicked.connect(self._open_trace)
        buttons.addWidget(self._trace_btn)

        buttons.addStretch()
        layout.addLayout(buttons)

        self.clear()

    def set_handlers(self, *, on_jump, on_retry) -> None:
        self._on_jump = on_jump
        self._on_retry = on_retry

    def clear(self) -> None:
        self._step_label.setText("Ошибок пока нет")
        self._selector_label.setText("")
        self._message.setPlainText("")
        self._screenshot_path = None
        self._trace_path = None
        self._jump_btn.setEnabled(False)
        self._retry_btn.setEnabled(False)
        self._shot_btn.setEnabled(False)
        self._trace_btn.setEnabled(False)

    def show_failure(
        self,
        *,
        step_index: int,
        selector: str,
        message: str,
        screenshot_path: str | None = None,
        trace_path: str | None = None,
    ) -> None:
        self._title.setText("Ошибка теста")
        self._step_label.setText(f"Шаг {step_index}")
        self._selector_label.setText(selector or "—")
        brief = (message or "").splitlines()[0].strip()
        if "Call log:" in brief:
            brief = brief.split("Call log:", 1)[0].strip()
        if len(brief) > 240:
            brief = brief[:237] + "..."
        self._message.setPlainText(brief)
        self._screenshot_path = screenshot_path
        self._trace_path = trace_path
        self._jump_btn.setEnabled(True)
        self._retry_btn.setEnabled(True)
        self._shot_btn.setEnabled(bool(screenshot_path))
        self._trace_btn.setEnabled(bool(trace_path))

    def _jump(self) -> None:
        if self._on_jump:
            self._on_jump()

    def _retry(self) -> None:
        if self._on_retry:
            self._on_retry()

    def _open_screenshot(self) -> None:
        if not self._screenshot_path:
            return
        from PySide6.QtCore import QUrl
        from PySide6.QtGui import QDesktopServices

        QDesktopServices.openUrl(QUrl.fromLocalFile(self._screenshot_path))

    def _open_trace(self) -> None:
        if not self._trace_path:
            return
        from PySide6.QtCore import QUrl
        from PySide6.QtGui import QDesktopServices

        QDesktopServices.openUrl(QUrl.fromLocalFile(self._trace_path))
