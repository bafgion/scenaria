"""Welcome checklist sync for MainWindow (T2-2 supplement)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import Qt

from app.feature_store import get_root
from app.settings import load_settings

if TYPE_CHECKING:
    from app.qt.main_window import MainWindow


class MainWindowWelcomeMixin:
    def _sync_welcome_checklist(self: MainWindow) -> None:
        settings = load_settings()
        dismissed = bool(settings.get("first_run_checklist_done"))
        project_open = get_root() is not None
        scenario = self._controller.scenario
        s = self._controller.session
        recorded = bool(scenario.steps) or s.recording
        played_success = dismissed
        self.workspace.welcome_panel.update_checklist(
            project_open=project_open,
            recorded=recorded,
            played_success=played_success,
            dismissed=dismissed,
        )

    def _on_welcome_checklist_step(self: MainWindow, step_id: int) -> None:
        if step_id == 1:
            self._open_project()
            return
        if step_id == 2:
            url = self.workspace.welcome_panel.quick_url()
            self._quick_start(url)
            return
        if step_id == 3:
            if not self.workspace.has_editor_tabs():
                self._new_scenario()
            else:
                self.workspace.show_editor()
            self._sync_menu_states()
            play_btn = self.workspace.quick_toolbar._buttons.get("play")
            if play_btn is not None and play_btn.isEnabled():
                play_btn.setFocus(Qt.FocusReason.OtherFocusReason)
            else:
                self.status_bar.set_message("Добавьте шаги и примените текст перед запуском")
