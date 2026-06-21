"""Dialog before appending new steps to an existing scenario."""

from __future__ import annotations

from PySide6.QtWidgets import QCheckBox, QDialog, QLabel, QVBoxLayout, QWidget

from app.qt.dialogs import BTN_OK, ok_cancel_button_box


class ContinueRecordingDialog(QDialog):
    def __init__(self, parent: QWidget | None, *, step_count: int) -> None:
        super().__init__(parent)
        self.setWindowTitle("Продолжить запись")
        self.setMinimumWidth(380)

        root = QVBoxLayout(self)
        root.addWidget(
            QLabel(
                f"Новые шаги будут добавлены в конец сценария "
                f"(сейчас {step_count} шаг(ов)). Существующие шаги не изменятся."
            )
        )

        self._prepare = QCheckBox("Подготовить страницу (прогнать сценарий до последнего шага)")
        self._prepare.setToolTip(
            "Выполнить все шаги в открытом браузере, чтобы страница соответствовала концу сценария"
        )
        self._prepare.setChecked(step_count <= 40)
        root.addWidget(self._prepare)

        buttons = ok_cancel_button_box()
        ok_btn = next(btn for btn in buttons.buttons() if btn.text() == BTN_OK)
        ok_btn.setText("Начать дозапись")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def prepare_browser(self) -> bool:
        return self._prepare.isChecked()


def ask_continue_recording(parent: QWidget | None, *, step_count: int) -> bool | None:
    """Return prepare_browser flag, or None if cancelled."""
    dialog = ContinueRecordingDialog(parent, step_count=step_count)
    if dialog.exec() != QDialog.DialogCode.Accepted:
        return None
    return dialog.prepare_browser()
