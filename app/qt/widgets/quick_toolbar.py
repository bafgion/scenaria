"""Two-row toolbar: primary actions with labels and secondary tools."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QSizePolicy, QToolButton, QVBoxLayout, QWidget

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
        self.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)

        root = QVBoxLayout(self)
        root.setContentsMargins(6, 2, 6, 2)
        root.setSpacing(2)

        primary_row = QHBoxLayout()
        primary_row.setContentsMargins(0, 0, 0, 0)
        primary_row.setSpacing(4)
        primary_row.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        secondary_row = QHBoxLayout()
        secondary_row.setContentsMargins(0, 0, 0, 0)
        secondary_row.setSpacing(4)
        secondary_row.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        self._buttons: dict[str, QToolButton] = {}
        self._default_tooltips: dict[str, str] = {}
        self._button_labels: dict[str, str] = {}
        self._compact = False
        self._compact_threshold = 980

        self._add_btn(
            primary_row,
            "browser",
            icons.toolbar_icon("browser"),
            "Браузер",
            "Открыть браузер на стартовом адресе (Ctrl+B)",
            self.browser_clicked,
            primary=True,
        )
        self._add_btn(
            primary_row,
            "record",
            icons.record_icon(),
            "Запись",
            "Начать запись действий на сайте (Ctrl+R)",
            self.record_clicked,
            primary=True,
        )
        self._add_btn(
            primary_row,
            "stop",
            icons.stop_icon(),
            "Стоп",
            "Остановить запись, тест или браузер",
            self.stop_clicked,
            primary=True,
        )
        self._add_btn(
            primary_row,
            "play",
            icons.play_icon(),
            "Запустить",
            "Прогнать сценарий в браузере (Ctrl+Enter)",
            self.play_clicked,
            primary=True,
        )
        self._add_btn(
            primary_row,
            "save",
            icons.toolbar_icon("save"),
            "Сохранить",
            "Сохранить файл сценария (Ctrl+S)",
            self.save_clicked,
            primary=True,
        )
        primary_row.addStretch()

        self._add_btn(
            secondary_row,
            "pause",
            icons.pause_icon(),
            "Пауза",
            "Приостановить запись",
            self.pause_clicked,
            primary=False,
        )
        self._add_separator(secondary_row)
        self._add_btn(
            secondary_row,
            "focus_browser",
            icons.toolbar_icon("browser_focus"),
            "Показать браузер",
            "Переключиться на окно браузера",
            self.focus_browser_clicked,
            primary=False,
        )
        self._add_btn(
            secondary_row,
            "validate",
            icons.toolbar_icon("validate"),
            "Проверить элементы",
            "Убедиться, что все элементы сценария находятся на странице",
            self.validate_clicked,
            primary=False,
        )
        self._add_btn(
            secondary_row,
            "picker",
            icons.toolbar_icon("picker"),
            "Указать элемент",
            "Выбрать элемент на странице для шага сценария",
            self.picker_clicked,
            primary=False,
        )
        self._add_btn(
            secondary_row,
            "quick_record",
            icons.quick_record_icon(),
            "Быстрая запись",
            "Открыть браузер и сразу начать запись",
            self.quick_record_clicked,
            primary=False,
        )
        self._add_btn(
            secondary_row,
            "check",
            icons.toolbar_icon("check"),
            "Проверить текст",
            "Проверить синтаксис текста сценария",
            self.check_clicked,
            primary=False,
        )
        self._add_btn(
            secondary_row,
            "undo",
            icons.toolbar_icon("undo"),
            "Отменить шаг",
            "Убрать последний записанный шаг",
            self.undo_step_clicked,
            primary=False,
        )
        self._add_separator(secondary_row)
        self._add_btn(
            secondary_row,
            "log",
            icons.toolbar_icon("log"),
            "Журнал",
            "Открыть журнал выполнения",
            self.log_clicked,
            primary=False,
        )
        self._add_btn(
            secondary_row,
            "results",
            icons.toolbar_icon("results"),
            "Результаты",
            "Показать результаты последнего теста",
            self.results_clicked,
            primary=False,
        )
        secondary_row.addStretch()

        root.addLayout(primary_row)
        root.addLayout(secondary_row)

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        compact = self.width() < self._compact_threshold
        if compact != self._compact:
            self._compact = compact
            self._apply_layout_mode()

    def _apply_layout_mode(self) -> None:
        for key, btn in self._buttons.items():
            label = self._button_labels[key]
            is_primary = bool(btn.property("toolbar-primary"))
            if self._compact and not is_primary:
                btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
                btn.setText("")
            else:
                btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
                btn.setText(label)

    def _add_btn(
        self,
        layout: QHBoxLayout,
        key: str,
        qicon,
        label: str,
        tooltip: str,
        signal,
        *,
        primary: bool,
    ) -> QToolButton:
        btn = QToolButton(self)
        btn.setIcon(qicon)
        btn.setText(label)
        btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        btn.setIconSize(icons.icon_size(16 if primary else 14))
        btn.setToolTip(tooltip)
        btn.setAutoRaise(True)
        btn.setProperty("toolbar-primary" if primary else "toolbar-secondary", True)
        if primary:
            btn.setMinimumHeight(26)
        else:
            btn.setMinimumHeight(22)
        btn.clicked.connect(signal.emit)
        layout.addWidget(btn, 0, Qt.AlignmentFlag.AlignVCenter)
        self._buttons[key] = btn
        self._button_labels[key] = label
        self._default_tooltips[key] = tooltip
        return btn

    def _add_separator(self, layout: QHBoxLayout) -> None:
        line = QFrame(self)
        line.setFrameShape(QFrame.Shape.VLine)
        line.setStyleSheet(f"color: {COLOR_BORDER};")
        line.setFixedSize(1, 16)
        layout.addWidget(line, 0, Qt.AlignmentFlag.AlignVCenter)

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
        self._buttons["play"].setEnabled(can_play and not unapplied)
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
            self._buttons["play"].setToolTip("Нет шагов — запишите действия или введите сценарий")
        elif unapplied:
            self._buttons["play"].setToolTip("Исправьте ошибки в тексте сценария")
