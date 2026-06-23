"""Step help catalog: search, categories, insert on double-click."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QSplitter,
    QTextBrowser,
    QWidget,
)

from app.help_topics import (
    GUIDE_CATEGORY,
    GUIDE_CATEGORY_LABELS,
    GuideTopic,
    format_guide_help,
    list_guide_topics,
)
from app.qt.dialog_buttons import BTN_CLOSE
from app.qt.widgets.base_dialog import BaseAppDialog, dialog_action_button
from app.step_catalog import CATEGORY_LABELS, StepEntry, format_entry_help, list_step_entries

_HELP_CATEGORY_LABELS: dict[str, str] = {
    **CATEGORY_LABELS,
    **{key: value for key, value in GUIDE_CATEGORY_LABELS.items() if key not in CATEGORY_LABELS},
}


class StepHelpPanel(BaseAppDialog):
    def __init__(
        self,
        parent: QWidget | None,
        *,
        editor=None,
        focus_entry: StepEntry | None = None,
        focus_topic: GuideTopic | None = None,
        initial_search: str = "",
    ) -> None:
        super().__init__(parent, title="Справка", min_size=(720, 520))
        self._editor = editor
        self._focus_entry = focus_entry
        self._focus_topic = focus_topic

        filters = QHBoxLayout()
        self._category = QComboBox()
        for key, label in _HELP_CATEGORY_LABELS.items():
            self._category.addItem(label, key)
        self._category.currentIndexChanged.connect(self._refresh_list)
        filters.addWidget(QLabel("Категория:"))
        filters.addWidget(self._category)

        self._search = QLineEdit()
        self._search.setPlaceholderText("Поиск по шагам, таблицам примеров, .params.json…")
        self._search.setText(initial_search)
        self._search.textChanged.connect(self._refresh_list)
        filters.addWidget(self._search, stretch=1)
        self.content_layout.addLayout(filters)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        self._list = QListWidget()
        self._list.setProperty("role", "settings-list")
        self._list.itemActivated.connect(self._insert_selected)
        self._list.currentItemChanged.connect(self._on_selection_changed)
        splitter.addWidget(self._list)

        self._detail = QTextBrowser()
        self._detail.setProperty("role", "help-detail")
        self._detail.setOpenExternalLinks(True)
        self._detail.setFrameShape(QTextBrowser.Shape.NoFrame)
        self._detail.setPlaceholderText("Выберите тему в списке слева")
        splitter.addWidget(self._detail)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        self.content_layout.addWidget(splitter, stretch=1)

        self._insert_btn = dialog_action_button("Вставить", primary=True, default=True)
        self._insert_btn.clicked.connect(self._insert_selected)
        close_btn = dialog_action_button(BTN_CLOSE)
        close_btn.clicked.connect(self.reject)
        self.add_button_row(self._insert_btn, close_btn)

        self._refresh_list()
        if focus_topic is not None:
            self._select_topic(focus_topic)
        elif focus_entry is not None:
            self._select_entry(focus_entry)

    def _refresh_list(self) -> None:
        category = str(self._category.currentData() or "all")
        query = self._search.text()
        guides = list_guide_topics(query=query, category=category)
        steps = list_step_entries(query=query, category=category)
        self._list.clear()
        for topic in guides:
            row = QListWidgetItem(topic.label)
            row.setData(Qt.ItemDataRole.UserRole, topic)
            row.setToolTip(topic.description)
            self._list.addItem(row)
        for entry in steps:
            row = QListWidgetItem(f"{entry.label}  ({entry.action})")
            row.setData(Qt.ItemDataRole.UserRole, entry)
            row.setToolTip(entry.description)
            self._list.addItem(row)
        if self._list.count():
            self._list.setCurrentRow(0)
        self._on_selection_changed()

    def _select_topic(self, topic: GuideTopic) -> None:
        for row in range(self._list.count()):
            item = self._list.item(row)
            if item is None:
                continue
            data = item.data(Qt.ItemDataRole.UserRole)
            if isinstance(data, GuideTopic) and data.id == topic.id:
                self._list.setCurrentItem(item)
                return
        index = self._category.findData(topic.category)
        if index >= 0:
            self._category.setCurrentIndex(index)
        self._search.setText(topic.label)
        self._refresh_list()
        self._select_topic(topic)

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

    def _current_item(self) -> StepEntry | GuideTopic | None:
        item = self._list.currentItem()
        if item is None:
            return None
        data = item.data(Qt.ItemDataRole.UserRole)
        if isinstance(data, (StepEntry, GuideTopic)):
            return data
        return None

    def _on_selection_changed(self) -> None:
        current = self._current_item()
        if current is None:
            self._detail.clear()
            self._insert_btn.setEnabled(False)
            return
        if isinstance(current, GuideTopic):
            self._detail.setHtml(format_guide_help(current))
            can_insert = self._editor is not None and bool(current.insert_text)
        else:
            self._detail.setHtml(format_entry_help(current))
            can_insert = self._editor is not None
        self._insert_btn.setEnabled(can_insert)
        self._insert_btn.setText("Вставить шаблон" if isinstance(current, GuideTopic) else "Вставить")

    def _insert_selected(self) -> None:
        current = self._current_item()
        if current is None or self._editor is None:
            return
        if isinstance(current, GuideTopic):
            if not current.insert_text:
                return
            cursor = self._editor.textCursor()
            cursor.insertText(current.insert_text)
            self._editor.setTextCursor(cursor)
        else:
            self._editor._insert_snippet_at_cursor(current.snippet)
        self.accept()


def open_step_help_panel(
    parent: QWidget | None,
    *,
    editor=None,
    focus_entry: StepEntry | None = None,
    focus_topic: GuideTopic | None = None,
    initial_search: str = "",
    initial_category: str = "",
) -> None:
    dialog = StepHelpPanel(
        parent,
        editor=editor,
        focus_entry=focus_entry,
        focus_topic=focus_topic,
        initial_search=initial_search,
    )
    if initial_category:
        index = dialog._category.findData(initial_category)
        if index >= 0:
            dialog._category.setCurrentIndex(index)
    dialog.setWindowModality(Qt.WindowModality.WindowModal)
    dialog.exec()
