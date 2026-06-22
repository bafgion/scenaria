"""Features catalog tree widget."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QModelIndex, QPoint, QSize, Qt, Signal
from PySide6.QtGui import QBrush, QColor, QStandardItem, QStandardItemModel
from PySide6.QtWidgets import QMenu, QSizePolicy, QStackedWidget, QTreeView, QVBoxLayout, QWidget

from app.mvc.models.catalog_model import CatalogNode, CatalogViewState
from app.run_display import format_last_run_summary
from app.qt.theme import COLOR_ERROR, COLOR_MUTED, COLOR_SUCCESS, COLOR_WARNING
from app.qt.widgets.catalog_empty_state import CatalogEmptyState


class CatalogTreeView(QTreeView):
    run_folder_requested = Signal(object)  # Path
    add_folder_to_selection_requested = Signal(object)  # Path
    run_history_requested = Signal(object)  # Path
    run_file_requested = Signal(object)  # Path
    run_vanessa_file_requested = Signal(object)  # Path
    run_vanessa_folder_requested = Signal(object)  # Path
    run_folder_history_requested = Signal(object)  # Path

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setHeaderHidden(True)
        self.setIndentation(16)
        self.setAnimated(True)
        self.setExpandsOnDoubleClick(False)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumWidth(0)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setTextElideMode(Qt.TextElideMode.ElideRight)
        self._on_activate = None
        self._on_expansion_changed = None
        self._on_toggle_run_selection = None
        self._run_selection: frozenset[str] = frozenset()
        self._selection_mode = False

    def minimumSizeHint(self) -> QSize:  # noqa: N802
        hint = super().minimumSizeHint()
        return QSize(0, hint.height())

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        self._fit_column_width()

    def _fit_column_width(self) -> None:
        width = self.viewport().width()
        if width > 0 and self.model() is not None:
            self.setColumnWidth(0, width)

    def set_activate_handler(self, handler) -> None:
        self._on_activate = handler
        self.activated.connect(self._handle_activated)

    def set_toggle_run_selection_handler(self, handler) -> None:
        self._on_toggle_run_selection = handler

    def set_selection_mode(self, enabled: bool) -> None:
        self._selection_mode = enabled

    def set_run_selection(self, keys: frozenset[str]) -> None:
        self._run_selection = keys

    def set_expansion_handler(self, handler) -> None:
        self._on_expansion_changed = handler
        self.collapsed.connect(self._handle_collapsed)
        self.expanded.connect(self._handle_expanded)

    def _node_key(self, index: QModelIndex) -> tuple[str, str] | None:
        if not index.isValid():
            return None
        data = index.data(Qt.ItemDataRole.UserRole)
        if not data:
            return None
        path_str, kind = data
        return path_str, kind

    def _handle_collapsed(self, index: QModelIndex) -> None:
        if not self._on_expansion_changed:
            return
        info = self._node_key(index)
        if info and info[1] in {"root", "dir"}:
            self._on_expansion_changed(info[0], True)

    def _handle_expanded(self, index: QModelIndex) -> None:
        if not self._on_expansion_changed:
            return
        info = self._node_key(index)
        if info and info[1] in {"root", "dir"}:
            self._on_expansion_changed(info[0], False)

    def _handle_activated(self, index: QModelIndex) -> None:
        if not index.isValid():
            return
        from PySide6.QtWidgets import QApplication

        if QApplication.keyboardModifiers() & Qt.KeyboardModifier.ControlModifier:
            return
        self._activate_index(index)

    def mousePressEvent(self, event) -> None:  # noqa: N802
        index = self.indexAt(event.position().toPoint())
        if index.isValid() and event.button() == Qt.MouseButton.LeftButton:
            data = index.data(Qt.ItemDataRole.UserRole)
            if data:
                path_str, kind = data
                if (
                    kind == "file"
                    and self._on_toggle_run_selection
                    and (
                        event.modifiers() & Qt.KeyboardModifier.ControlModifier
                        or self._selection_mode
                    )
                ):
                    self._on_toggle_run_selection(Path(path_str))
                    event.accept()
                    return
        super().mousePressEvent(event)

    def _activate_index(self, index: QModelIndex) -> None:
        if not self._on_activate:
            return
        data = index.data(Qt.ItemDataRole.UserRole)
        if not data:
            return
        path_str, kind = data
        self._on_activate(Path(path_str), kind=kind)

    def _node_at(self, point: QPoint) -> tuple[Path, str] | None:
        index = self.indexAt(point)
        if not index.isValid():
            return None
        data = index.data(Qt.ItemDataRole.UserRole)
        if not data:
            return None
        path_str, kind = data
        return Path(path_str), kind

    def _show_context_menu(self, point: QPoint) -> None:
        info = self._node_at(point)
        if info is None:
            return
        path, kind = info
        menu = QMenu(self)
        if kind == "file":
            menu.addAction("Запустить сценарий", lambda: self.run_file_requested.emit(path))
            self._add_vanessa_actions(menu, paths=[path])
            menu.addSeparator()
            selected = str(path.resolve()) in self._run_selection
            if selected:
                toggle = menu.addAction("Убрать из запуска")
            else:
                toggle = menu.addAction("Добавить в запуск")
            toggle.triggered.connect(
                lambda: self._on_toggle_run_selection(path) if self._on_toggle_run_selection else None
            )
            menu.addSeparator()
            menu.addAction(
                "История прогонов",
                lambda: self.run_history_requested.emit(path),
            )
        elif kind in {"root", "dir"}:
            menu.addAction("Запустить сценарии в папке", lambda: self.run_folder_requested.emit(path))
            self._add_vanessa_actions(menu, paths=None, folder=path)
            menu.addAction(
                "История прогонов папки",
                lambda: self.run_folder_history_requested.emit(path),
            )
            menu.addAction(
                "Добавить папку в выбор",
                lambda: self.add_folder_to_selection_requested.emit(path),
            )
        if menu.actions():
            menu.exec(self.viewport().mapToGlobal(point))

    def _add_vanessa_actions(self, menu: QMenu, *, paths: list[Path] | None = None, folder: Path | None = None) -> None:
        from app.plugins.registry import get_registry

        info = next((item for item in get_registry().runner_infos() if item.id == "vanessa"), None)
        if info is None:
            return
        if info.available:
            if paths is not None:
                menu.addAction(
                    "Запустить через Vanessa…",
                    lambda: self.run_vanessa_file_requested.emit(paths[0]),
                )
            elif folder is not None:
                menu.addAction(
                    "Запустить через Vanessa…",
                    lambda: self.run_vanessa_folder_requested.emit(folder),
                )
        elif not info.installed:
            label = "Установить Vanessa…"
            if paths is not None:
                menu.addAction(label, lambda: self.run_vanessa_file_requested.emit(paths[0]))
            elif folder is not None:
                menu.addAction(label, lambda: self.run_vanessa_folder_requested.emit(folder))

    @staticmethod
    def _strip_run_mark(text: str) -> str:
        return text[2:] if text.startswith("◉ ") else text

    def update_run_selection_marks(self, keys: frozenset[str]) -> None:
        self._run_selection = keys
        model = self.model()
        if not isinstance(model, QStandardItemModel):
            return
        root = model.invisibleRootItem().child(0)
        if root is not None:
            self._update_item_marks(root)
            self._fit_column_width()

    def _update_item_marks(self, item: QStandardItem) -> None:
        data = item.data(Qt.ItemDataRole.UserRole)
        if data:
            path_str, kind = data
            if kind == "file":
                base = self._strip_run_mark(item.text())
                selected = str(Path(path_str).resolve()) in self._run_selection
                item.setText(f"◉ {base}" if selected else base)
        for row in range(item.rowCount()):
            self._update_item_marks(item.child(row))

    def show_tree(
        self,
        tree: CatalogNode | None,
        *,
        collapsed: set[str] | None = None,
        expand_all: bool = False,
        run_selection: frozenset[str] | None = None,
    ) -> None:
        collapsed = collapsed or set()
        self._run_selection = run_selection or frozenset()
        model = QStandardItemModel()
        if tree is not None:
            root_item = self._make_item(tree)
            for child in tree.children:
                root_item.appendRow(self._make_branch(child))
            model.appendRow(root_item)
        self.setModel(model)
        if expand_all:
            self.expandAll()
        elif tree is not None:
            self._apply_expansion(model.invisibleRootItem().child(0), collapsed)
        self._fit_column_width()

    def _apply_expansion(self, item: QStandardItem | None, collapsed: set[str]) -> None:
        if item is None:
            return
        index = item.index()
        data = item.data(Qt.ItemDataRole.UserRole)
        if data:
            path_str, kind = data
            if kind in {"root", "dir"}:
                self.setExpanded(index, path_str not in collapsed)
        for row in range(item.rowCount()):
            self._apply_expansion(item.child(row), collapsed)

    def _file_label(self, node: CatalogNode) -> str:
        if node.parse_error:
            badge = "⚠"
        elif node.run_success is True:
            badge = "✓"
        elif node.run_success is False:
            badge = "✗"
        else:
            badge = "○"
        selected = str(node.path.resolve()) in self._run_selection
        if self._selection_mode and node.kind == "file":
            box = "☑" if selected else "☐"
            mark = f"{box} "
        else:
            mark = "◉ " if selected else ""
        parts = [node.name]
        if node.parse_error:
            parts.append("ошибка")
        elif node.step_count:
            parts.append(f"{node.step_count} ш.")
        if node.example_count:
            parts.append(f"{node.example_count} прим.")
        if node.params_count:
            parts.append(f"{node.params_count} пар.")
        if node.domain:
            parts.append(node.domain)
        if node.tags:
            parts.append(" ".join(f"@{tag}" for tag in node.tags[:2]))
        if node.run_runner and node.run_runner != "playwright":
            parts.append(f"[{node.run_runner}]")
        return f"{mark}{badge} {' · '.join(parts)}"

    def _make_item(self, node: CatalogNode) -> QStandardItem:
        if node.kind == "file":
            text = self._file_label(node)
            tooltip_parts = [node.path.name]
            if node.parse_error:
                tooltip_parts.append(f"Ошибка разбора: {node.parse_error}")
            elif node.step_count:
                tooltip_parts.append(f"Шагов: {node.step_count}")
            if node.example_count:
                tooltip_parts.append(f"Примеров: {node.example_count}")
            if node.params_count:
                tooltip_parts.append(f"Наборов параметров: {node.params_count}")
            if node.domain:
                tooltip_parts.append(f"Домен: {node.domain}")
            if node.tags:
                tooltip_parts.append("Теги: " + " ".join(f"@{tag}" for tag in node.tags))
            tooltip_parts.append(
                format_last_run_summary(
                    success=node.run_success,
                    at=node.run_at,
                    duration_ms=node.run_duration_ms,
                    failed_step=node.run_failed_step,
                    message=node.run_message,
                    runner=node.run_runner,
                )
            )
            tooltip = "\n".join(tooltip_parts)
        else:
            text = f"📁 {node.name}"
            tooltip = str(node.path)
        item = QStandardItem(text)
        item.setEditable(False)
        item.setToolTip(tooltip)
        item.setData((str(node.path), node.kind), Qt.ItemDataRole.UserRole)
        if node.kind == "file":
            if node.parse_error:
                item.setForeground(QBrush(QColor(COLOR_WARNING)))
            elif node.run_success is True:
                item.setForeground(QBrush(QColor(COLOR_SUCCESS)))
            elif node.run_success is False:
                item.setForeground(QBrush(QColor(COLOR_ERROR)))
            else:
                item.setForeground(QBrush(QColor(COLOR_MUTED)))
        return item

    def _make_branch(self, node: CatalogNode) -> QStandardItem:
        item = self._make_item(node)
        for child in node.children:
            item.appendRow(self._make_branch(child))
        return item


class CatalogPanel(QWidget):
    _PAGE_TREE = 0
    _PAGE_EMPTY = 1

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setProperty("role", "catalog-panel")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._stack = QStackedWidget(self)
        layout.addWidget(self._stack, stretch=1)

        self.tree = CatalogTreeView(self)
        self._stack.addWidget(self.tree)

        self._empty = CatalogEmptyState(self)
        self._stack.addWidget(self._empty)

    def bind_activate(self, handler) -> None:
        self.tree.set_activate_handler(handler)

    def bind_expansion(self, handler) -> None:
        self.tree.set_expansion_handler(handler)

    def display_state(
        self,
        state: CatalogViewState,
        *,
        collapsed: set[str] | None = None,
        run_selection: frozenset[str] | None = None,
    ) -> None:
        if state.show_empty_message:
            self._empty.set_state(
                state.empty_title or "",
                state.empty_hint or "",
                state.empty_kind,
            )
            self._stack.setCurrentIndex(self._PAGE_EMPTY)
            return

        self._stack.setCurrentIndex(self._PAGE_TREE)
        if state.tree is not None:
            self.tree.show_tree(
                state.tree,
                collapsed=collapsed or set(),
                expand_all=state.expand_all,
                run_selection=run_selection,
            )
        else:
            self.tree.setModel(None)

    def display_tree(self, tree: CatalogNode | None) -> None:
        """Backward-compatible wrapper."""
        from app.mvc.models.catalog_model import CatalogViewState

        self.display_state(CatalogViewState(tree=tree))

    def set_selection_mode(self, enabled: bool) -> None:
        self.tree.set_selection_mode(enabled)
