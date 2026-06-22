"""Dirty banner modes (F6-7)."""

from __future__ import annotations

import pytest
from PySide6.QtWidgets import QApplication


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_dirty_banner_unapplied_shows_apply(qapp) -> None:
    from app.qt.widgets.dirty_banner import DirtyBanner

    banner = DirtyBanner()
    banner.set_banner(visible=True, mode="unapplied")
    assert banner.isVisible()
    assert banner._apply_btn.isVisible()
    assert "Ctrl+Shift+S" in banner._text.text()


def test_dirty_banner_parse_error_hides_apply(qapp) -> None:
    from app.qt.widgets.dirty_banner import DirtyBanner

    banner = DirtyBanner()
    banner.set_banner(visible=True, mode="parse_error")
    assert banner.isVisible()
    assert not banner._apply_btn.isVisible()
