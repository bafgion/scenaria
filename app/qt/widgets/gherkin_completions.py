"""Autocomplete popup for the Gherkin editor."""

from __future__ import annotations

import re

from PySide6.QtCore import QAbstractListModel, QModelIndex, QRect, QSize, Qt
from PySide6.QtGui import QColor, QFont, QFontMetrics, QKeyEvent, QPainter
from PySide6.QtWidgets import (
    QCompleter,
    QPlainTextEdit,
    QStyle,
    QStyledItemDelegate,
    QStyleOptionViewItem,
)

from app.gherkin_snippets import KEYWORDS, GherkinSnippet, completions_for_line
from app.qt.theme import (
    COLOR_ACTIVITY,
    COLOR_BORDER,
    COLOR_DIR_SELECTED,
    COLOR_INPUT,
    COLOR_MUTED,
    COLOR_SIDEBAR,
    COLOR_TEXT,
)
from app.step_catalog import entry_for_action

# Gherkin string token color (matches gherkin_highlighter)
_COLOR_EXAMPLE = "#ce9178"
_COLOR_LABEL = "#9cdc8a"


class _CompletionDelegate(QStyledItemDelegate):
    """Rich completion row: label, description, example (F1-2)."""

    _PAD_H = 12
    _PAD_V = 8
    _LINE_GAP = 4
    _EXAMPLE_GAP = 6
    _EXAMPLE_PAD = 6

    def _fonts(self, base: QFont) -> tuple[QFont, QFont, QFont]:
        label_font = QFont(base)
        label_font.setBold(True)

        desc_font = QFont(base)
        if desc_font.pointSize() > 0:
            desc_font.setPointSize(max(8, desc_font.pointSize() - 1))

        mono_font = QFont(base)
        mono_font.setFamily("Consolas")
        if mono_font.family() != "Consolas":
            mono_font.setStyleHint(QFont.StyleHint.Monospace)
        if mono_font.pointSize() > 0:
            mono_font.setPointSize(max(8, mono_font.pointSize() - 1))
        return label_font, desc_font, mono_font

    def _row_height(self, option: QStyleOptionViewItem) -> int:
        label_font, desc_font, mono_font = self._fonts(option.font)
        label_fm = QFontMetrics(label_font)
        desc_fm = QFontMetrics(desc_font)
        mono_fm = QFontMetrics(mono_font)
        return (
            self._PAD_V * 2
            + label_fm.height()
            + self._LINE_GAP
            + desc_fm.height()
            + self._EXAMPLE_GAP
            + mono_fm.height()
            + self._EXAMPLE_PAD
        )

    def sizeHint(self, option: QStyleOptionViewItem, index: QModelIndex) -> QSize:  # noqa: N802
        width = option.rect.width() if option.rect.width() > 0 else 460
        return QSize(width, self._row_height(option))

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

        selected = bool(option.state & QStyle.StateFlag.State_Selected)
        hovered = bool(option.state & QStyle.StateFlag.State_MouseOver)

        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        if selected:
            painter.fillRect(option.rect, QColor(COLOR_DIR_SELECTED))
        elif hovered:
            painter.fillRect(option.rect, QColor(COLOR_ACTIVITY))

        label_font, desc_font, mono_font = self._fonts(option.font)
        label_fm = QFontMetrics(label_font)
        desc_fm = QFontMetrics(desc_font)
        mono_fm = QFontMetrics(mono_font)

        content = option.rect.adjusted(self._PAD_H, self._PAD_V, -self._PAD_H, -self._PAD_V)
        x = content.left()
        y = content.top()
        max_text_w = max(120, content.width())

        painter.setFont(label_font)
        painter.setPen(QColor(COLOR_TEXT if selected else _COLOR_LABEL))
        painter.drawText(x, y + label_fm.ascent(), snippet.label)
        y += label_fm.height() + self._LINE_GAP

        painter.setFont(desc_font)
        painter.setPen(QColor(COLOR_MUTED))
        painter.drawText(
            x,
            y + desc_fm.ascent(),
            desc_fm.elidedText(description, Qt.TextElideMode.ElideRight, max_text_w),
        )
        y += desc_fm.height() + self._EXAMPLE_GAP

        example_h = mono_fm.height() + self._EXAMPLE_PAD
        example_box = QRect(x - 2, y - 2, max_text_w + 4, example_h + 2)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(COLOR_INPUT if not selected else "#2a3f52"))
        painter.drawRoundedRect(example_box, 3, 3)

        painter.setFont(mono_font)
        painter.setPen(QColor(_COLOR_EXAMPLE))
        painter.drawText(
            example_box.adjusted(self._EXAMPLE_PAD, 0, -self._EXAMPLE_PAD, 0),
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
            mono_fm.elidedText(example, Qt.TextElideMode.ElideRight, example_box.width() - self._EXAMPLE_PAD * 2),
        )

        if index.row() > 0:
            divider = option.rect.adjusted(self._PAD_H, 0, -self._PAD_H, 0)
            painter.setPen(QColor(COLOR_BORDER))
            painter.drawLine(divider.topLeft(), divider.topRight())

        painter.restore()


_ACTION_RE = re.compile(r"action:\s*(\w+)", re.IGNORECASE)


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
        popup.setMinimumWidth(460)
        popup.setSpacing(0)
        popup.setUniformItemSizes(False)
        popup.setStyleSheet(
            f"""
            QListView {{
                background: {COLOR_SIDEBAR};
                color: {COLOR_TEXT};
                border: 1px solid {COLOR_BORDER};
                padding: 4px 0;
                outline: none;
            }}
            QListView::item {{
                border: none;
                padding: 0;
            }}
            """
        )
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
        rect.setWidth(max(460, self._completer.popup().sizeHintForColumn(0) + 48))
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
