"""Toolbar button states during playback."""

from __future__ import annotations

import pytest
from PySide6.QtWidgets import QApplication


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_toolbar_keeps_controls_during_playback_while_pending(qapp) -> None:
    from app.qt.widgets.quick_toolbar import QuickToolBar

    toolbar = QuickToolBar()
    toolbar.sync_states(
        pending=True,
        browser_open=True,
        recording=False,
        playing=True,
        has_steps=True,
    )

    assert toolbar._buttons["stop"].isEnabled()
    assert toolbar._buttons["focus_browser"].isEnabled()
    assert not toolbar._buttons["play"].isEnabled()


def test_toolbar_locks_all_while_pending_without_playback(qapp) -> None:
    from app.qt.widgets.quick_toolbar import QuickToolBar

    toolbar = QuickToolBar()
    toolbar.sync_states(
        pending=True,
        browser_open=False,
        recording=False,
        playing=False,
        has_steps=True,
    )

    assert not toolbar._buttons["stop"].isEnabled()
    assert not toolbar._buttons["focus_browser"].isEnabled()


def test_toolbar_enables_picker_for_player_browser_during_playback(qapp) -> None:
    from app.qt.widgets.quick_toolbar import QuickToolBar

    toolbar = QuickToolBar()
    toolbar.sync_states(
        pending=False,
        browser_open=True,
        recorder_browser_open=False,
        player_browser_open=True,
        recording=False,
        playing=True,
        has_steps=True,
    )

    assert toolbar._buttons["picker"].isEnabled()


def test_toolbar_enables_stop_for_player_browser_after_test(qapp) -> None:
    from app.qt.widgets.quick_toolbar import QuickToolBar

    toolbar = QuickToolBar()
    toolbar.sync_states(
        pending=False,
        browser_open=True,
        recorder_browser_open=False,
        player_browser_open=True,
        recording=False,
        playing=False,
        has_steps=True,
    )

    assert toolbar._buttons["stop"].isEnabled()


def test_toolbar_unlocks_during_picking(qapp) -> None:
    from app.qt.widgets.quick_toolbar import QuickToolBar

    toolbar = QuickToolBar()
    toolbar.sync_states(
        pending=True,
        browser_open=True,
        recording=False,
        playing=False,
        has_steps=True,
        picking=True,
    )

    assert toolbar._buttons["stop"].isEnabled()


def test_toolbar_enables_continue_record_with_steps_and_browser(qapp) -> None:
    from app.qt.widgets.quick_toolbar import QuickToolBar

    toolbar = QuickToolBar()
    toolbar.sync_states(
        pending=False,
        browser_open=True,
        recorder_browser_open=True,
        recording=False,
        playing=False,
        has_steps=True,
    )

    assert toolbar._buttons["continue_record"].isEnabled()


def test_toolbar_disables_continue_record_without_steps(qapp) -> None:
    from app.qt.widgets.quick_toolbar import QuickToolBar

    toolbar = QuickToolBar()
    toolbar.sync_states(
        pending=False,
        browser_open=True,
        recorder_browser_open=True,
        recording=False,
        playing=False,
        has_steps=False,
    )

    assert not toolbar._buttons["continue_record"].isEnabled()


def test_toolbar_disables_picker_without_browser(qapp) -> None:
    from app.qt.widgets.quick_toolbar import QuickToolBar

    toolbar = QuickToolBar()
    toolbar.sync_states(
        pending=False,
        browser_open=False,
        recorder_browser_open=False,
        player_browser_open=False,
        recording=False,
        playing=False,
        has_steps=True,
    )

    assert not toolbar._buttons["picker"].isEnabled()
