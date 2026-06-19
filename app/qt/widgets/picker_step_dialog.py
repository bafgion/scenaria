"""Dialog to pick a Gherkin step after element selection in the browser."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.gherkin_picker import PickerStepChoice, picker_step_choices
from app.qt.dialogs import ok_cancel_button_box
from app.qt.fonts import editor_font_css
from app.qt.theme import COLOR_MUTED, COLOR_PRIMARY, COLOR_TEXT


def _center_on_screen(widget: QWidget) -> None:
    screen = QGuiApplication.primaryScreen()
    if screen is None:
        return
    area = screen.availableGeometry()
    frame = widget.frameGeometry()
    frame.moveCenter(area.center())
    widget.move(frame.topLeft())


class PickerStepDialog(QDialog):
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
            Qt.WindowType.Dialog
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.WindowCloseButtonHint,
        )
        self._choices = list(choices or picker_step_choices(selector, keyword=keyword))
        self._selected: PickerStepChoice | None = None

        self.setWindowTitle("Элемент выбран — укажите шаг")
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        self.setMinimumSize(520, 420)

        layout = QVBoxLayout(self)

        preview = selector if len(selector) <= 160 else selector[:157] + "..."
        header = QLabel(f"Селектор:\n{preview}")
        header.setWordWrap(True)
        header.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(header)

        hint = QLabel("Выберите шаг — справа пример строки в сценарии:")
        hint.setStyleSheet(f"color: {COLOR_MUTED};")
        layout.addWidget(hint)

        row = QHBoxLayout()
        self._list = QListWidget()
        self._list.setSpacing(2)
        for choice in self._choices:
            item = QListWidgetItem(choice.label)
            item.setData(Qt.ItemDataRole.UserRole, choice)
            item.setToolTip(choice.description)
            self._list.addItem(item)
        self._list.currentRowChanged.connect(self._on_row_changed)
        self._list.itemDoubleClicked.connect(lambda _item: self.accept())
        row.addWidget(self._list, stretch=2)

        preview_box = QVBoxLayout()
        preview_caption = QLabel("Пример в сценарии")
        preview_caption.setStyleSheet(f"color: {COLOR_MUTED}; font-size: 9pt;")
        preview_box.addWidget(preview_caption)
        self._preview = QLabel("—")
        self._preview.setWordWrap(True)
        self._preview.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self._preview.setStyleSheet(
            f"color: {COLOR_TEXT}; background: #2d2d2d; border: 1px solid #454545;"
            f"padding: 8px; font-family: {editor_font_css()};"
        )
        self._preview.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        preview_box.addWidget(self._preview, stretch=1)
        self._description = QLabel("")
        self._description.setWordWrap(True)
        self._description.setStyleSheet(f"color: {COLOR_MUTED}; font-size: 9pt;")
        preview_box.addWidget(self._description)
        row.addLayout(preview_box, stretch=3)
        layout.addLayout(row, stretch=1)

        buttons = ok_cancel_button_box()
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

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
