"""Disabled toolbar tooltips (F6-2)."""

from __future__ import annotations

import pytest
from PySide6.QtWidgets import QApplication


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_record_disabled_without_browser(qapp) -> None:
    from app.qt.widgets.quick_toolbar import QuickToolBar

    toolbar = QuickToolBar()
    toolbar.sync_states(
        pending=False,
        browser_open=False,
        recorder_browser_open=False,
        recording=False,
        playing=False,
        has_steps=True,
        editor_active=True,
    )
    assert not toolbar._buttons["record"].isEnabled()
    assert "браузер" in toolbar._buttons["record"].toolTip().lower()


def test_play_disabled_shows_apply_hint(qapp) -> None:
    from app.qt.widgets.quick_toolbar import QuickToolBar

    toolbar = QuickToolBar()
    toolbar.sync_states(
        pending=False,
        browser_open=True,
        recorder_browser_open=True,
        recording=False,
        playing=False,
        has_steps=True,
        unapplied=True,
        editor_active=True,
    )
    assert not toolbar._buttons["play"].isEnabled()
    assert "Примените" in toolbar._buttons["play"].toolTip()


def test_play_disabled_shows_parse_error_hint(qapp) -> None:
    from app.qt.widgets.quick_toolbar import QuickToolBar

    toolbar = QuickToolBar()
    toolbar.sync_states(
        pending=False,
        browser_open=True,
        recorder_browser_open=True,
        recording=False,
        playing=False,
        has_steps=True,
        parse_error=True,
        editor_active=True,
    )
    assert not toolbar._buttons["play"].isEnabled()
    assert "ошиб" in toolbar._buttons["play"].toolTip().lower()


def test_enabled_play_keeps_default_tooltip(qapp) -> None:
    from app.qt.widgets.quick_toolbar import QuickToolBar

    toolbar = QuickToolBar()
    toolbar.sync_states(
        pending=False,
        browser_open=True,
        recorder_browser_open=True,
        recording=False,
        playing=False,
        has_steps=True,
        editor_active=True,
    )
    assert toolbar._buttons["play"].isEnabled()
    assert "Ctrl+Enter" in toolbar._buttons["play"].toolTip()
