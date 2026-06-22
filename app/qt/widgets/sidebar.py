"""Explorer sidebar."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QLineEdit, QSizePolicy, QToolButton, QVBoxLayout, QWidget

from app.mvc.controllers.catalog_controller import CatalogController
from app.mvc.models.catalog_model import CatalogModel, CatalogViewState
from app.qt import icons
from app.qt.widgets.catalog_panel import CatalogPanel
from app.settings import load_settings, save_settings


class Sidebar(QWidget):
    run_selected_requested = Signal()
    run_folder_requested = Signal(object)  # Path
    run_history_requested = Signal(object)  # Path
    run_file_requested = Signal(object)  # Path
    run_vanessa_file_requested = Signal(object)  # Path
    run_vanessa_folder_requested = Signal(object)  # Path
    run_folder_history_requested = Signal(object)  # Path

    def __init__(
        self,
        model: CatalogModel,
        controller: CatalogController,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._model = model
        self._selection_mode = False
        self._tree_visible = False
        self.setProperty("role", "sidebar")
        self.setMinimumWidth(120)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        header = QWidget(self)
        header.setProperty("role", "sidebar-header")
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(8, 6, 8, 6)
        header_layout.setSpacing(4)

        title = QLabel("СЦЕНАРИИ")
        title.setProperty("role", "zone-title")
        header_layout.addWidget(title)

        search_row = QHBoxLayout()
        search_row.setSpacing(4)
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Поиск или @тег")
        self.search_edit.textChanged.connect(controller.set_filter)
        search_row.addWidget(self.search_edit, stretch=1)
        self.new_btn = QToolButton()
        self.new_btn.setIcon(icons.icon("plus", size=icons.SIZE_MD))
        self.new_btn.setIconSize(icons.icon_size(icons.SIZE_MD))
        self.new_btn.setFixedSize(24, 24)
        self.new_btn.setAutoRaise(True)
        self.new_btn.setProperty("compact-icon", True)
        self.new_btn.setToolTip("Новый сценарий")
        search_row.addWidget(self.new_btn)
        self._selection_mode_btn = QToolButton()
        self._selection_mode_btn.setText("Выбор")
        self._selection_mode_btn.setCheckable(True)
        self._selection_mode_btn.setAutoRaise(True)
        self._selection_mode_btn.setToolTip("Режим выбора сценариев для пакетного запуска")
        self._selection_mode_btn.toggled.connect(self._on_selection_mode_toggled)
        search_row.addWidget(self._selection_mode_btn)
        header_layout.addLayout(search_row)

        self._run_row = QWidget(header)
        run_row_layout = QHBoxLayout(self._run_row)
        run_row_layout.setContentsMargins(0, 0, 0, 0)
        run_row_layout.setSpacing(4)
        self.run_selection_label = QLabel("Выбрано для запуска: 0")
        self.run_selection_label.setProperty("role", "muted")
        run_row_layout.addWidget(self.run_selection_label, stretch=1)
        self.clear_run_selection_btn = QToolButton()
        self.clear_run_selection_btn.setText("×")
        self.clear_run_selection_btn.setFixedSize(24, 24)
        self.clear_run_selection_btn.setAutoRaise(True)
        self.clear_run_selection_btn.setToolTip("Снять выбор")
        self.clear_run_selection_btn.clicked.connect(model.clear_run_selection)
        run_row_layout.addWidget(self.clear_run_selection_btn)
        self.run_selected_btn = QToolButton()
        self.run_selected_btn.setIcon(icons.play_icon())
        self.run_selected_btn.setIconSize(icons.icon_size(icons.SIZE_MD))
        self.run_selected_btn.setFixedSize(24, 24)
        self.run_selected_btn.setAutoRaise(True)
        self.run_selected_btn.setProperty("compact-icon", True)
        self.run_selected_btn.setToolTip("Запустить выбранные сценарии")
        self.run_selected_btn.clicked.connect(self.run_selected_requested.emit)
        run_row_layout.addWidget(self.run_selected_btn)
        header_layout.addWidget(self._run_row)

        self._batch_hint = QLabel(
            "Кликните «Выбор» или Ctrl+клик по файлу — пакетный запуск"
        )
        self._batch_hint.setProperty("role", "muted")
        self._batch_hint.setWordWrap(True)
        self._batch_hint.setStyleSheet("font-size: 8pt; padding-top: 2px;")
        header_layout.addWidget(self._batch_hint)

        layout.addWidget(header)

        self.catalog_panel = CatalogPanel(self)
        self.catalog_panel.bind_activate(controller.on_tree_activated)
        self.catalog_panel.bind_expansion(self._on_tree_expansion)
        self.catalog_panel.tree.set_toggle_run_selection_handler(controller.toggle_run_selection)
        self.catalog_panel.tree.run_folder_requested.connect(self.run_folder_requested.emit)
        self.catalog_panel.tree.run_history_requested.connect(self.run_history_requested.emit)
        self.catalog_panel.tree.run_file_requested.connect(self.run_file_requested.emit)
        self.catalog_panel.tree.run_vanessa_file_requested.connect(self.run_vanessa_file_requested.emit)
        self.catalog_panel.tree.run_vanessa_folder_requested.connect(self.run_vanessa_folder_requested.emit)
        self.catalog_panel.tree.run_folder_history_requested.connect(self.run_folder_history_requested.emit)
        self.catalog_panel.tree.add_folder_to_selection_requested.connect(
            controller.add_folder_to_run_selection
        )
        layout.addWidget(self.catalog_panel, stretch=1)

        model.tree_changed.connect(self._on_tree_changed)
        model.run_selection_changed.connect(self._on_run_selection_changed)

        self._update_run_selection_ui()
        self._update_batch_hint()

    def _on_selection_mode_toggled(self, checked: bool) -> None:
        self._selection_mode = checked
        self.catalog_panel.set_selection_mode(checked)
        self._model.refresh_tree()

    def _on_run_selection_changed(self) -> None:
        if self._model.run_selection_count > 0:
            self._dismiss_batch_hint()
        self._update_run_selection_ui()
        self.catalog_panel.tree.update_run_selection_marks(self._model.run_selection_keys)

    def _on_tree_expansion(self, key: str, collapsed: bool) -> None:
        self._model.set_collapsed(key, collapsed)

    def _on_tree_changed(self, state: object) -> None:
        if isinstance(state, CatalogViewState):
            self._tree_visible = state.tree is not None and not state.show_empty_message
            self.catalog_panel.display_state(
                state,
                collapsed=self._model.collapsed_keys,
                run_selection=self._model.run_selection_keys,
            )
        else:
            self._tree_visible = False
            self.catalog_panel.display_tree(None)
        self._update_batch_hint()

    def _update_run_selection_ui(self) -> None:
        count = self._model.run_selection_count
        self.run_selection_label.setText(f"Выбрано для запуска: {count}")
        enabled = count > 0
        self.run_selected_btn.setEnabled(enabled)
        self.clear_run_selection_btn.setEnabled(enabled)

    def _update_batch_hint(self) -> None:
        dismissed = bool(load_settings().get("catalog_batch_hint_dismissed"))
        visible = self._tree_visible and not dismissed and self._model.run_selection_count == 0
        self._batch_hint.setVisible(visible)

    def _dismiss_batch_hint(self) -> None:
        settings = load_settings()
        if settings.get("catalog_batch_hint_dismissed"):
            return
        settings["catalog_batch_hint_dismissed"] = True
        save_settings(settings)
        self._update_batch_hint()
