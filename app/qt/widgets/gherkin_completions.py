"""Autocomplete popup for the Gherkin editor."""

from __future__ import annotations

import re

from PySide6.QtCore import QAbstractListModel, QModelIndex, Qt, QSize
from PySide6.QtGui import QColor, QFont, QKeyEvent, QPainter
from PySide6.QtWidgets import QCompleter, QPlainTextEdit, QStyledItemDelegate, QStyleOptionViewItem

from app.gherkin_snippets import GherkinSnippet, KEYWORDS, completions_for_line
from app.step_catalog import entry_for_action


class _CompletionDelegate(QStyledItemDelegate):
    """Rich completion row: label, description, example (F1-2)."""

    def sizeHint(self, option: QStyleOptionViewItem, index: QModelIndex) -> QSize:  # noqa: N802
        return QSize(option.rect.width(), 58)

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex) -> None:  # noqa: N802
        snippet: GherkinSnippet | None = index.data(Qt.ItemDataRole.UserRole)
        if snippet is None:
            super().paint(painter, option, index)
            return
        entry = entry_for_action(
            _action_from_snippet(snippet),
            line_body=snippet.insert,
        )
        description = entry.description if entry else snippet.description
        example = entry.example if entry else snippet.insert

        painter.save()
        if option.state & option.StateFlag.State_Selected:
            painter.fillRect(option.rect, option.palette.highlight())
            text_color = option.palette.highlightedText().color()
        else:
            text_color = option.palette.text().color()
        muted = QColor(text_color)
        muted.setAlpha(180)

        x = option.rect.x() + 8
        y = option.rect.y() + 6
        label_font = QFont(option.font)
        label_font.setBold(True)
        painter.setFont(label_font)
        painter.setPen(text_color)
        painter.drawText(x, y + painter.fontMetrics().ascent(), snippet.label)

        body_font = QFont(option.font)
        body_font.setPointSize(max(8, body_font.pointSize() - 1))
        painter.setFont(body_font)
        painter.setPen(muted)
        painter.drawText(
            x,
            y + painter.fontMetrics().height() + 6,
            painter.fontMetrics().elidedText(description, Qt.TextElideMode.ElideRight, option.rect.width() - 16),
        )
        mono = QFont(option.font)
        mono.setFamily("Consolas")
        mono.setPointSize(max(8, mono.pointSize() - 1))
        painter.setFont(mono)
        painter.setPen(text_color)
        painter.drawText(
            x,
            y + painter.fontMetrics().height() * 2 + 4,
            painter.fontMetrics().elidedText(example, Qt.TextElideMode.ElideRight, option.rect.width() - 16),
        )
        painter.restore()


_ACTION_RE = re.compile(r"\(action:\s*(\w+)\)", re.IGNORECASE)


def _action_from_snippet(snippet: GherkinSnippet) -> str:
    match = _ACTION_RE.search(snippet.description)
    return match.group(1) if match else ""


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
            entry = entry_for_action(_action_from_snippet(snippet), line_body=snippet.insert)
            if entry:
                return f"{snippet.label} — {entry.description}"
            return f"{snippet.label} — {snippet.description}"
        if role == Qt.ItemDataRole.ToolTipRole:
            entry = entry_for_action(_action_from_snippet(snippet), line_body=snippet.insert)
            example = entry.example if entry else snippet.insert
            description = entry.description if entry else snippet.description
            return f"{description}\nПример: {example}"
        if role == Qt.ItemDataRole.UserRole:
            return snippet
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
        popup = self._completer.popup()
        popup.setItemDelegate(_CompletionDelegate(popup))
        popup.setMinimumWidth(420)
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
        rect.setWidth(max(420, self._completer.popup().sizeHintForColumn(0) + 48))
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
