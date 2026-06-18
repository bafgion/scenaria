"""Four-step workflow strip (browser → record → test → save)."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QWidget

from app.qt.theme import COLOR_BORDER, COLOR_MUTED, COLOR_PRIMARY, COLOR_SUCCESS, COLOR_WARNING


class WorkflowStrip(QWidget):
    browser_clicked = Signal()
    record_clicked = Signal()
    test_clicked = Signal()
    save_clicked = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setProperty("role", "workflow-strip")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(6)

        self._steps: list[tuple[str, QPushButton, Signal]] = []
        for index, (label, signal) in enumerate(
            (
                ("1. Браузер", self.browser_clicked),
                ("2. Запись", self.record_clicked),
                ("3. Проверка", self.test_clicked),
                ("4. Сохранение", self.save_clicked),
            )
        ):
            if index:
                arrow = QLabel("→")
                arrow.setStyleSheet(f"color: {COLOR_MUTED};")
                layout.addWidget(arrow)
            btn = QPushButton(label)
            btn.setProperty("workflow", True)
            btn.clicked.connect(signal.emit)
            layout.addWidget(btn)
            self._steps.append((label, btn, signal))

        layout.addStretch()

    def sync_state(
        self,
        *,
        pending: bool,
        browser_open: bool,
        recording: bool,
        playing: bool,
        has_steps: bool,
        unapplied: bool,
        file_unsaved: bool,
    ) -> None:
        for _label, btn, _signal in self._steps:
            btn.setEnabled(not pending and not playing)

        browser_btn = self._steps[0][1]
        record_btn = self._steps[1][1]
        test_btn = self._steps[2][1]
        save_btn = self._steps[3][1]

        if not pending:
            browser_btn.setEnabled(not browser_open and not recording)
            record_btn.setEnabled(browser_open and not recording)
            test_btn.setEnabled(not recording and has_steps and not unapplied)
            save_btn.setEnabled(not recording and (file_unsaved or unapplied))

        active = 0
        if browser_open or recording:
            active = 1
        if recording:
            active = 1
        elif browser_open and has_steps:
            active = 2
        elif browser_open:
            active = 1
        if has_steps and not recording and not playing and not unapplied:
            active = 3 if file_unsaved else 2
        if file_unsaved or unapplied:
            active = max(active, 3)

        for index, (_label, btn, _signal) in enumerate(self._steps):
            if index == active:
                btn.setStyleSheet(
                    f"border: 1px solid {COLOR_PRIMARY}; background: #094771; padding: 2px 8px;"
                )
            elif index == active + 1 and not pending:
                btn.setStyleSheet(
                    f"border: 1px dashed {COLOR_WARNING}; padding: 2px 8px;"
                )
            else:
                btn.setStyleSheet(f"border: 1px solid {COLOR_BORDER}; padding: 2px 8px;")

        if recording:
            record_btn.setStyleSheet(
                f"border: 1px solid #f14c4c; background: #5a1d1d; padding: 2px 8px;"
            )
        if playing:
            test_btn.setStyleSheet(
                f"border: 1px solid {COLOR_PRIMARY}; background: #094771; padding: 2px 8px;"
            )

        tips = {
            0: "Откройте браузер на стартовом URL",
            1: "Запишите действия в браузере",
            2: "Запустите тест или проверьте селекторы",
            3: "Примените Gherkin и сохраните файл",
        }
        for index, (_label, btn, _signal) in enumerate(self._steps):
            extra = tips.get(index, "")
            if index == 1 and not browser_open:
                btn.setToolTip("Сначала откройте браузер")
            elif index == 2 and unapplied:
                btn.setToolTip("Сначала примените Gherkin (Ctrl+Shift+S)")
            elif index == 2 and not has_steps:
                btn.setToolTip("Нет шагов — запишите или введите сценарий")
            else:
                btn.setToolTip(extra)
