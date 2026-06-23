"""Qt modal dialogs."""

from __future__ import annotations

from enum import Enum

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QWidget,
)

from app.qt.dialog_buttons import (
    BTN_CANCEL,
    BTN_CLOSE,
    BTN_NO,
    BTN_OK,
    BTN_YES,
    close_button_box,
    ok_cancel_button_box,
)
from app.qt.labels import muted_label
from app.qt.widgets.base_dialog import BaseAppDialog


class PickerInsertMode(str, Enum):
    CLICK = "click"
    VISIBLE = "visible"
    HOVER = "hover"
    RAW = "raw"


def alert(parent: QWidget | None, title: str, message: str) -> None:
    box = QMessageBox(parent)
    box.setWindowTitle(title)
    box.setText(message)
    box.setIcon(QMessageBox.Icon.Warning)
    box.addButton(BTN_OK, QMessageBox.ButtonRole.AcceptRole)
    box.exec()


def confirm(parent: QWidget | None, title: str, message: str) -> bool:
    box = QMessageBox(parent)
    box.setWindowTitle(title)
    box.setText(message)
    box.setIcon(QMessageBox.Icon.Question)
    yes = box.addButton(BTN_YES, QMessageBox.ButtonRole.YesRole)
    no = box.addButton(BTN_NO, QMessageBox.ButtonRole.NoRole)
    box.setDefaultButton(no)
    box.exec()
    return box.clickedButton() == yes


def prompt_text(
    parent: QWidget | None,
    title: str,
    label: str,
    *,
    initial: str = "",
) -> str | None:
    dialog = BaseAppDialog(parent, title=title, min_width=400)
    dialog.content_layout.addWidget(QLabel(label))
    edit = QLineEdit(initial)
    edit.setClearButtonEnabled(True)
    dialog.content_layout.addWidget(edit)

    buttons = dialog.add_ok_cancel()
    buttons.accepted.connect(dialog.accept)
    buttons.rejected.connect(dialog.reject)
    edit.returnPressed.connect(dialog.accept)
    edit.setFocus()

    if dialog.exec() != QDialog.DialogCode.Accepted:
        return None
    return edit.text()


def prompt_email_code(
    parent: QWidget | None,
    *,
    email: str,
    selector: str = "",
) -> str | None:
    dialog = BaseAppDialog(parent, title="Код из почты", min_width=400)
    dialog.content_layout.addWidget(QLabel("Код подтверждения отправлен на:"))

    email_label = QLabel(email.strip())
    email_label.setProperty("role", "dialog-title")
    email_label.setWordWrap(True)
    email_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
    dialog.content_layout.addWidget(email_label)

    dialog.content_layout.addWidget(QLabel("Введите код из письма на этот адрес:"))
    if selector.strip():
        preview = selector if len(selector) <= 100 else selector[:97] + "..."
        dialog.content_layout.addWidget(muted_label(f"Поле на странице: {preview}", word_wrap=True))

    code_edit = QLineEdit()
    code_edit.setPlaceholderText("Код из письма")
    code_edit.setClearButtonEnabled(True)
    dialog.content_layout.addWidget(code_edit)

    buttons = dialog.add_ok_cancel()
    buttons.accepted.connect(dialog.accept)
    buttons.rejected.connect(dialog.reject)
    code_edit.returnPressed.connect(dialog.accept)

    dialog.show()
    dialog.raise_()
    dialog.activateWindow()
    code_edit.setFocus()

    if dialog.exec() != QDialog.DialogCode.Accepted:
        return None
    return code_edit.text()


def prompt_http_auth(
    parent: QWidget | None,
    *,
    host: str,
    username: str = "",
    password: str = "",
) -> tuple[str, str, str] | None:
    dialog = BaseAppDialog(parent, title="HTTP-авторизация", min_width=420)
    dialog.add_hint(
        "Логин и пароль для HTTP Basic Auth (окно «Войти» в браузере).\n"
        "Данные сохраняются локально для указанного домена."
    )

    host_edit = QLineEdit(host)
    host_edit.setPlaceholderText("stage.example.com")
    dialog.content_layout.addWidget(QLabel("Сайт"))
    dialog.content_layout.addWidget(host_edit)

    user_edit = QLineEdit(username)
    user_edit.setPlaceholderText("Имя пользователя")
    dialog.content_layout.addWidget(QLabel("Имя пользователя"))
    dialog.content_layout.addWidget(user_edit)

    password_edit = QLineEdit(password)
    password_edit.setEchoMode(QLineEdit.EchoMode.Password)
    password_edit.setPlaceholderText("Пароль")
    dialog.content_layout.addWidget(QLabel("Пароль"))
    dialog.content_layout.addWidget(password_edit)

    buttons = dialog.add_ok_cancel()
    buttons.accepted.connect(dialog.accept)
    buttons.rejected.connect(dialog.reject)
    host_edit.returnPressed.connect(dialog.accept)
    user_edit.returnPressed.connect(dialog.accept)
    password_edit.returnPressed.connect(dialog.accept)
    host_edit.setFocus()

    if dialog.exec() != QDialog.DialogCode.Accepted:
        return None
    return host_edit.text().strip(), user_edit.text(), password_edit.text()


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
