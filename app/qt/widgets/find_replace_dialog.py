"""Find and replace dialog for the Gherkin editor."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import (
    QCheckBox,
    QFormLayout,
    QLineEdit,
    QWidget,
)

from app.qt.dialogs import BTN_CLOSE
from app.qt.labels import muted_label
from app.qt.widgets.base_dialog import BaseAppDialog, dialog_action_button
from app.text_replace import find_matches, replace_all


class FindReplaceDialog(BaseAppDialog):
    def __init__(self, parent: QWidget | None, editor) -> None:
        super().__init__(parent, title="Найти и заменить", min_width=420)
        self.setWindowModality(Qt.WindowModality.NonModal)
        self._editor = editor
        self._last_index = 0

        form = QFormLayout()
        self._find = QLineEdit()
        self._find.setClearButtonEnabled(True)
        self._find.textChanged.connect(self._update_count)
        form.addRow("Найти:", self._find)

        self._replace = QLineEdit()
        self._replace.setClearButtonEnabled(True)
        form.addRow("Заменить на:", self._replace)
        self.content_layout.addLayout(form)

        self._case = QCheckBox("Учитывать регистр")
        self._case.toggled.connect(self._update_count)
        self._steps_only = QCheckBox("Только в шагах")
        self._steps_only.setToolTip("Не менять заголовки, теги и комментарии")
        self._steps_only.setChecked(True)
        self._steps_only.toggled.connect(self._update_count)
        self.content_layout.addWidget(self._case)
        self.content_layout.addWidget(self._steps_only)

        self._count_label = muted_label("")
        self.content_layout.addWidget(self._count_label)

        find_btn = dialog_action_button("Найти далее", default=True)
        find_btn.clicked.connect(self._find_next)
        replace_btn = dialog_action_button("Заменить")
        replace_btn.clicked.connect(self._replace_current)
        replace_all_btn = dialog_action_button("Заменить все")
        replace_all_btn.clicked.connect(self._replace_all)
        close_btn = dialog_action_button(BTN_CLOSE)
        close_btn.clicked.connect(self.reject)
        self.add_button_row(find_btn, replace_btn, replace_all_btn, close_btn)

        self._find.returnPressed.connect(self._find_next)
        self._replace.returnPressed.connect(self._replace_current)

    def showEvent(self, event) -> None:  # noqa: N802
        super().showEvent(event)
        cursor = self._editor.textCursor()
        if cursor.hasSelection():
            self._find.setText(cursor.selectedText().replace("\u2029", "\n"))
        self._find.setFocus()
        self._find.selectAll()
        self._update_count()

    def _opts(self) -> tuple[bool, bool]:
        return self._case.isChecked(), self._steps_only.isChecked()

    def _update_count(self) -> None:
        needle = self._find.text()
        case_sensitive, steps_only = self._opts()
        count = len(
            find_matches(
                self._editor.toPlainText(),
                needle,
                case_sensitive=case_sensitive,
                steps_only=steps_only,
            )
        )
        if not needle:
            self._count_label.setText("")
        elif count:
            self._count_label.setText(f"Найдено: {count}")
        else:
            self._count_label.setText("Совпадений нет")

    def _matches(self):
        return find_matches(
            self._editor.toPlainText(),
            self._find.text(),
            case_sensitive=self._case.isChecked(),
            steps_only=self._steps_only.isChecked(),
        )

    def _find_next(self) -> None:
        matches = self._matches()
        if not matches:
            self._update_count()
            return
        cursor = self._editor.textCursor()
        pos = cursor.position()
        if cursor.hasSelection():
            pos = max(cursor.anchor(), cursor.position())
        index = 0
        for i, match in enumerate(matches):
            if match.start >= pos:
                index = i
                break
        else:
            index = 0
        self._last_index = index
        match = matches[index]
        self._select_match(match.start, match.end)

    def _select_match(self, start: int, end: int) -> None:
        cursor = QTextCursor(self._editor.document())
        cursor.setPosition(start)
        cursor.setPosition(end, QTextCursor.MoveMode.KeepAnchor)
        self._editor.setTextCursor(cursor)
        self._editor.setFocus()

    def _replace_current(self) -> None:
        needle = self._find.text()
        if not needle:
            return
        matches = self._matches()
        if not matches:
            self._update_count()
            return
        cursor = self._editor.textCursor()
        pos = cursor.position()
        if cursor.hasSelection():
            pos = min(cursor.anchor(), cursor.position())
        current = None
        for match in matches:
            if match.start <= pos < match.end:
                current = match
                break
        if current is None:
            self._find_next()
            return
        edit = QTextCursor(self._editor.document())
        edit.beginEditBlock()
        edit.setPosition(current.start)
        edit.setPosition(current.end, QTextCursor.MoveMode.KeepAnchor)
        edit.insertText(self._replace.text())
        edit.endEditBlock()
        self._editor.setTextCursor(edit)
        self._find_next()
        self._update_count()

    def _replace_all(self) -> None:
        needle = self._find.text()
        if not needle:
            return
        case_sensitive, steps_only = self._opts()
        text, count = replace_all(
            self._editor.toPlainText(),
            needle,
            self._replace.text(),
            case_sensitive=case_sensitive,
            steps_only=steps_only,
        )
        if count:
            cursor = self._editor.textCursor()
            position = cursor.position()
            self._editor.setPlainText(text)
            restored = QTextCursor(self._editor.document())
            restored.setPosition(min(position, len(text)))
            self._editor.setTextCursor(restored)
        self._update_count()


def open_find_replace_dialog(parent: QWidget | None, editor) -> None:
    dialog = FindReplaceDialog(parent, editor)
    dialog.setWindowModality(Qt.WindowModality.NonModal)
    dialog.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
    dialog.show()
