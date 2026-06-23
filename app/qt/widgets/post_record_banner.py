"""Post-recording action banner with quality hints."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.qt.labels import caption_label, set_label_tone
from app.scenario_hints import ScenarioHint


def hint_dismiss_key(hint: ScenarioHint) -> str:
    if hint.step_indices:
        return f"{hint.id}:{hint.step_indices[0]}"
    return hint.id


class PostRecordBanner(QWidget):
    apply_and_test_clicked = Signal()
    save_clicked = Signal()
    fix_hover_clicked = Signal()
    dismiss_clicked = Signal()
    hint_fix_requested = Signal(object)  # ScenarioHint
    hint_show_step_requested = Signal(int)  # 1-based step index
    hint_dismiss_requested = Signal(str)  # dismiss key

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setProperty("role", "post-record-banner")
        self.hide()
        self._hints: list[ScenarioHint] = []
        self._all_hints: list[ScenarioHint] = []
        self._dismissed_keys: set[str] = set()
        self._step_count = 0

        root = QVBoxLayout(self)
        root.setContentsMargins(8, 4, 8, 4)
        root.setSpacing(4)

        top = QHBoxLayout()
        top.setSpacing(8)

        self._summary = QLabel("")
        top.addWidget(self._summary, stretch=1)

        self._legacy_hover_hint = caption_label("")
        self._legacy_hover_hint.hide()
        top.addWidget(self._legacy_hover_hint)

        self._fix_btn = QPushButton("Добавить наведение")
        self._fix_btn.hide()
        self._fix_btn.clicked.connect(self.fix_hover_clicked.emit)
        top.addWidget(self._fix_btn)

        test_btn = QPushButton("Проверить")
        test_btn.setProperty("primary", True)
        test_btn.clicked.connect(self.apply_and_test_clicked.emit)
        top.addWidget(test_btn)

        save_btn = QPushButton("Сохранить")
        save_btn.clicked.connect(self.save_clicked.emit)
        top.addWidget(save_btn)

        close_btn = QPushButton("Закрыть")
        close_btn.setProperty("banner-dismiss", True)
        close_btn.clicked.connect(self.dismiss_clicked.emit)
        top.addWidget(close_btn)

        root.addLayout(top)

        self._hints_list = QListWidget(self)
        self._hints_list.setMaximumHeight(120)
        self._hints_list.hide()
        self._hints_list.currentItemChanged.connect(self._on_hint_selection_changed)
        root.addWidget(self._hints_list)

        hint_actions = QHBoxLayout()
        hint_actions.setSpacing(6)
        self._show_step_btn = QPushButton("Показать шаг")
        self._show_step_btn.hide()
        self._show_step_btn.clicked.connect(self._on_show_step)
        hint_actions.addWidget(self._show_step_btn)

        self._fix_hint_btn = QPushButton("Исправить")
        self._fix_hint_btn.hide()
        self._fix_hint_btn.clicked.connect(self._on_fix_hint)
        hint_actions.addWidget(self._fix_hint_btn)

        self._ignore_hint_btn = QPushButton("Игнорировать")
        self._ignore_hint_btn.hide()
        self._ignore_hint_btn.clicked.connect(self._on_ignore_hint)
        hint_actions.addWidget(self._ignore_hint_btn)

        hint_actions.addStretch()
        root.addLayout(hint_actions)

    def show_recording(self, step_count: int, *, hints: list[ScenarioHint] | None = None) -> None:
        self._step_count = step_count
        self._all_hints = list(hints or [])
        visible_hints = [
            hint for hint in self._all_hints if hint_dismiss_key(hint) not in self._dismissed_keys
        ]
        self._hints = visible_hints
        hint_count = len(visible_hints)
        if hint_count:
            self._summary.setText(f"Записано шагов: {step_count} · подсказок: {hint_count}")
        else:
            self._summary.setText(f"Записано шагов: {step_count}")

        menu_hover_count = sum(1 for hint in visible_hints if hint.id == "menu_hover")
        if menu_hover_count:
            self._legacy_hover_hint.setText(
                f"Похоже на hover-меню: {menu_hover_count} клик(ов) без «навожу»"
            )
            set_label_tone(self._legacy_hover_hint, "warning")
            self._legacy_hover_hint.show()
            self._fix_btn.show()
        else:
            self._legacy_hover_hint.hide()
            self._fix_btn.hide()

        self._populate_hints_list(visible_hints)
        self.show()

    def _populate_hints_list(self, hints: list[ScenarioHint]) -> None:
        self._hints_list.blockSignals(True)
        self._hints_list.clear()
        if not hints:
            self._hints_list.hide()
            self._show_step_btn.hide()
            self._fix_hint_btn.hide()
            self._ignore_hint_btn.hide()
            self._hints_list.blockSignals(False)
            return
        for hint in hints:
            step_no = hint.step_indices[0] + 1 if hint.step_indices else 0
            prefix = "⚠ " if hint.severity == "warning" else "ℹ "
            item = QListWidgetItem(f"{prefix}{hint.title}" + (f" (шаг {step_no})" if step_no else ""))
            item.setData(Qt.ItemDataRole.UserRole, hint)
            self._hints_list.addItem(item)

        self._hints_list.setCurrentRow(0)
        self._hints_list.show()
        self._hints_list.blockSignals(False)
        self._on_hint_selection_changed()

    def _on_hint_selection_changed(self, *_args) -> None:
        hint = self.current_hint()
        has_hint = hint is not None
        self._show_step_btn.setVisible(has_hint and bool(hint and hint.step_indices))
        self._fix_hint_btn.setVisible(has_hint and bool(hint and hint.auto_fixable))
        self._ignore_hint_btn.setVisible(has_hint)

    def _on_show_step(self) -> None:
        hint = self.current_hint()
        if hint and hint.step_indices:
            self.hint_show_step_requested.emit(hint.step_indices[0] + 1)

    def _on_fix_hint(self) -> None:
        hint = self.current_hint()
        if hint is not None:
            self.hint_fix_requested.emit(hint)

    def _on_ignore_hint(self) -> None:
        hint = self.current_hint()
        if hint is None:
            return
        key = hint_dismiss_key(hint)
        self._dismissed_keys.add(key)
        self.hint_dismiss_requested.emit(key)
        self.show_recording(self._step_count, hints=self._all_hints)

    def current_hint(self) -> ScenarioHint | None:
        item = self._hints_list.currentItem()
        if item is None:
            return self._hints[0] if self._hints else None
        hint = item.data(Qt.ItemDataRole.UserRole)
        return hint if isinstance(hint, ScenarioHint) else None

    def dismiss_current_hint(self) -> None:
        self._on_ignore_hint()

    def reset_dismissed(self) -> None:
        self._dismissed_keys.clear()

    def hide_banner(self) -> None:
        self._hints_list.clear()
        self._show_step_btn.hide()
        self._fix_hint_btn.hide()
        self._ignore_hint_btn.hide()
        self.hide()
