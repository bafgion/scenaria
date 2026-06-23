"""Batch run and plugin runner helpers extracted from MainWindow (T2-3)."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtWidgets import QFileDialog, QInputDialog

from app.brand import BRAND_NAME
from app.feature_store import get_root
from app.plugins.installer import PluginInstallError, install_from_zip, install_plugin
from app.plugins.registry import get_registry
from app.qt.dialogs import alert, confirm

if TYPE_CHECKING:
    from app.qt.main_window import MainWindow


class MainWindowBatchMixin:
    """Selected/folder/tag batch runs and optional runner add-ons."""

    def _is_plugin_installed(self: MainWindow, plugin_id: str) -> bool:
        return get_registry().get_runner(plugin_id) is not None

    def _run_batch_with_runner(self: MainWindow, runner_id: str) -> None:
        root = get_root()
        if root is None:
            alert(self, BRAND_NAME, "Сначала откройте проект с .feature файлами")
            return
        if not self._prepare_batch_run():
            return
        self._controller.recording.run_project_suite_with_runner(runner_id)

    def _install_runner_addon(self: MainWindow, plugin_id: str) -> bool:
        if self._is_plugin_installed(plugin_id):
            return True
        if confirm(self, BRAND_NAME, f"Скачать add-on «{plugin_id}» с GitHub Releases?"):
            try:
                install_plugin(plugin_id)
            except PluginInstallError as exc:
                if not confirm(self, BRAND_NAME, f"{exc}\n\nУказать локальный zip?"):
                    return False
                path, _ = QFileDialog.getOpenFileName(
                    self,
                    "Выберите zip add-on",
                    "",
                    "Zip (*.zip)",
                )
                if not path:
                    return False
                try:
                    install_from_zip(Path(path), plugin_id=plugin_id)
                except PluginInstallError as exc2:
                    alert(self, BRAND_NAME, str(exc2))
                    return False
            self._refresh_plugins_menu()
            alert(self, BRAND_NAME, f"Add-on «{plugin_id}» установлен.")
            return self._is_plugin_installed(plugin_id)

        path, _ = QFileDialog.getOpenFileName(
            self,
            "Выберите zip add-on",
            "",
            "Zip (*.zip)",
        )
        if not path:
            return False
        try:
            install_from_zip(Path(path), plugin_id=plugin_id)
        except PluginInstallError as exc:
            alert(self, BRAND_NAME, str(exc))
            return False
        self._refresh_plugins_menu()
        alert(self, BRAND_NAME, f"Add-on «{plugin_id}» установлен.")
        return self._is_plugin_installed(plugin_id)

    def _prepare_batch_run(self: MainWindow) -> bool:
        self.workspace.persist_current_tab()
        if self.workspace.gherkin_panel.has_parse_error:
            if not confirm(
                self,
                BRAND_NAME,
                "В тексте сценария есть ошибки.\n"
                "Пакетный запуск читает файлы с диска — продолжить?",
            ):
                return False
        self.workspace.flush_all_tabs_to_disk()
        return True

    def _run_selected_features(self: MainWindow) -> None:
        paths = self._controller.catalog.run_selection_paths
        if not paths:
            return
        if not self._prepare_batch_run():
            return
        self._controller.recording.run_selected_features(paths)

    def _run_folder_features(self: MainWindow, folder: object) -> None:
        from app.mvc.models.catalog_model import collect_feature_paths_under

        if not isinstance(folder, Path):
            return
        paths = collect_feature_paths_under(folder)
        if not paths:
            alert(self, BRAND_NAME, "В этой папке нет .feature сценариев")
            return
        if not self._prepare_batch_run():
            return
        self._controller.recording.run_selected_features(paths)

    def _run_single_feature(self: MainWindow, path: object) -> None:
        if not isinstance(path, Path):
            return
        if not self._prepare_batch_run():
            return
        self._controller.recording.run_selected_features([path])

    def _run_vanessa_file(self: MainWindow, path: object) -> None:
        if not isinstance(path, Path):
            return
        if not self._is_plugin_installed("vanessa"):
            if not self._install_runner_addon("vanessa"):
                return
        self._run_vanessa_paths([path])

    def _run_vanessa_folder(self: MainWindow, folder: object) -> None:
        from app.mvc.models.catalog_model import collect_feature_paths_under

        if not isinstance(folder, Path):
            return
        if not self._is_plugin_installed("vanessa"):
            if not self._install_runner_addon("vanessa"):
                return
        paths = collect_feature_paths_under(folder)
        if not paths:
            alert(self, BRAND_NAME, "В этой папке нет .feature сценариев")
            return
        self._run_vanessa_paths(paths)

    def _run_vanessa_paths(self: MainWindow, paths: list[Path]) -> None:
        if not paths:
            return
        if not self._prepare_batch_run():
            return
        if len(paths) == 1:
            label = f"Прогон Vanessa — {paths[0].name}"
        else:
            label = f"Прогон Vanessa ({len(paths)} файлов)"
        self._controller.recording.run_features_with_runner(
            paths,
            runner_id="vanessa",
            label=label,
        )

    def _show_folder_run_history(self: MainWindow, folder: object) -> None:
        from app.mvc.models.catalog_model import collect_feature_paths_under
        from app.run_status_store import get_run_history

        if not isinstance(folder, Path):
            return
        paths = [item for item in collect_feature_paths_under(folder) if get_run_history(item)]
        if not paths:
            alert(self, BRAND_NAME, "В папке нет сохранённой истории прогонов.")
            return
        if len(paths) == 1:
            self._show_run_history(paths[0])
            return
        root = get_root()
        labels = []
        for item in paths:
            if root is not None:
                try:
                    labels.append(str(item.resolve().relative_to(root.resolve())))
                except ValueError:
                    labels.append(item.name)
            else:
                labels.append(item.name)
        choice, ok = QInputDialog.getItem(
            self,
            "История прогонов папки",
            "Выберите сценарий:",
            labels,
            editable=False,
        )
        if not ok or not choice:
            return
        index = labels.index(str(choice))
        self._show_run_history(paths[index])

    def _run_project_tag(self: MainWindow) -> None:
        from app.mvc.models.catalog_model import parse_catalog_filter

        _, tag_from_filter = parse_catalog_filter(self._controller.catalog.filter_text)
        initial = tag_from_filter or ""
        value = self._prompt_tag_for_batch(initial)
        if value is None:
            return
        tag = value.strip().lstrip("@")
        if not tag:
            alert(self, BRAND_NAME, "Укажите тег")
            return
        if not self._prepare_batch_run():
            return
        self._controller.recording.run_project_tag(tag)

    def _prompt_tag_for_batch(self: MainWindow, initial: str) -> str | None:
        from app.qt.dialogs import prompt_text

        return prompt_text(
            self,
            "Запуск по тегу",
            "Тег (без @), например smoke:",
            initial=initial,
        )

    def _update_run_selection_menu(self: MainWindow) -> None:
        count = self._controller.catalog.run_selection_count
        self._act_run_selected.setText(
            f"Запустить выбранные ({count})" if count else "Запустить выбранные"
        )
        self._act_run_selected.setEnabled(count > 0)
