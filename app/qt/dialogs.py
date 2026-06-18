"""Qt modal dialogs."""

from __future__ import annotations

from enum import Enum

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QVBoxLayout,
    QWidget,
)


class PickerInsertMode(str, Enum):
    CLICK = "click"
    VISIBLE = "visible"
    HOVER = "hover"
    RAW = "raw"


def alert(parent: QWidget | None, title: str, message: str) -> None:
    QMessageBox.warning(parent, title, message)


def confirm(parent: QWidget | None, title: str, message: str) -> bool:
    result = QMessageBox.question(
        parent,
        title,
        message,
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        QMessageBox.StandardButton.No,
    )
    return result == QMessageBox.StandardButton.Yes


def prompt_text(
    parent: QWidget | None,
    title: str,
    label: str,
    *,
    initial: str = "",
) -> str | None:
    text, ok = QInputDialog.getText(parent, title, label, text=initial)
    if not ok:
        return None
    return text


def prompt_email_code(
    parent: QWidget | None,
    *,
    email: str,
    selector: str = "",
) -> str | None:
    dialog = QDialog(parent)
    dialog.setWindowTitle("Код из почты")
    dialog.setWindowModality(Qt.WindowModality.ApplicationModal)
    dialog.setMinimumWidth(400)

    layout = QVBoxLayout(dialog)
    layout.addWidget(QLabel("Код подтверждения отправлен на:"))

    email_label = QLabel(email.strip())
    email_font = email_label.font()
    email_font.setBold(True)
    email_font.setPointSize(email_font.pointSize() + 2)
    email_label.setFont(email_font)
    email_label.setWordWrap(True)
    email_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
    layout.addWidget(email_label)

    layout.addWidget(QLabel("Введите код из письма на этот адрес:"))
    if selector.strip():
        preview = selector if len(selector) <= 100 else selector[:97] + "..."
        hint = QLabel(f"Поле на странице: {preview}")
        hint.setStyleSheet("color: palette(mid);")
        layout.addWidget(hint)

    code_edit = QLineEdit()
    code_edit.setPlaceholderText("Код из письма")
    code_edit.setClearButtonEnabled(True)
    layout.addWidget(code_edit)

    buttons = QDialogButtonBox(
        QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
    )
    buttons.accepted.connect(dialog.accept)
    buttons.rejected.connect(dialog.reject)
    layout.addWidget(buttons)
    code_edit.returnPressed.connect(dialog.accept)

    dialog.show()
    dialog.raise_()
    dialog.activateWindow()
    code_edit.setFocus()

    if dialog.exec() != QDialog.DialogCode.Accepted:
        return None
    return code_edit.text()


def pick_picker_insert_mode(parent: QWidget | None, selector: str) -> PickerInsertMode | None:
    preview = selector if len(selector) <= 120 else selector[:117] + "..."
    box = QMessageBox(parent)
    box.setWindowTitle("Вставка селектора")
    box.setText("Куда вставить выбранный селектор?")
    box.setInformativeText(preview)
    btn_click = box.addButton("нажимаю …", QMessageBox.ButtonRole.ActionRole)
    btn_visible = box.addButton("вижу …", QMessageBox.ButtonRole.ActionRole)
    btn_hover = box.addButton("навожу …", QMessageBox.ButtonRole.ActionRole)
    btn_raw = box.addButton("Только селектор", QMessageBox.ButtonRole.ActionRole)
    box.addButton("Отмена", QMessageBox.ButtonRole.RejectRole)
    box.exec()
    clicked = box.clickedButton()
    if clicked == btn_click:
        return PickerInsertMode.CLICK
    if clicked == btn_visible:
        return PickerInsertMode.VISIBLE
    if clicked == btn_hover:
        return PickerInsertMode.HOVER
    if clicked == btn_raw:
        return PickerInsertMode.RAW
    return None
