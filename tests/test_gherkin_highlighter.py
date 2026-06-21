"""Tests for Gherkin syntax highlighter."""

from __future__ import annotations

import pytest
from PySide6.QtGui import QTextDocument
from PySide6.QtWidgets import QApplication

from app.qt.widgets.gherkin_highlighter import GherkinHighlighter


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_highlighter_accepts_feature_text(qapp) -> None:
    doc = QTextDocument()
    doc.setPlainText(
        "Функционал: UI\n"
        "@smoke\n"
        "Сценарий: Demo\n"
        "\t# комментарий\n"
        "\tДопустим открыт \"https://example.com\"\n"
        "\tИ нажимаю \"buy\"\n"
    )
    highlighter = GherkinHighlighter(doc)
    highlighter.set_error_line(5)
    highlighter.rehighlight()
    assert highlighter._error_line == 5


def test_highlighter_clears_error_line(qapp) -> None:
    doc = QTextDocument("Сценарий: x\n\tИ жду 1 сек")
    highlighter = GherkinHighlighter(doc)
    highlighter.set_error_line(2)
    highlighter.set_error_line(None)
    assert highlighter._error_line is None
