"""Russian labels and factories for standard dialog button rows."""

from __future__ import annotations

from PySide6.QtWidgets import QDialogButtonBox

BTN_OK = "ОК"
BTN_CANCEL = "Отмена"
BTN_YES = "Да"
BTN_NO = "Нет"
BTN_CLOSE = "Закрыть"


def ok_cancel_button_box() -> QDialogButtonBox:
    box = QDialogButtonBox()
    box.addButton(BTN_OK, QDialogButtonBox.ButtonRole.AcceptRole)
    box.addButton(BTN_CANCEL, QDialogButtonBox.ButtonRole.RejectRole)
    return box


def close_button_box() -> QDialogButtonBox:
    box = QDialogButtonBox()
    box.addButton(BTN_CLOSE, QDialogButtonBox.ButtonRole.RejectRole)
    return box
