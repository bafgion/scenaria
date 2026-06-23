"""Dialog before appending new steps to an existing scenario."""

from __future__ import annotations

from PySide6.QtWidgets import QCheckBox, QDialog, QLabel, QWidget

from app.qt.dialog_buttons import BTN_OK
from app.qt.widgets.base_dialog import BaseAppDialog


class ContinueRecordingDialog(BaseAppDialog):
    def __init__(self, parent: QWidget | None, *, step_count: int) -> None:
        super().__init__(parent, title="Продолжить запись", min_width=380)
        self.content_layout.addWidget(
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
        self.content_layout.addWidget(self._prepare)

        buttons = self.add_ok_cancel()
        ok_btn = next(btn for btn in buttons.buttons() if btn.text() == BTN_OK)
        ok_btn.setText("Начать дозапись")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

    def prepare_browser(self) -> bool:
        return self._prepare.isChecked()


def ask_continue_recording(parent: QWidget | None, *, step_count: int) -> bool | None:
    """Return prepare_browser flag, or None if cancelled."""
    dialog = ContinueRecordingDialog(parent, step_count=step_count)
    if dialog.exec() != QDialog.DialogCode.Accepted:
        return None
    return dialog.prepare_browser()
