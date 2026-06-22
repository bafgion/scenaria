"""Lucide-backed Qt icons."""

from __future__ import annotations

import pytest

from app.qt import icons
from app.qt.lucide_svgs import LUCIDE_BODIES


@pytest.fixture(scope="module")
def qapp():
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


@pytest.mark.parametrize("name", sorted(LUCIDE_BODIES))
def test_lucide_icon_renders(qapp, name: str) -> None:
    qicon = icons.icon(name, size=20)
    assert not qicon.isNull()
    pixmap = qicon.pixmap(20, 20)
    assert not pixmap.isNull()


def test_semantic_toolbar_icons(qapp) -> None:
    for factory in (
        icons.play_icon,
        icons.stop_icon,
        icons.record_icon,
        icons.pause_icon,
        icons.quick_record_icon,
        icons.welcome_tab_icon,
    ):
        assert not factory().isNull()


def test_toolbar_icon_names(qapp) -> None:
    for name in ("browser", "save", "validate", "picker", "log", "results", "undo", "check"):
        assert not icons.toolbar_icon(name).isNull()
