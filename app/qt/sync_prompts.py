"""Thread-safe modal prompts for playback worker threads."""

from __future__ import annotations

from PySide6.QtCore import Q_ARG, QMetaObject, QObject, Qt, QThread, Slot
from PySide6.QtWidgets import QApplication, QWidget

from app.qt.dialogs import prompt_email_code as _prompt_email_code_dialog


class _PromptService(QObject):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._parent = parent
        self._result: str | None = None

    @Slot(str, str)
    def _ask_email_code(self, email: str, selector: str) -> None:
        if not email.strip():
            self._result = None
            return
        self._result = _prompt_email_code_dialog(
            self._parent,
            email=email,
            selector=selector,
        )


_service: _PromptService | None = None


def install_prompt_service(parent: QWidget | None) -> None:
    global _service
    _service = _PromptService(parent)


def prompt_email_code_blocking(*, email: str, selector: str = "") -> str | None:
    if not email.strip():
        return None
    if _service is None:
        return None
    app = QApplication.instance()
    if app is None:
        return None
    if QThread.currentThread() == app.thread():
        return _prompt_email_code_dialog(_service._parent, email=email, selector=selector)
    _service._result = None
    QMetaObject.invokeMethod(
        _service,
        "_ask_email_code",
        Qt.ConnectionType.BlockingQueuedConnection,
        Q_ARG(str, email or ""),
        Q_ARG(str, selector or ""),
    )
    return _service._result
