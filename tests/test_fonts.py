"""Tests for editor font resolution."""

from __future__ import annotations

import pytest
from PySide6.QtWidgets import QApplication


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_editor_font_family_resolves(qapp) -> None:
    from app.qt.fonts import editor_font, editor_font_family

    family = editor_font_family()
    assert family

    font = editor_font()
    assert font.pointSize() == 10
    assert font.fixedPitch()
