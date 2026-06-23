"""GUI smoke tests: startup, theme, dialogs, recording controller paths."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest
from PySide6.QtWidgets import QApplication, QPlainTextEdit

from app.mvc.controllers.app_controller import AppController
from app.mvc.controllers.recording_controller import RecordingController
from app.mvc.models.catalog_model import CatalogModel
from app.mvc.models.scenario_model import ScenarioModel
from app.mvc.models.session_model import SessionModel
from app.player import ScenarioPlayer
from app.recorder import ScenarioRecorder


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


@pytest.fixture
def recording_controller() -> RecordingController:
    recorder = MagicMock(spec=ScenarioRecorder)
    recorder.browser_open = False
    recorder.is_busy = False
    player = MagicMock(spec=ScenarioPlayer)
    player.browser_open = False
    ctrl = RecordingController(
        scenario=ScenarioModel(),
        catalog=CatalogModel(),
        session=SessionModel(),
        recorder=recorder,
        player=player,
        scenario_controller=MagicMock(),
    )
    ctrl.attach_bridge(MagicMock())
    return ctrl


def _show_and_close(dialog, qapp) -> None:
    dialog.show()
    qapp.processEvents()
    dialog.reject()


def test_apply_dark_theme_smoke(qapp) -> None:
    from app.qt.branding import apply_app_branding
    from app.qt.theme import apply_dark_theme

    apply_app_branding(qapp)
    apply_dark_theme(qapp)
    sheet = qapp.styleSheet()
    assert len(sheet) > 500
    assert "QMainWindow" in sheet


def test_theme_avoids_unsupported_qss_selectors() -> None:
    """Regression guard for Qt stylesheet parse errors on Windows."""
    source = (Path(__file__).resolve().parents[1] / "app" / "qt" / "theme.py").read_text(
        encoding="utf-8"
    )
    forbidden = [
        ':not([accent="true"])',
        ':not([accent])',
        '[default="true"]',
        "hover:!selected",
        "8.5pt",
        'QLabel[role="link-label"] a',
    ]
    for pattern in forbidden:
        assert pattern not in source, f"unsupported QSS pattern still present: {pattern}"


def test_main_window_startup_smoke(qapp, monkeypatch) -> None:
    from app.qt.branding import apply_app_branding, apply_window_icon
    from app.qt.main_window import MainWindow
    from app.qt.theme import apply_dark_theme

    monkeypatch.setattr(
        "app.qt.main_window.MainWindow._maybe_check_updates_on_startup",
        lambda self: None,
    )

    apply_app_branding(qapp)
    apply_dark_theme(qapp)
    controller = AppController()
    window = MainWindow(controller)
    apply_window_icon(window)
    window.show()
    qapp.processEvents()

    window._on_startup()
    qapp.processEvents()

    window._sync_menu_states()
    window._sync_welcome_checklist()
    window._sync_status_runner()
    window._sync_browser_overlay()
    window._update_window_title()
    qapp.processEvents()

    assert window.isVisible()
    assert window.workspace.tab_bar.count() >= 1
    window.close()
    qapp.processEvents()


def test_main_window_view_toggles_smoke(qapp, monkeypatch) -> None:
    from app.qt.main_window import MainWindow

    monkeypatch.setattr(
        "app.qt.main_window.MainWindow._maybe_check_updates_on_startup",
        lambda self: None,
    )
    window = MainWindow(AppController())
    window.show()
    qapp.processEvents()

    window._toggle_explorer(False)
    window._toggle_explorer(True)
    window._toggle_bottom_panel(True)
    window._show_bottom_panel("log")
    window._toggle_bottom_panel(False)
    window._apply_toolbar_compact(True)
    window._apply_toolbar_compact(False)
    qapp.processEvents()

    window.close()


@pytest.mark.parametrize(
    "factory_name",
    [
        "hotkeys",
        "settings",
        "http_auth",
        "browser_session",
        "continue_recording",
        "run_history",
        "command_palette",
        "step_help",
        "picker_step",
        "save_snippet",
        "update_progress",
        "find_replace",
        "snippet_palette",
        "project_replace",
    ],
)
def test_dialogs_instantiate_without_error(qapp, factory_name: str, tmp_path: Path) -> None:
    parent = None
    editor = QPlainTextEdit()
    editor.setPlainText("Функционал: demo\nСценарий: x\n\tДопустим открыт \"https://example.com\"")
    feature = tmp_path / "demo.feature"
    feature.write_text(editor.toPlainText(), encoding="utf-8")

    if factory_name == "hotkeys":
        from app.qt.widgets.hotkeys_dialog import HotkeysDialog

        dialog = HotkeysDialog(parent)
    elif factory_name == "settings":
        from app.qt.widgets.settings_dialog import SettingsDialog

        dialog = SettingsDialog()
    elif factory_name == "http_auth":
        from app.qt.widgets.http_auth_dialog import HttpAuthDialog

        dialog = HttpAuthDialog(parent, suggested_host="example.com")
    elif factory_name == "browser_session":
        from app.qt.widgets.browser_session_dialog import BrowserSessionDialog

        dialog = BrowserSessionDialog(parent)
    elif factory_name == "continue_recording":
        from app.qt.widgets.continue_recording_dialog import ContinueRecordingDialog

        dialog = ContinueRecordingDialog(parent, step_count=3)
    elif factory_name == "run_history":
        from app.qt.widgets.run_history_dialog import RunHistoryDialog

        dialog = RunHistoryDialog(parent, feature)
    elif factory_name == "command_palette":
        from app.qt.widgets.command_palette import CommandPaletteDialog, PaletteCommand

        dialog = CommandPaletteDialog(
            [PaletteCommand(id="save", label="Сохранить", shortcut="Ctrl+S", run=lambda: None)],
            parent=parent,
        )
    elif factory_name == "step_help":
        from app.qt.widgets.step_help_panel import StepHelpPanel

        dialog = StepHelpPanel(parent, editor=editor)
    elif factory_name == "picker_step":
        from app.qt.widgets.picker_step_dialog import PickerStepDialog

        dialog = PickerStepDialog(parent, selector="button.submit")
    elif factory_name == "save_snippet":
        from app.qt.widgets.save_snippet_dialog import SaveSnippetDialog

        dialog = SaveSnippetDialog(parent, text="\tДопустим открыт \"https://example.com\"")
    elif factory_name == "update_progress":
        from app.qt.widgets.update_progress_dialog import UpdateProgressDialog

        dialog = UpdateProgressDialog(parent, from_version="0.7.0", to_version="0.8.0")
    elif factory_name == "find_replace":
        from app.qt.widgets.find_replace_dialog import FindReplaceDialog

        dialog = FindReplaceDialog(parent, editor)
    elif factory_name == "snippet_palette":
        from app.qt.widgets.snippet_palette_dialog import SnippetPaletteDialog

        mock_editor = MagicMock()
        mock_editor.insert_snippet_block = MagicMock()
        dialog = SnippetPaletteDialog(parent, editor=mock_editor)
    elif factory_name == "project_replace":
        from app.qt.widgets.project_replace_dialog import ProjectReplaceDialog

        dialog = ProjectReplaceDialog(
            parent,
            current_path=feature,
            open_paths=[feature],
            project_root=tmp_path,
        )
    else:
        raise AssertionError(factory_name)

    _show_and_close(dialog, qapp)


def test_editor_test_client_reads_scenario_model(recording_controller: RecordingController) -> None:
    recording_controller._scenario.set_source_text(
        'Контекст:\n\tДано я подключаю TestClient "DemoUser"\n'
    )
    assert recording_controller._editor_test_client() == "DemoUser"


def test_editor_test_client_empty_without_context(recording_controller: RecordingController) -> None:
    recording_controller._scenario.set_source_text("Функционал: demo\nСценарий: x\n")
    assert recording_controller._editor_test_client() is None


def test_open_browser_handles_gherkin_parse_error(
    recording_controller: RecordingController,
) -> None:
    recording_controller._scenario.set_source_text(
        "Контекст:\n\tДано неизвестный шаг в контексте\n"
    )
    recording_controller.open_browser("https://example.com")
    recording_controller._recorder.open_browser.assert_not_called()


def test_open_browser_passes_test_client_name(recording_controller: RecordingController) -> None:
    recording_controller._scenario.set_source_text(
        'Контекст:\n\tДано я подключаю TestClient "DemoUser"\n'
    )
    recording_controller.open_browser("https://example.com")
    recording_controller._recorder.open_browser.assert_called_once()
    kwargs = recording_controller._recorder.open_browser.call_args.kwargs
    assert kwargs.get("test_client") == "DemoUser"


def test_examples_testclient_feature_parses_in_editor(qapp, monkeypatch) -> None:
    from app.qt.main_window import MainWindow

    monkeypatch.setattr(
        "app.qt.main_window.MainWindow._maybe_check_updates_on_startup",
        lambda self: None,
    )
    examples_root = Path(__file__).resolve().parents[1] / "examples"
    feature = examples_root / "05-testclient-kontekst.feature"
    assert feature.is_file()

    window = MainWindow(AppController())
    window.show()
    qapp.processEvents()

    window._controller.catalog.set_features_root(examples_root)
    window._on_catalog_file_open(feature)
    qapp.processEvents()

    assert window.workspace.is_editor_tab_active()
    text = window._controller.scenario.source_text or ""
    assert "Контекст:" in text
    assert "DemoUser" in text
    assert window._suggested_test_client_name() == "DemoUser"

    window.close()
