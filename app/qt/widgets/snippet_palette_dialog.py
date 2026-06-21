"""Snippet palette: built-in + user snippets (Ctrl+Shift+Space)."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.feature_store import get_root
from app.qt.dialogs import BTN_CANCEL, BTN_OK, ok_cancel_button_box, prompt_text
from app.snippet_store import (
    PaletteSnippet,
    list_palette_snippets,
    resolve_placeholders,
)


class SnippetPaletteDialog(QDialog):
    def __init__(self, parent: QWidget | None, *, editor) -> None:
        super().__init__(parent)
        self._editor = editor
        self._selected: PaletteSnippet | None = None
        self.setWindowTitle("Палитра сниппетов")
        self.setMinimumSize(520, 420)

        root = QVBoxLayout(self)
        self._search = QLineEdit()
        self._search.setPlaceholderText("Поиск по названию или описанию…")
        self._search.textChanged.connect(self._refresh_list)
        root.addWidget(self._search)

        self._list = QListWidget()
        self._list.itemActivated.connect(self._accept_selection)
        self._list.currentItemChanged.connect(self._on_selection_changed)
        root.addWidget(self._list)

        self._hint = QLabel("")
        self._hint.setWordWrap(True)
        self._hint.setStyleSheet("color: #858585;")
        root.addWidget(self._hint)

        buttons = QHBoxLayout()
        insert_btn = QPushButton("Вставить")
        insert_btn.setDefault(True)
        insert_btn.clicked.connect(self._accept_selection)
        buttons.addWidget(insert_btn)
        buttons.addStretch()
        cancel = QPushButton(BTN_CANCEL)
        cancel.clicked.connect(self.reject)
        buttons.addWidget(cancel)
        root.addLayout(buttons)

        self._refresh_list()

    def _refresh_list(self) -> None:
        query = self._search.text()
        items = list_palette_snippets(get_root(), query=query)
        self._list.clear()
        for item in items:
            prefix = "★ " if item.kind == "user" else ""
            source = ""
            if item.kind == "user":
                source = " [проект]" if item.source == "project" else " [глобально]"
            label = f"{prefix}{item.label}{source}"
            row = QListWidgetItem(label)
            row.setData(Qt.ItemDataRole.UserRole, item)
            row.setToolTip(item.description or item.text)
            self._list.addItem(row)
        if self._list.count():
            self._list.setCurrentRow(0)

    def _on_selection_changed(self) -> None:
        item = self._list.currentItem()
        if item is None:
            self._hint.setText("")
            return
        snippet = item.data(Qt.ItemDataRole.UserRole)
        if isinstance(snippet, PaletteSnippet):
            lines = [snippet.description] if snippet.description else []
            if snippet.placeholders:
                lines.append("Плейсхолдеры: " + ", ".join(f"{{{{{name}}}}}" for name in snippet.placeholders))
            preview = snippet.text.replace("\n", " ↵ ")
            if len(preview) > 160:
                preview = preview[:157] + "…"
            lines.append(preview)
            self._hint.setText("\n".join(lines))

    def _current_snippet(self) -> PaletteSnippet | None:
        item = self._list.currentItem()
        if item is None:
            return None
        snippet = item.data(Qt.ItemDataRole.UserRole)
        return snippet if isinstance(snippet, PaletteSnippet) else None

    def _accept_selection(self) -> None:
        snippet = self._current_snippet()
        if snippet is None:
            return
        text = snippet.text
        if snippet.placeholders:
            values = _prompt_placeholders(self, snippet)
            if values is None:
                return
            text = resolve_placeholders(text, values)
        if snippet.kind == "builtin" and snippet.builtin is not None:
            self._editor._insert_snippet_at_cursor(snippet.builtin)
        else:
            self._editor.insert_snippet_block(text)
        self.accept()


def _prompt_placeholders(parent: QWidget, snippet: PaletteSnippet) -> dict[str, str] | None:
    if len(snippet.placeholders) == 1:
        name = snippet.placeholders[0]
        value = prompt_text(parent, "Подстановка", f"Значение для {{{{{name}}}}}:")
        if value is None:
            return None
        return {name: value}

    dialog = QDialog(parent)
    dialog.setWindowTitle("Подстановка значений")
    layout = QVBoxLayout(dialog)
    form = QFormLayout()
    edits: dict[str, QLineEdit] = {}
    for name in snippet.placeholders:
        edit = QLineEdit()
        edit.setClearButtonEnabled(True)
        form.addRow(f"{{{{{name}}}}}:", edit)
        edits[name] = edit
    layout.addLayout(form)
    box = ok_cancel_button_box()
    box.accepted.connect(dialog.accept)
    box.rejected.connect(dialog.reject)
    layout.addWidget(box)
    if dialog.exec() != QDialog.DialogCode.Accepted:
        return None
    return {name: edit.text() for name, edit in edits.items()}


def open_snippet_palette(parent: QWidget | None, editor) -> None:
    dialog = SnippetPaletteDialog(parent, editor=editor)
    dialog.setWindowModality(Qt.WindowModality.WindowModal)
    dialog.exec()
