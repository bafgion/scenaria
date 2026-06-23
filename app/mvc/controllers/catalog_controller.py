"""Catalog sidebar controller."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QFileDialog, QWidget

from app.brand import BRAND_NAME
from app.feature_store import resolve_project_root
from app.mvc.models.catalog_model import CatalogModel
from app.qt.dialogs import alert


class CatalogController(QObject):
    file_open_requested = Signal(object)  # Path

    def __init__(self, model: CatalogModel, *, parent_widget: QWidget | None = None) -> None:
        super().__init__(parent_widget)
        self._model = model
        self._parent_widget = parent_widget

    def initialize(self) -> None:
        root = resolve_project_root()
        if root is not None:
            self._model.set_features_root(root)
        else:
            self._model.refresh_tree()

    def open_project(self) -> bool:
        start = str(self._model.features_root or Path.home())
        path = QFileDialog.getExistingDirectory(
            self._parent_widget,
            "Открыть папку проекта",
            start,
        )
        if not path:
            return False
        return self.open_project_at(Path(path))

    def open_project_at(self, path: Path) -> bool:
        if not path.is_dir():
            return False
        self._model.set_features_root(path)
        return True

    def choose_root_directory(self) -> None:
        self.open_project()

    def set_filter(self, text: str) -> None:
        self._model.set_filter(text)

    def on_tree_activated(self, path: Path, *, kind: str) -> None:
        if kind == "file":
            self.file_open_requested.emit(path)
        else:
            self._model.select_directory(path)

    def toggle_run_selection(self, path: Path) -> None:
        self._model.toggle_run_selection(path)

    def add_folder_to_run_selection(self, path: Path) -> None:
        from app.mvc.models.catalog_model import collect_feature_paths_under

        paths = collect_feature_paths_under(path)
        if not paths:
            if self._parent_widget is not None:
                alert(self._parent_widget, BRAND_NAME, "В этой папке нет .feature сценариев")
            return
        added_before = self._model.run_selection_count
        self._model.add_folder_to_run_selection(path)
        if self._model.run_selection_count == added_before:
            if self._parent_widget is not None:
                alert(self._parent_widget, BRAND_NAME, "Все сценарии папки уже в выборе")

    def new_scenario_requested(self) -> None:
        target = self._model.target_directory_for_new_file()
        if target is not None:
            self._model.select_directory(target)
