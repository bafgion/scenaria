"""Gherkin code editor with full-line highlights for steps and errors only."""

from __future__ import annotations

import re

from PySide6.QtCore import Qt
from app.gherkin_ru import STEP_INDENT, is_step_indented, leading_indent, suggest_step_keyword
from app.gherkin_ru import block_text_has_step_content
from PySide6.QtGui import (
    QColor,
    QGuiApplication,
    QKeyEvent,
    QTextCharFormat,
    QTextCursor,
    QTextFormat,
)
from PySide6.QtWidgets import QMenu, QPlainTextEdit, QTextEdit

from app.qt.fonts import editor_font
from app.qt.theme import COLOR_EDITOR
from app.qt.widgets.gherkin_completions import GherkinCompleter
from app.qt.widgets.gherkin_highlighter import GherkinHighlighter


class GherkinEditor(QPlainTextEdit):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._step_selections: list[QTextEdit.ExtraSelection] = []
        self._completer = GherkinCompleter(self)
        self._highlighter = GherkinHighlighter(self.document())
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.setProperty("role", "code-editor")
        font = editor_font()
        self.setFont(font)
        self.setTabStopDistance(4 * self.fontMetrics().horizontalAdvance(" "))
        self.setStyleSheet(f"QPlainTextEdit {{ background: {COLOR_EDITOR}; }}")

    def keyPressEvent(self, event: QKeyEvent) -> None:  # noqa: N802
        if event.key() == Qt.Key.Key_F1:
            event.accept()
            self._open_step_help_for_line()
            return
        if (
            event.key() == Qt.Key.Key_Space
            and event.modifiers() & Qt.KeyboardModifier.ControlModifier
            and event.modifiers() & Qt.KeyboardModifier.ShiftModifier
        ):
            event.accept()
            self._open_snippet_palette()
            return
        if event.key() == Qt.Key.Key_Space and event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            event.accept()
            self._completer.trigger()
            return
        if self._completer.handle_key(event):
            event.accept()
            return
        super().keyPressEvent(event)
        if event.text() and event.text().isprintable():
            self._completer.maybe_auto_trigger()

    def contextMenuEvent(self, event) -> None:  # noqa: N802
        from app.gherkin_snippets import HEADER_SNIPPETS, STEP_SNIPPETS

        cursor = self.textCursor()
        menu = QMenu(self)
        undo = menu.addAction("Отменить")
        undo.setShortcut("Ctrl+Z")
        undo.triggered.connect(self.undo)
        undo.setEnabled(self.document().isUndoAvailable())
        redo = menu.addAction("Повторить")
        redo.setShortcut("Ctrl+Y")
        redo.triggered.connect(self.redo)
        redo.setEnabled(self.document().isRedoAvailable())
        menu.addSeparator()
        cut = menu.addAction("Вырезать")
        cut.setShortcut("Ctrl+X")
        cut.triggered.connect(self.cut)
        cut.setEnabled(cursor.hasSelection() and not self.isReadOnly())
        copy = menu.addAction("Копировать")
        copy.setShortcut("Ctrl+C")
        copy.triggered.connect(self.copy)
        copy.setEnabled(cursor.hasSelection())
        if cursor.hasSelection() and not self.isReadOnly():
            save_snippet = menu.addAction("Сохранить выделение как сниппет…")
            save_snippet.triggered.connect(self._save_selection_as_snippet)
        paste = menu.addAction("Вставить")
        paste.setShortcut("Ctrl+V")
        paste.triggered.connect(self.paste)
        paste.setEnabled(
            not self.isReadOnly() and QGuiApplication.clipboard().mimeData().hasText()
        )
        menu.addSeparator()
        insert_menu = menu.addMenu("Вставить шаг")
        for snippet in (*HEADER_SNIPPETS, *STEP_SNIPPETS):
            action = insert_menu.addAction(snippet.label)
            action.setToolTip(f"{snippet.description}\n{snippet.insert}")
            action.triggered.connect(lambda _checked=False, s=snippet: self._insert_snippet_at_cursor(s))
        panel = self.parent()
        if panel is not None and hasattr(panel, "insert_hover_step"):
            menu.addSeparator()
            hover_action = menu.addAction("Наведение для меню…")
            hover_action.setToolTip("Вставить шаг «навожу» для выпадающего меню")
            hover_action.triggered.connect(panel.insert_hover_step)
            fix_action = menu.addAction("Починить клик с hover-меню…")
            fix_action.setToolTip("Добавить «навожу» перед строкой «нажимаю» под курсором")
            fix_action.triggered.connect(panel.fix_menu_click_at_cursor)
        complete = menu.addAction("Автодополнение")
        complete.setShortcut("Ctrl+Space")
        complete.triggered.connect(self._completer.trigger)
        from app.gherkin_quick_fixes import suggest_quick_fixes

        fixes = suggest_quick_fixes(self.toPlainText(), cursor.blockNumber() + 1)
        actionable = [item for item in fixes if item[0].label != "Открыть палитру шагов (Ctrl+Shift+Space)"]
        if actionable:
            menu.addSeparator()
            fix_menu = menu.addMenu("Исправить")
            for quick_fix, new_text in actionable:
                action = fix_menu.addAction(quick_fix.label)
                action.setToolTip(quick_fix.description)

                def _apply_fix(_checked=False, payload=new_text) -> None:
                    self.setPlainText(payload)

                action.triggered.connect(_apply_fix)
            palette_fix = next(
                (item for item in fixes if item[0].label == "Открыть палитру шагов (Ctrl+Shift+Space)"),
                None,
            )
            if palette_fix is not None:
                unknown = fix_menu.addAction("Похожий шаг из палитры…")
                unknown.triggered.connect(self._open_snippet_palette)
        palette = menu.addAction("Палитра сниппетов…")
        palette.setShortcut("Ctrl+Shift+Space")
        palette.triggered.connect(self._open_snippet_palette)
        step_help = menu.addAction("Справка по шагу…")
        step_help.setShortcut("F1")
        step_help.triggered.connect(self._open_step_help_for_line)
        menu.addSeparator()
        find_action = menu.addAction("Найти и заменить…")
        find_action.setShortcut("Ctrl+H")
        find_action.triggered.connect(self._open_find_replace)
        menu.addSeparator()
        select_all = menu.addAction("Выделить всё")
        select_all.setShortcut("Ctrl+A")
        select_all.triggered.connect(self.selectAll)
        menu.exec(event.globalPos())

    def _open_find_replace(self) -> None:
        from app.qt.widgets.find_replace_dialog import open_find_replace_dialog

        window = self.window()
        open_find_replace_dialog(window, self)

    def _save_selection_as_snippet(self) -> None:
        from app.qt.widgets.save_snippet_dialog import open_save_snippet_dialog

        cursor = self.textCursor()
        if not cursor.hasSelection():
            return
        text = cursor.selectedText().replace("\u2029", "\n")
        default_label = text.strip().splitlines()[0][:40] if text.strip() else "Сниппет"
        open_save_snippet_dialog(self.window(), text=text, default_label=default_label)

    def _open_step_help_for_line(self) -> None:
        from app.step_catalog import resolve_step_entry
        from app.qt.widgets.step_help_panel import open_step_help_panel

        cursor = self.textCursor()
        line_no = cursor.blockNumber() + 1
        text = self.toPlainText()
        entry = resolve_step_entry(text=text, line_no=line_no)
        search = ""
        if entry is None:
            line = cursor.block().text().strip()
            if line and not line.startswith("#"):
                search = re.sub(
                    r"^(?:Допустим|Когда|Тогда|И|Но)\s+",
                    "",
                    line,
                    flags=re.IGNORECASE,
                ).strip()
        open_step_help_panel(
            self.window(),
            editor=self,
            focus_entry=entry,
            initial_search=search,
        )

    def _open_snippet_palette(self) -> None:
        from app.qt.widgets.snippet_palette_dialog import open_snippet_palette

        open_snippet_palette(self.window(), self)

    def _insert_snippet_at_cursor(self, snippet) -> None:
        cursor = self.textCursor()
        block = cursor.block()
        line = block.text()
        column = cursor.position() - block.position()
        indent = leading_indent(line)
        text = snippet.insert
        if line.strip() and not line.strip().startswith("#"):
            if not is_step_indented(line) and snippet.label not in ("Функционал:", "Сценарий:"):
                text = f"{STEP_INDENT}Допустим {snippet.insert}"
            elif snippet.label in ("Допустим", "Когда", "Тогда", "И", "Но"):
                text = f"{snippet.insert} "
        elif not line.strip():
            if snippet.label in ("Функционал:", "Сценарий:"):
                text = snippet.insert
            else:
                text = f"{indent or STEP_INDENT}Допустим {snippet.insert}"
        if not line.strip() and cursor.atBlockStart():
            cursor.insertText(text)
        else:
            cursor.insertText(("\n" if column == len(line) else "") + text)
        self.setTextCursor(cursor)

    def insert_snippet_block(self, text: str) -> None:
        """Insert a multi-line Gherkin block at the cursor."""
        chunk = text.strip("\n")
        if not chunk:
            return
        cursor = self.textCursor()
        block = cursor.block()
        line = block.text()
        column = cursor.position() - block.position()
        if column < len(line):
            cursor.movePosition(QTextCursor.MoveOperation.EndOfBlock)
        elif line.strip():
            cursor.insertText("\n")
        cursor.insertText(chunk + "\n")
        self.setTextCursor(cursor)

    def suggested_step_keyword(self, cursor: QTextCursor | None = None) -> str:
        cursor = cursor or self.textCursor()
        block = cursor.block()
        line = block.text()
        column = cursor.position() - block.position()
        return suggest_step_keyword(
            current_line=line,
            cursor_column=column,
            has_steps_before=self._document_has_steps_before_cursor(cursor),
        )

    def _document_has_steps_before_cursor(self, cursor: QTextCursor) -> bool:
        block = cursor.block()
        while block.isValid():
            text = block.text()
            if block_text_has_step_content(text):
                if block != cursor.block():
                    return True
                column = cursor.position() - block.position()
                prefix = text[:column].strip()
                if prefix and not prefix.startswith("#"):
                    return True
            block = block.previous()
        return False

    def insert_step_line(self, body: str, *, before_block=None) -> None:
        """Insert a Gherkin step line at the cursor or before the given block."""
        cursor = self.textCursor()
        if before_block is not None and before_block.isValid():
            cursor.setPosition(before_block.position())
        else:
            block = cursor.block()
            line = block.text()
            column = cursor.position() - block.position()
            if column < len(line):
                cursor.movePosition(QTextCursor.MoveOperation.EndOfBlock)
        block = cursor.block()
        line = block.text()
        indent = leading_indent(line)
        if not indent:
            indent = STEP_INDENT
        keyword = self.suggested_step_keyword(cursor)
        text = f"{indent}{keyword} {body}"
        cursor.insertText(text + "\n")
        self.setTextCursor(cursor)

    def insert_quoted_text(self, value: str) -> None:
        """Insert escaped double-quoted text at the cursor."""
        from app.gherkin_ru import _quote

        cursor = self.textCursor()
        cursor.insertText(f'"{_quote(value)}"')
        self.setTextCursor(cursor)

    def set_syntax_error_line(self, line_no: int | None) -> None:
        self._highlighter.set_error_line(line_no)

    def replace_plain_text_preserve_caret(self, text: str) -> None:
        cursor = self.textCursor()
        position = cursor.position()
        anchor = cursor.anchor()
        v_scroll = self.verticalScrollBar().value()
        h_scroll = self.horizontalScrollBar().value()
        self.setPlainText(text)
        new_len = len(text)
        restored = QTextCursor(self.document())
        restored.setPosition(min(anchor, new_len))
        restored.setPosition(min(position, new_len), QTextCursor.MoveMode.KeepAnchor)
        self.setTextCursor(restored)
        self.verticalScrollBar().setValue(min(v_scroll, self.verticalScrollBar().maximum()))
        self.horizontalScrollBar().setValue(min(h_scroll, self.horizontalScrollBar().maximum()))

    def _sync_selection_highlight(self) -> None:
        self.setExtraSelections(list(self._step_selections))

    def set_step_line_highlights(self, line_numbers: list[int], *, failed: bool = False) -> None:
        self._step_selections = []
        bg = QColor("#5a1d1d") if failed else QColor("#264f78")
        for line_no in line_numbers:
            block = self.document().findBlockByNumber(max(0, line_no - 1))
            if not block.isValid():
                continue
            fmt = QTextCharFormat()
            fmt.setBackground(bg)
            fmt.setProperty(QTextFormat.Property.FullWidthSelection, True)
            sel = QTextEdit.ExtraSelection()
            sel.cursor = QTextCursor(block)
            sel.format = fmt
            self._step_selections.append(sel)
        self._sync_selection_highlight()

    def clear_step_line_highlights(self) -> None:
        self._step_selections = []
        self._sync_selection_highlight()

    def clear_char_formats(self) -> None:
        cursor = self.textCursor()
        position = cursor.position()
        anchor = cursor.anchor()
        had_selection = cursor.hasSelection()
        self._highlighter.rehighlight()
        self._restore_text_cursor(position, anchor, had_selection)

    def _restore_text_cursor(self, position: int, anchor: int, had_selection: bool) -> None:
        doc_len = len(self.toPlainText())
        restored = QTextCursor(self.document())
        if had_selection:
            start = max(0, min(anchor, position, doc_len))
            end = max(0, min(max(anchor, position), doc_len))
            restored.setPosition(start)
            restored.setPosition(end, QTextCursor.MoveMode.KeepAnchor)
        else:
            restored.setPosition(max(0, min(position, doc_len)))
        self.setTextCursor(restored)
