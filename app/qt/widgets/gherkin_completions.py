"""Autocomplete popup for the Gherkin editor."""

from __future__ import annotations

import re

from PySide6.QtCore import QAbstractListModel, QModelIndex, Qt
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import QCompleter, QPlainTextEdit

from app.gherkin_snippets import GherkinSnippet, KEYWORDS, completions_for_line


class _SnippetListModel(QAbstractListModel):
    def __init__(self) -> None:
        super().__init__()
        self._snippets: list[GherkinSnippet] = []

    def set_snippets(self, snippets: list[GherkinSnippet]) -> None:
        self.beginResetModel()
        self._snippets = snippets
        self.endResetModel()

    def snippet_at(self, row: int) -> GherkinSnippet | None:
        if 0 <= row < len(self._snippets):
            return self._snippets[row]
        return None

    def rowCount(self, parent: QModelIndex | None = None) -> int:  # noqa: N802
        return len(self._snippets)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole):  # noqa: N802
        if not index.isValid():
            return None
        snippet = self._snippets[index.row()]
        if role == Qt.ItemDataRole.DisplayRole:
            return f"{snippet.label} — {snippet.description}"
        if role == Qt.ItemDataRole.ToolTipRole:
            return f"{snippet.description}\n{snippet.insert}"
        return None


class GherkinCompleter:
    """Line-aware completer for QPlainTextEdit."""

    def __init__(self, editor: QPlainTextEdit) -> None:
        self._editor = editor
        self._replace_start = 0
        self._replace_end = 0
        self._model = _SnippetListModel()
        self._completer = QCompleter(self._model, editor)
        self._completer.setWidget(editor)
        self._completer.setCompletionMode(QCompleter.CompletionMode.UnfilteredPopupCompletion)
        self._completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self._completer.setWrapAround(False)
        self._completer.activated.connect(self._on_activated)

    def popup_visible(self) -> bool:
        return self._completer.popup().isVisible()

    def handle_key(self, event: QKeyEvent) -> bool:
        if not self.popup_visible():
            return False
        key = event.key()
        if key in (Qt.Key.Key_Enter, Qt.Key.Key_Return, Qt.Key.Key_Tab):
            self._accept_current()
            return True
        if key == Qt.Key.Key_Escape:
            self._completer.popup().hide()
            return True
        return False

    def trigger(self) -> bool:
        cursor = self._editor.textCursor()
        block = cursor.block()
        line = block.text()
        column = cursor.position() - block.position()
        start, end, matches = completions_for_line(line, column)
        if not matches:
            self._completer.popup().hide()
            return False

        self._replace_start = block.position() + start
        self._replace_end = block.position() + end
        self._model.set_snippets(matches)
        prefix = line[start:end]
        self._completer.setCompletionPrefix(prefix)
        rect = self._editor.cursorRect(cursor)
        rect.setWidth(max(360, self._completer.popup().sizeHintForColumn(0) + 48))
        self._completer.complete(rect)
        return True

    def maybe_auto_trigger(self) -> None:
        if self.popup_visible():
            return
        cursor = self._editor.textCursor()
        block = cursor.block()
        line = block.text()
        column = cursor.position() - block.position()
        start, end, matches = completions_for_line(line, column)
        if len(matches) < 1:
            return
        prefix = line[start:end]
        if len(matches) == 1 and len(prefix) < 2 and not prefix.endswith(" "):
            return
        if len(matches) >= 2 and len(prefix) < 2 and not prefix.endswith(" "):
            return
        self.trigger()

    def _accept_current(self) -> None:
        popup = self._completer.popup()
        row = popup.currentIndex().row()
        if row < 0:
            row = 0
        snippet = self._model.snippet_at(row)
        if snippet is not None:
            self._insert_snippet(snippet)
        popup.hide()

    def _on_activated(self, _text: object) -> None:
        popup = self._completer.popup()
        snippet = self._model.snippet_at(popup.currentIndex().row())
        if snippet is not None:
            self._insert_snippet(snippet)
        popup.hide()

    def _insert_snippet(self, snippet: GherkinSnippet) -> None:
        cursor = self._editor.textCursor()
        block_text = cursor.block().text()
        indent = block_text[: len(block_text) - len(block_text.lstrip())]

        insert = snippet.insert
        if snippet.label in KEYWORDS:
            if not block_text.strip():
                insert = f"{indent}{snippet.insert} "
            else:
                insert = f"{snippet.insert} "
        else:
            stripped = block_text.strip()
            has_keyword = bool(
                re.match(r"^(Допустим|Когда|Тогда|И|Но)\s+", stripped, flags=re.IGNORECASE)
            )
            if not has_keyword:
                keyword = self._editor.suggested_step_keyword(cursor)
                insert = f"{keyword} {insert}"

        cursor.beginEditBlock()
        cursor.setPosition(self._replace_start)
        cursor.setPosition(self._replace_end, cursor.MoveMode.KeepAnchor)
        cursor.insertText(insert)
        cursor.endEditBlock()
        self._editor.setTextCursor(cursor)
