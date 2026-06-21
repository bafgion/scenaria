"""Step help catalog: search, categories, insert on double-click."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSplitter,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from app.step_catalog import CATEGORY_LABELS, StepEntry, format_entry_help, list_step_entries


class StepHelpPanel(QDialog):
    def __init__(
        self,
        parent: QWidget | None,
        *,
        editor=None,
        focus_entry: StepEntry | None = None,
        initial_search: str = "",
    ) -> None:
        super().__init__(parent)
        self._editor = editor
        self._focus_entry = focus_entry
        self.setWindowTitle("Справка по шагам")
        self.setMinimumSize(720, 520)

        root = QVBoxLayout(self)

        filters = QHBoxLayout()
        self._category = QComboBox()
        for key, label in CATEGORY_LABELS.items():
            self._category.addItem(label, key)
        self._category.currentIndexChanged.connect(self._refresh_list)
        filters.addWidget(QLabel("Категория:"))
        filters.addWidget(self._category)

        self._search = QLineEdit()
        self._search.setPlaceholderText("Поиск по названию, действию или примеру…")
        self._search.setText(initial_search)
        self._search.textChanged.connect(self._refresh_list)
        filters.addWidget(self._search, stretch=1)
        root.addLayout(filters)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        self._list = QListWidget()
        self._list.itemActivated.connect(self._insert_selected)
        self._list.currentItemChanged.connect(self._on_selection_changed)
        splitter.addWidget(self._list)

        self._detail = QTextBrowser()
        self._detail.setOpenExternalLinks(True)
        splitter.addWidget(self._detail)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        root.addWidget(splitter)

        buttons = QHBoxLayout()
        insert_btn = QPushButton("Вставить")
        insert_btn.setDefault(True)
        insert_btn.clicked.connect(self._insert_selected)
        buttons.addWidget(insert_btn)
        buttons.addStretch()
        close_btn = QPushButton("Закрыть")
        close_btn.clicked.connect(self.reject)
        buttons.addWidget(close_btn)
        root.addLayout(buttons)

        self._refresh_list()
        if focus_entry is not None:
            self._select_entry(focus_entry)

    def _refresh_list(self) -> None:
        category = str(self._category.currentData() or "all")
        items = list_step_entries(query=self._search.text(), category=category)
        self._list.clear()
        for entry in items:
            row = QListWidgetItem(f"{entry.label}  ({entry.action})")
            row.setData(Qt.ItemDataRole.UserRole, entry)
            row.setToolTip(entry.description)
            self._list.addItem(row)
        if self._list.count():
            self._list.setCurrentRow(0)

    def _select_entry(self, entry: StepEntry) -> None:
        for row in range(self._list.count()):
            item = self._list.item(row)
            if item is None:
                continue
            data = item.data(Qt.ItemDataRole.UserRole)
            if isinstance(data, StepEntry) and data.id == entry.id:
                self._list.setCurrentItem(item)
                return
        index = self._category.findData(entry.category)
        if index >= 0:
            self._category.setCurrentIndex(index)
        self._search.setText(entry.label)
        self._refresh_list()
        self._select_entry(entry)

    def _current_entry(self) -> StepEntry | None:
        item = self._list.currentItem()
        if item is None:
            return None
        entry = item.data(Qt.ItemDataRole.UserRole)
        return entry if isinstance(entry, StepEntry) else None

    def _on_selection_changed(self) -> None:
        entry = self._current_entry()
        if entry is None:
            self._detail.clear()
            return
        self._detail.setHtml(format_entry_help(entry))

    def _insert_selected(self) -> None:
        entry = self._current_entry()
        if entry is None or self._editor is None:
            return
        self._editor._insert_snippet_at_cursor(entry.snippet)
        self.accept()


def open_step_help_panel(
    parent: QWidget | None,
    *,
    editor=None,
    focus_entry: StepEntry | None = None,
    initial_search: str = "",
) -> None:
    dialog = StepHelpPanel(
        parent,
        editor=editor,
        focus_entry=focus_entry,
        initial_search=initial_search,
    )
    dialog.setWindowModality(Qt.WindowModality.WindowModal)
    dialog.exec()
