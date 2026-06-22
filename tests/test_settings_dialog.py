"""Unified settings dialog (F6-5)."""

from __future__ import annotations

import json

import pytest
from PySide6.QtWidgets import QApplication

from app.qt.widgets.settings_dialog import SettingsDialog


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_settings_dialog_saves_to_file(qapp, tmp_path, monkeypatch) -> None:
    path = tmp_path / "settings.json"
    path.write_text(json.dumps({"toolbar_compact": False, "steps_panel_height": 160}), encoding="utf-8")
    monkeypatch.setattr("app.settings.settings_path", lambda: path)
    monkeypatch.setattr("app.paths.settings_path", lambda: path)

    dialog = SettingsDialog()
    dialog._toolbar_compact.setChecked(True)
    dialog._steps_panel_height.setValue(200)
    dialog._filter_recording.setChecked(True)
    dialog._save_and_accept()

    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["toolbar_compact"] is True
    assert data["steps_panel_height"] == 200
    assert data["filter_recording"] is True


def test_open_settings_returns_result_on_accept(qapp, tmp_path, monkeypatch) -> None:
    path = tmp_path / "settings.json"
    path.write_text("{}", encoding="utf-8")
    monkeypatch.setattr("app.settings.settings_path", lambda: path)
    monkeypatch.setattr("app.paths.settings_path", lambda: path)

    dialog = SettingsDialog()
    dialog._toolbar_compact.setChecked(True)
    dialog._save_and_accept()
    result = dialog.save_result()
    assert result.saved
    assert result.toolbar_compact is True
    assert result.toolbar_compact_changed is True


def test_settings_search_filters_options(qapp) -> None:
    from app.qt.widgets.command_palette import match_score

    dialog = SettingsDialog()
    dialog.show()
    qapp.processEvents()
    dialog._search_edit.setText("компакт")
    qapp.processEvents()
    interface_matches = [
        target
        for target in dialog._search_targets
        if target.tab == "interface" and match_score("компакт", target.text) is not None
    ]
    recording_matches = [
        target
        for target in dialog._search_targets
        if target.tab == "recording" and match_score("компакт", target.text) is not None
    ]
    assert interface_matches
    assert not recording_matches
    assert any(target.widget.isVisible() for target in interface_matches)
    dialog._search_edit.clear()
    qapp.processEvents()
    dialog.reject()


def test_settings_search_switches_tab(qapp) -> None:
    dialog = SettingsDialog(initial_tab="interface")
    dialog._search_edit.setText("vanessa")
    qapp.processEvents()
    current = dialog._nav.currentItem()
    assert current is not None
    assert current.text() == "Плагины"
    dialog.reject()


def test_recording_settings_opens_recording_tab(qapp) -> None:
    from app.qt.widgets.recording_settings_dialog import open_recording_settings_dialog

    dialog = SettingsDialog(initial_tab="recording")
    item = dialog._nav.currentItem()
    assert item is not None
    assert item.text() == "Запись и браузер"
    dialog.reject()
    assert open_recording_settings_dialog.__module__ == "app.qt.widgets.recording_settings_dialog"
