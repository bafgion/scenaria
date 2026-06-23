"""VS Code–style command palette."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence
from PySide6.QtWidgets import (
    QDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
)

from app.qt.labels import muted_label
from app.qt.widgets.base_dialog import BaseAppDialog


@dataclass(frozen=True)
class PaletteCommand:
    id: str
    label: str
    shortcut: str
    run: Callable[[], None]


def _label_tokens(label: str) -> list[str]:
    for ch in "…()[]":
        label = label.replace(ch, " ")
    return [part for part in label.lower().split() if part]


def match_score(query: str, label: str) -> int | None:
    needle = query.strip().lower()
    if not needle:
        return 0
    hay = label.lower()
    if needle in hay:
        return 1000 - hay.index(needle)
    if len(needle) >= 3:
        stem = needle[: min(4, len(needle))]
        for token in _label_tokens(label):
            if token.startswith(stem) or stem.startswith(token[: len(stem)]):
                return 700 - len(token)
    pos = 0
    for char in hay:
        if pos < len(needle) and char == needle[pos]:
            pos += 1
    if pos == len(needle):
        return 500 - len(hay)
    return None


def filter_commands(
    query: str,
    commands: list[PaletteCommand],
    *,
    recent_ids: list[str] | None = None,
) -> list[PaletteCommand]:
    recent = {item: index for index, item in enumerate(recent_ids or [])}
    scored: list[tuple[int, int, str, PaletteCommand]] = []
    for command in commands:
        score = match_score(query, command.label)
        if score is None:
            continue
        if command.id in recent:
            score += 200 - recent[command.id]
        scored.append((score, recent.get(command.id, 999), command.label.lower(), command))
    scored.sort(key=lambda item: (-item[0], item[1], item[2]))
    return [item[3] for item in scored]


class CommandPaletteDialog(BaseAppDialog):
    def __init__(
        self,
        commands: list[PaletteCommand],
        *,
        recent_ids: list[str] | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent, title="Команды", min_size=(560, 360))
        self._commands = commands
        self._recent_ids = list(recent_ids or [])
        self._selected: PaletteCommand | None = None

        self.content_layout.addWidget(muted_label("Введите название команды"))

        self._filter = QLineEdit()
        self._filter.setPlaceholderText("Поиск команд…")
        self._filter.textChanged.connect(self._refresh_list)
        self.content_layout.addWidget(self._filter)

        self._list = QListWidget()
        self._list.setProperty("role", "settings-list")
        self._list.itemActivated.connect(self._accept_item)
        self._list.itemDoubleClicked.connect(self._accept_item)
        self.content_layout.addWidget(self._list, stretch=1)

        buttons = self.add_close_box()
        buttons.accepted.connect(self._accept_current)
        buttons.rejected.connect(self.reject)

        self._refresh_list()
        self._filter.setFocus()

    def selected_command(self) -> PaletteCommand | None:
        return self._selected

    def _matches(self) -> list[PaletteCommand]:
        return filter_commands(self._filter.text(), self._commands, recent_ids=self._recent_ids)

    def _refresh_list(self) -> None:
        self._list.clear()
        for command in self._matches():
            display = command.label
            if command.shortcut:
                display = f"{command.label}\t{command.shortcut}"
            item = QListWidgetItem(display)
            item.setData(Qt.ItemDataRole.UserRole, command)
            if command.shortcut:
                item.setToolTip(command.shortcut)
            self._list.addItem(item)
        if self._list.count() > 0:
            self._list.setCurrentRow(0)

    def _accept_item(self, item: QListWidgetItem) -> None:
        command = item.data(Qt.ItemDataRole.UserRole)
        if isinstance(command, PaletteCommand):
            self._selected = command
            self.accept()

    def _accept_current(self) -> None:
        item = self._list.currentItem()
        if item is None:
            return
        self._accept_item(item)

    def keyPressEvent(self, event) -> None:  # noqa: N802
        if event.key() in {Qt.Key.Key_Return, Qt.Key.Key_Enter}:
            self._accept_current()
            return
        super().keyPressEvent(event)


def open_command_palette(
    parent,
    commands: list[PaletteCommand],
    *,
    recent_ids: list[str] | None = None,
) -> PaletteCommand | None:
    dialog = CommandPaletteDialog(commands, recent_ids=recent_ids, parent=parent)
    if dialog.exec() != QDialog.DialogCode.Accepted:
        return None
    return dialog.selected_command()


def normalize_menu_label(text: str) -> str:
    return text.replace("&", "").strip()


def shortcut_text(action) -> str:
    seq = action.shortcut()
    if seq.isEmpty():
        return ""
    return seq.toString(QKeySequence.SequenceFormat.PortableText)
