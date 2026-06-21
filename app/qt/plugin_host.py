"""Run menu host for plugin menu contributions."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtGui import QAction
from PySide6.QtWidgets import QMenu, QWidget

from app.feature_store import get_root


class RunMenuHost:
    def __init__(self, window) -> None:
        self._window = window
        self._plugin_actions: list[QAction] = []

    def parent_widget(self) -> QWidget:
        return self._window

    def project_root(self) -> Path | None:
        return get_root()

    def selected_feature_paths(self) -> list[Path]:
        return list(self._window._controller.catalog.run_selection_paths)

    def refresh_runner_menu(self) -> None:
        self._window._refresh_runner_menu()

    def ensure_plugin_installed(self, plugin_id: str) -> bool:
        if self._window._is_plugin_installed(plugin_id):
            return True
        return self._window._install_runner_addon(plugin_id)

    def prepare_batch_run(self) -> bool:
        return self._window._prepare_batch_run()

    def start_runner_batch(
        self,
        runner_id: str,
        paths: list[Path],
        *,
        label: str,
        tags: list[str] | None = None,
        exclude_tags: list[str] | None = None,
        scenario_names: list[str] | None = None,
        runner_options: dict | None = None,
    ) -> None:
        if not self.prepare_batch_run():
            return
        self._window._controller.recording.run_features_with_runner(
            paths,
            runner_id=runner_id,
            label=label,
            tags=tags or [],
            exclude_tags=exclude_tags or [],
            scenario_names=scenario_names or [],
            runner_options=runner_options or {},
        )

    def add_menu_action(self, label: str, callback) -> None:
        action = QAction(label, self._window)
        action.triggered.connect(callback)
        menu: QMenu = self._window._run_menu
        if self._window._runner_menu_separator is None:
            self._window._runner_menu_separator = menu.addSeparator()
        menu.addAction(action)
        self._plugin_actions.append(action)
        self._window._runner_menu_actions.append(action)

    def add_run_action(self, label: str, runner_id: str, callback) -> None:
        self.add_menu_action(label, callback)

    def add_install_action(self, label: str, plugin_id: str, callback) -> None:
        self.add_menu_action(label, callback)

    def clear_plugin_actions(self) -> None:
        menu: QMenu = self._window._run_menu
        for action in self._plugin_actions:
            menu.removeAction(action)
        self._plugin_actions.clear()
