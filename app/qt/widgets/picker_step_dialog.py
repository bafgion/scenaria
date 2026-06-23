"""Dialog to pick a Gherkin step after element selection in the browser."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QDialog, QHBoxLayout, QListWidget, QListWidgetItem, QVBoxLayout, QWidget

from app.gherkin_picker import PickerStepChoice, picker_step_choices
from app.qt.labels import caption_label, code_preview_label, dialog_title_label
from app.qt.widgets.base_dialog import BaseAppDialog


def _center_on_screen(widget: QWidget) -> None:
    screen = QGuiApplication.primaryScreen()
    if screen is None:
        return
    area = screen.availableGeometry()
    frame = widget.frameGeometry()
    frame.moveCenter(area.center())
    widget.move(frame.topLeft())


class PickerStepDialog(BaseAppDialog):
    def __init__(
        self,
        parent: QWidget | None,
        *,
        selector: str,
        keyword: str = "Допустим",
        choices: list[PickerStepChoice] | None = None,
    ) -> None:
        super().__init__(
            None,
            title="Элемент выбран — укажите шаг",
            min_size=(520, 420),
        )
        self.setWindowFlags(
            Qt.WindowType.Dialog
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.WindowCloseButtonHint
        )
        self._choices = list(choices or picker_step_choices(selector, keyword=keyword))
        self._selected: PickerStepChoice | None = None

        preview = selector if len(selector) <= 160 else selector[:157] + "..."
        self.content_layout.addWidget(dialog_title_label(f"Селектор:\n{preview}", selectable=True))
        self.content_layout.addWidget(
            caption_label("Выберите шаг — справа пример строки в сценарии:")
        )

        row = QHBoxLayout()
        self._list = QListWidget()
        self._list.setProperty("role", "settings-list")
        for choice in self._choices:
            item = QListWidgetItem(choice.label)
            item.setData(Qt.ItemDataRole.UserRole, choice)
            item.setToolTip(choice.description)
            self._list.addItem(item)
        self._list.currentRowChanged.connect(self._on_row_changed)
        self._list.itemDoubleClicked.connect(lambda _item: self.accept())
        row.addWidget(self._list, stretch=2)

        preview_column = QWidget()
        preview_layout = QVBoxLayout(preview_column)
        preview_layout.setContentsMargins(0, 0, 0, 0)
        preview_layout.addWidget(caption_label("Пример в сценарии"))
        self._preview = code_preview_label("—")
        preview_layout.addWidget(self._preview, stretch=1)
        self._description = caption_label("")
        self._description.setWordWrap(True)
        preview_layout.addWidget(self._description)
        row.addWidget(preview_column, stretch=3)
        self.content_layout.addLayout(row, stretch=1)

        buttons = self.add_ok_cancel()
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        if self._list.count():
            self._list.setCurrentRow(0)

    def showEvent(self, event) -> None:  # noqa: N802
        super().showEvent(event)
        self.raise_()
        self.activateWindow()

    def _on_row_changed(self, row: int) -> None:
        if row < 0 or row >= len(self._choices):
            self._preview.setText("—")
            self._description.setText("")
            return
        choice = self._choices[row]
        self._preview.setText(choice.preview or choice.step_body)
        self._description.setText(choice.description)

    def selected_choice(self) -> PickerStepChoice | None:
        if self._selected is not None:
            return self._selected
        row = self._list.currentRow()
        if row < 0:
            return None
        return self._choices[row]

    def accept(self) -> None:
        row = self._list.currentRow()
        if row < 0:
            return
        self._selected = self._choices[row]
        super().accept()


def pick_picker_step(
    parent: QWidget | None,
    selector: str,
    *,
    keyword: str = "Допустим",
) -> PickerStepChoice | None:
    _ = parent
    dialog = PickerStepDialog(None, selector=selector, keyword=keyword)
    dialog.adjustSize()
    _center_on_screen(dialog)
    if dialog.exec() != QDialog.DialogCode.Accepted:
        return None
    return dialog.selected_choice()
