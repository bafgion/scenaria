"""Tests for Gherkin editor widget."""

from __future__ import annotations

import pytest
from PySide6.QtCore import Qt
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import QApplication


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_editor_accepts_typing(qapp) -> None:
    from app.qt.widgets.gherkin_editor import GherkinEditor

    editor = GherkinEditor()
    editor.setPlainText("")

    event = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_A, Qt.KeyboardModifier.NoModifier, "a")
    editor.keyPressEvent(event)

    assert editor.toPlainText() == "a"


def test_clear_char_formats_keeps_caret_without_selection(qapp) -> None:
    from app.qt.widgets.gherkin_editor import GherkinEditor

    editor = GherkinEditor()
    editor.setPlainText("Функционал: UI\nСценарий: Demo\n\tИ нажимаю \"buy\"")
    cursor = editor.textCursor()
    cursor.setPosition(len("Функционал: UI\nСценарий: Demo\n\tИ "))
    editor.setTextCursor(cursor)

    editor.clear_char_formats()

    restored = editor.textCursor()
    assert restored.position() == len("Функционал: UI\nСценарий: Demo\n\tИ ")
    assert not restored.hasSelection()


def test_replace_plain_text_preserves_caret(qapp) -> None:
    from app.qt.widgets.gherkin_editor import GherkinEditor

    editor = GherkinEditor()
    editor.setPlainText("Функционал: UI\nСценарий: Demo\n\tИ нажимаю \"buy\"")
    cursor = editor.textCursor()
    cursor.setPosition(len("Функционал: UI\nСценарий: Demo\n\tИ "))
    editor.setTextCursor(cursor)

    editor.replace_plain_text_preserve_caret(editor.toPlainText() + "\n")

    assert editor.textCursor().position() == len("Функционал: UI\nСценарий: Demo\n\tИ ")
