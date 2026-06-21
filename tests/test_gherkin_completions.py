"""Gherkin completion popup delegate."""

from __future__ import annotations

import pytest
from PySide6.QtGui import QFont, QFontMetrics, QImage, QPainter
from PySide6.QtWidgets import QApplication, QStyle, QStyleOptionViewItem

from app.gherkin_snippets import GherkinSnippet
from app.qt.widgets.gherkin_completions import _CompletionDelegate


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_completion_row_height_fits_three_lines(qapp) -> None:
    delegate = _CompletionDelegate()
    option = QStyleOptionViewItem()
    option.font = QFont("Segoe UI", 9)
    height = delegate._row_height(option)

    label_fm = QFontMetrics(option.font)
    assert height >= label_fm.height() * 3 + 20


def test_completion_delegate_paint_does_not_crash(qapp) -> None:
    delegate = _CompletionDelegate()
    snippet = GherkinSnippet(label="нажимаю", insert='нажимаю "button.submit"', description="Клик (action: click)")
    image = QImage(480, 80, QImage.Format.Format_ARGB32)
    image.fill(0)

    painter = QPainter(image)
    option = QStyleOptionViewItem()
    option.rect = image.rect()
    option.font = QFont("Segoe UI", 9)
    option.state = option.state | QStyle.StateFlag.State_Selected

    from PySide6.QtCore import QAbstractListModel, QModelIndex, Qt

    class _OneRowModel(QAbstractListModel):
        def rowCount(self, parent=None):
            return 1

        def data(self, index, role=Qt.ItemDataRole.DisplayRole):
            if role == Qt.ItemDataRole.UserRole:
                return snippet
            return None

    model = _OneRowModel()
    index = model.index(0)
    delegate.paint(painter, option, index)
    painter.end()

    assert not image.isNull()
