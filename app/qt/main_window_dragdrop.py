"""Drag-and-drop open for MainWindow (T7-1)."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtGui import QDragEnterEvent, QDropEvent

from app.brand import BRAND_NAME
from app.feature_store import get_root
from app.qt.dialogs import alert, confirm
from app.qt.drag_drop import classify_drop_paths, paths_from_drop_urls
from app.recent import remember_feature, remember_project

if TYPE_CHECKING:
    from app.qt.main_window import MainWindow


class MainWindowDragDropMixin:
    def dragEnterEvent(self: MainWindow, event: QDragEnterEvent) -> None:  # noqa: N802
        if not event.mimeData().hasUrls():
            return
        urls = [url.toLocalFile() for url in event.mimeData().urls()]
        paths = paths_from_drop_urls(urls)
        if not paths:
            return
        features, directories = classify_drop_paths(paths)
        if not features and not directories:
            return
        event.acceptProposedAction()
        hints: list[str] = []
        if features:
            hints.append(f"{len(features)} .feature")
        if directories:
            hints.append(f"проект «{directories[0].name}»")
        self.status_bar.set_message(f"Отпустите для открытия: {', '.join(hints)}", "info")

    def dragLeaveEvent(self: MainWindow, event) -> None:  # noqa: N802
        self._restore_status_after_drag()
        super().dragLeaveEvent(event)

    def dropEvent(self: MainWindow, event: QDropEvent) -> None:  # noqa: N802
        if not event.mimeData().hasUrls():
            return
        urls = [url.toLocalFile() for url in event.mimeData().urls()]
        paths = paths_from_drop_urls(urls)
        features, directories = classify_drop_paths(paths)
        ignored = len(paths) - len(features) - len(directories)

        if directories:
            self._open_dropped_project(directories[0])

        if features:
            if not self.workspace.apply_before_action():
                event.acceptProposedAction()
                self._restore_status_after_drag()
                return
            opened = self.workspace.open_files(features, reload_if_clean=True)
            root = get_root()
            for path in features:
                remember_feature(path)
                if root is not None and root in path.parents:
                    self._controller.catalog.select_feature(path)
            self._refresh_welcome_recents()
            self.status_bar.set_message(f"Открыто файлов: {opened}", "success")

        if ignored > 0:
            alert(
                self,
                BRAND_NAME,
                f"Пропущено элементов: {ignored} (ожидаются .feature или папка проекта).",
            )

        event.acceptProposedAction()
        if not features:
            self._restore_status_after_drag()

    def _open_dropped_project(self: MainWindow, folder: Path) -> None:
        resolved = folder.resolve()
        current = get_root()
        if current is not None and current.resolve() != resolved:
            if not confirm(
                self,
                BRAND_NAME,
                f"Открыть проект «{resolved.name}»?\nТекущий: {current}",
            ):
                return
        self._controller.catalog.set_features_root(resolved)
        remember_project(resolved)
        self._refresh_welcome_recents()
        self.status_bar.set_message(str(resolved))
        self.workspace.ensure_welcome_tab(activate=not self.workspace.has_editor_tabs())

    def _restore_status_after_drag(self: MainWindow) -> None:
        root = get_root()
        if root is not None:
            self.status_bar.set_message(str(root))
        else:
            self.status_bar.set_message("Проект → Открыть проект…", "info")
