"""Steps table with edit controls."""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QSizePolicy,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from app.step_display import format_step_table_cells


class _StepsTableModel(QAbstractTableModel):
    HEADERS = ("#", "Действие", "Элемент", "Значение")

    def __init__(self) -> None:
        super().__init__()
        self._steps: list[dict[str, Any]] = []

    def set_steps(self, steps: list[dict[str, Any]]) -> None:
        self.beginResetModel()
        self._steps = list(steps)
        self.endResetModel()

    def step_at(self, row: int) -> dict[str, Any] | None:
        if 0 <= row < len(self._steps):
            return self._steps[row]
        return None

    def rowCount(self, parent=None) -> int:  # noqa: N802
        return len(self._steps)

    def columnCount(self, parent=None) -> int:  # noqa: N802
        return len(self.HEADERS)

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):  # noqa: N802
        if role == Qt.ItemDataRole.DisplayRole and orientation == Qt.Orientation.Horizontal:
            return self.HEADERS[section]
        return None

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):  # noqa: N802
        if not index.isValid():
            return None
        step = self._steps[index.row()]
        if role == Qt.ItemDataRole.DisplayRole:
            if index.column() == 0:
                return str(index.row() + 1)
            cells = format_step_table_cells(step)
            return cells[index.column() - 1]
        return None


class StepsStrip(QWidget):
    step_selected = Signal(int)
    fix_menu_clicked = Signal(int)
    step_move_up = Signal(int)
    step_move_down = Signal(int)
    step_edit = Signal(int)
    step_delete = Signal(int)
    collapse_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setProperty("role", "steps-strip")
        self.setMinimumHeight(80)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        header = QHBoxLayout()
        header.setContentsMargins(8, 2, 8, 2)
        title = QLabel("Шаги")
        title.setStyleSheet("font-size: 8pt; font-weight: 600;")
        header.addWidget(title)

        self._collapse_btn = QPushButton("▼")
        self._collapse_btn.setFixedWidth(28)
        self._collapse_btn.setToolTip("Скрыть панель шагов")
        self._collapse_btn.clicked.connect(self.collapse_requested.emit)
        header.addWidget(self._collapse_btn)
        header.addStretch()

        self._up_btn = QPushButton("↑")
        self._up_btn.setFixedWidth(28)
        self._up_btn.setToolTip("Переместить шаг выше")
        self._up_btn.clicked.connect(lambda: self._emit_row_signal(self.step_move_up))
        header.addWidget(self._up_btn)

        self._down_btn = QPushButton("↓")
        self._down_btn.setFixedWidth(28)
        self._down_btn.setToolTip("Переместить шаг ниже")
        self._down_btn.clicked.connect(lambda: self._emit_row_signal(self.step_move_down))
        header.addWidget(self._down_btn)

        self._edit_btn = QPushButton("Изм.")
        self._edit_btn.setToolTip("Изменить шаг")
        self._edit_btn.clicked.connect(lambda: self._emit_row_signal(self.step_edit))
        header.addWidget(self._edit_btn)

        self._delete_btn = QPushButton("Удал.")
        self._delete_btn.setToolTip("Удалить шаг")
        self._delete_btn.clicked.connect(lambda: self._emit_row_signal(self.step_delete))
        header.addWidget(self._delete_btn)

        self._fix_btn = QPushButton("Починить меню")
        self._fix_btn.setToolTip("Добавить наведение для выбранного клика")
        self._fix_btn.hide()
        self._fix_btn.clicked.connect(self._on_fix_menu)
        header.addWidget(self._fix_btn)
        layout.addLayout(header)

        self._table = QTableView()
        self._model = _StepsTableModel()
        self._table.setModel(self._model)
        self._table.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QTableView.SelectionMode.SingleSelection)
        self._table.setEditTriggers(QTableView.EditTrigger.NoEditTriggers)
        self._table.verticalHeader().hide()
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self._table.setMinimumHeight(48)
        self._table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._table.setShowGrid(False)
        self._table.clicked.connect(self._on_row_clicked)
        self._table.selectionModel().selectionChanged.connect(self._on_selection_changed)
        layout.addWidget(self._table)

        self._selected_row = -1
        self._update_actions()

    def step_count(self) -> int:
        return self._model.rowCount()

    def set_steps(self, steps: list[dict[str, Any]]) -> None:
        self._model.set_steps(steps)
        self._fix_btn.hide()
        self._selected_row = -1
        self._update_actions()

    def highlight_step(self, index: int) -> None:
        row = index - 1
        if 0 <= row < self._model.rowCount():
            self._table.selectRow(row)
            self._table.scrollTo(self._model.index(row, 0))

    def select_row(self, row: int) -> None:
        if 0 <= row < self._model.rowCount():
            self._table.selectRow(row)
            self._selected_row = row
            self._update_actions()

    def _emit_row_signal(self, signal) -> None:
        if self._selected_row >= 0:
            signal.emit(self._selected_row)

    def _on_row_clicked(self, index) -> None:
        row = index.row()
        self._selected_row = row
        self.step_selected.emit(row + 1)
        self._update_actions()

    def _on_selection_changed(self) -> None:
        indexes = self._table.selectionModel().selectedRows()
        if indexes:
            self._selected_row = indexes[0].row()
        else:
            self._selected_row = -1
        self._update_actions()

    def _update_actions(self) -> None:
        row = self._selected_row
        count = self._model.rowCount()
        has_row = 0 <= row < count
        self._up_btn.setEnabled(has_row and row > 0)
        self._down_btn.setEnabled(has_row and row < count - 1)
        self._edit_btn.setEnabled(has_row)
        self._delete_btn.setEnabled(has_row)
        step = self._model.step_at(row) if has_row else None
        self._fix_btn.setVisible(step is not None and step.get("action") == "click")

    def _on_fix_menu(self) -> None:
        if self._selected_row >= 0:
            self.fix_menu_clicked.emit(self._selected_row + 1)
