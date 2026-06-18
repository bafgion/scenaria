"""Horizontal quick-access toolbar (IDE style)."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QSizePolicy, QToolButton, QWidget

from app.qt import icons
from app.qt.theme import COLOR_BORDER


class QuickToolBar(QWidget):
    save_clicked = Signal()
    browser_clicked = Signal()
    focus_browser_clicked = Signal()
    record_clicked = Signal()
    stop_clicked = Signal()
    pause_clicked = Signal()
    play_clicked = Signal()
    validate_clicked = Signal()
    apply_clicked = Signal()
    check_clicked = Signal()
    url_clicked = Signal()
    undo_step_clicked = Signal()
    quick_record_clicked = Signal()
    picker_clicked = Signal()
    log_clicked = Signal()
    results_clicked = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setProperty("role", "quick-toolbar")
        self.setFixedHeight(32)
        self.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 2, 6, 2)
        layout.setSpacing(2)
        layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        self._buttons: dict[str, QToolButton] = {}
        self._default_tooltips: dict[str, str] = {}

        self._add_btn("play", icons.play_icon(), "Запустить тест (Ctrl+Enter)", self.play_clicked)
        self._add_btn("record", icons.record_icon(), "Запись (Ctrl+R)", self.record_clicked)
        self._add_btn("stop", icons.stop_icon(), "Стоп", self.stop_clicked)
        self._add_btn("pause", icons.pause_icon(), "Пауза", self.pause_clicked)
        self._add_separator()
        self._add_btn("browser", icons.toolbar_icon("browser"), "Браузер (Ctrl+B)", self.browser_clicked)
        self._add_btn(
            "focus_browser",
            icons.toolbar_icon("browser_focus"),
            "Показать браузер",
            self.focus_browser_clicked,
        )
        self._add_btn("validate", icons.toolbar_icon("validate"), "Проверить селекторы", self.validate_clicked)
        self._add_btn(
            "picker",
            icons.toolbar_icon("picker"),
            "Указать элемент на странице (селектор)",
            self.picker_clicked,
        )
        self._add_btn(
            "quick_record",
            icons.quick_record_icon(),
            "Быстрая запись: открыть браузер и сразу записать",
            self.quick_record_clicked,
        )
        self._add_separator()
        self._add_btn("save", icons.toolbar_icon("save"), "Сохранить (Ctrl+S)", self.save_clicked)
        self._add_btn("apply", icons.toolbar_icon("apply"), "Применить Gherkin (Ctrl+Shift+S)", self.apply_clicked)
        self._add_btn("check", icons.toolbar_icon("check"), "Проверить Gherkin", self.check_clicked)
        self._add_btn("undo", icons.toolbar_icon("undo"), "Отменить шаг записи", self.undo_step_clicked)
        self._add_separator()
        self._add_btn("log", icons.toolbar_icon("log"), "Журнал", self.log_clicked)
        self._add_btn("results", icons.toolbar_icon("results"), "Результаты", self.results_clicked)

    def _add_btn(self, key: str, qicon, tooltip: str, signal) -> QToolButton:
        btn = QToolButton(self)
        btn.setIcon(qicon)
        btn.setIconSize(icons.icon_size())
        btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        btn.setToolTip(tooltip)
        btn.setAutoRaise(True)
        btn.setProperty("toolbar-icon", True)
        btn.setFixedSize(icons.TOOLBAR_BTN, icons.TOOLBAR_BTN)
        btn.clicked.connect(signal.emit)
        self.layout().addWidget(btn, 0, Qt.AlignmentFlag.AlignVCenter)
        self._buttons[key] = btn
        self._default_tooltips[key] = tooltip
        return btn

    def _add_separator(self) -> None:
        line = QFrame(self)
        line.setFrameShape(QFrame.Shape.VLine)
        line.setStyleSheet(f"color: {COLOR_BORDER};")
        line.setFixedSize(1, 18)
        self.layout().addWidget(line, 0, Qt.AlignmentFlag.AlignVCenter)

    def sync_states(
        self,
        *,
        pending: bool,
        browser_open: bool,
        recorder_browser_open: bool = False,
        player_browser_open: bool = False,
        recording: bool,
        playing: bool,
        has_steps: bool,
        unapplied: bool = False,
        batch_running: bool = False,
        picking: bool = False,
        disable_reasons: dict[str, str] | None = None,
    ) -> None:
        if not recorder_browser_open:
            recorder_browser_open = browser_open
        reasons = disable_reasons or {}
        lock_all = pending and not playing and not batch_running and not picking
        for key, btn in self._buttons.items():
            btn.setEnabled(not lock_all)
            btn.setToolTip(reasons.get(key, self._default_tooltips.get(key, "")))

        if lock_all:
            return

        self._buttons["browser"].setEnabled(not browser_open and not recording and not batch_running)
        self._buttons["focus_browser"].setEnabled(browser_open or playing)
        self._buttons["record"].setEnabled(
            recorder_browser_open and not recording and not playing and not batch_running
        )
        self._buttons["quick_record"].setEnabled(not recording and not playing and not batch_running)
        self._buttons["stop"].setEnabled(
            recording or playing or batch_running or player_browser_open or picking
        )
        self._buttons["pause"].setEnabled(recording)
        can_play = not recording and not playing and has_steps and not batch_running
        self._buttons["play"].setEnabled(can_play)
        self._buttons["validate"].setEnabled(not recording and not playing and not batch_running)
        if not recorder_browser_open:
            recorder_browser_open = browser_open and not player_browser_open
        can_picker = False
        if not recording and not batch_running and not picking:
            if playing:
                can_picker = player_browser_open
            else:
                can_picker = recorder_browser_open or player_browser_open
        self._buttons["picker"].setEnabled(can_picker)
        self._buttons["undo"].setEnabled(recording)

        if not can_play and not has_steps:
            self._buttons["play"].setToolTip("Нет шагов — запишите или введите сценарий")
        elif can_play and unapplied:
            self._buttons["play"].setToolTip("Запуск (Gherkin будет применён автоматически)")
