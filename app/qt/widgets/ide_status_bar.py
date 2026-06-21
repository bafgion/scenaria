"""VS Code–style segmented status bar."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import QHBoxLayout, QLabel, QProgressBar, QPushButton, QWidget

from app.progress_state import ProgressState
from app.qt import icons
from app.qt.theme import COLOR_BORDER, COLOR_MUTED, COLOR_PRIMARY, COLOR_RECORDING, COLOR_SUCCESS, COLOR_TEXT, COLOR_WARNING


class _StatusSegment(QWidget):
    clicked = Signal()

    def __init__(
        self,
        text: str = "",
        *,
        icon_name: str | None = None,
        led: bool = False,
        clickable: bool = False,
        tooltip: str = "",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setProperty("status-segment", True)
        self.setProperty("clickable", "true" if clickable else "false")
        self._clickable = clickable
        self._accent_mode: str | None = None

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 0, 10, 0)
        layout.setSpacing(6)

        self._led = QLabel()
        self._led.setFixedSize(6, 6)
        self._led.hide()
        layout.addWidget(self._led)

        self._icon = QLabel()
        self._icon.setFixedSize(14, 14)
        self._icon.setScaledContents(True)
        self._icon.hide()
        layout.addWidget(self._icon)

        self._label = QLabel(text)
        layout.addWidget(self._label)

        if led:
            self._led.show()
            self.set_led(False)
        if icon_name:
            self.set_icon(icon_name)
        if tooltip:
            self.setToolTip(tooltip)

        self._apply_base_style()
        self.set_muted(not clickable)
        if clickable:
            self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

    def set_text(self, text: str) -> None:
        self._label.setText(text)

    def set_led(self, on: bool) -> None:
        color = COLOR_SUCCESS if on else COLOR_MUTED
        self._led.setStyleSheet(
            f"background: {color}; border-radius: 3px; min-width: 6px; max-width: 6px;"
        )

    def set_muted(self, muted: bool = True) -> None:
        if self._accent_mode:
            return
        color = COLOR_MUTED if muted else COLOR_TEXT
        self._label.setStyleSheet(f"color: {color}; font-size: 8pt;")

    def set_accent(self, *, recording: bool = False, playing: bool = False) -> None:
        if recording:
            self._accent_mode = "recording"
            self.setProperty("accent", "recording")
        elif playing:
            self._accent_mode = "playing"
            self.setProperty("accent", "playing")
        else:
            self._accent_mode = None
            self.setProperty("accent", "")
        self._apply_base_style()
        if self._accent_mode:
            self._label.setStyleSheet("color: #ffffff; font-size: 8pt; font-weight: 600;")
        else:
            self.set_muted(True)

    def set_warning(self) -> None:
        self._accent_mode = None
        self.setProperty("accent", "")
        self._apply_base_style()
        self._label.setStyleSheet(f"color: {COLOR_WARNING}; font-size: 8pt;")

    def set_success(self) -> None:
        self._accent_mode = None
        self.setProperty("accent", "")
        self._apply_base_style()
        self._label.setStyleSheet(f"color: {COLOR_SUCCESS}; font-size: 8pt;")

    def set_icon(self, name: str, *, color: str | None = None) -> None:
        qcolor = color or COLOR_MUTED
        self._icon.setPixmap(icons.icon(name, size=14, color=qcolor).pixmap(14, 14))
        self._icon.show()

    def _apply_base_style(self) -> None:
        self.style().unpolish(self)
        self.style().polish(self)

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if self._clickable and event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
            event.accept()
            return
        super().mousePressEvent(event)


class IdeStatusBar(QWidget):
    panel_clicked = Signal()
    project_clicked = Signal()
    progress_cancelled = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setProperty("role", "ide-status-bar")
        self.setFixedHeight(24)

        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self._message = QLabel("")
        self._message.setProperty("status", "message")
        self._message.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        root.addWidget(self._message, stretch=1)

        self._progress_wrap = QWidget()
        progress_layout = QHBoxLayout(self._progress_wrap)
        progress_layout.setContentsMargins(0, 0, 8, 0)
        progress_layout.setSpacing(6)
        self._progress_bar = QProgressBar()
        self._progress_bar.setFixedHeight(14)
        self._progress_bar.setTextVisible(False)
        self._progress_bar.setMaximum(100)
        progress_layout.addWidget(self._progress_bar, stretch=1)
        self._progress_cancel = QPushButton("Отмена")
        self._progress_cancel.setFixedHeight(20)
        self._progress_cancel.clicked.connect(self._on_progress_cancel)
        progress_layout.addWidget(self._progress_cancel)
        self._progress_wrap.hide()
        root.addWidget(self._progress_wrap)
        self._progress_task_id = ""

        right = QWidget()
        right.setProperty("status", "right")
        right_layout = QHBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        self._session = _StatusSegment(tooltip="Состояние записи или теста")
        self._browser = _StatusSegment(
            "Браузер · закрыт",
            led=True,
            tooltip="Состояние окна браузера для записи и тестов",
        )
        self._steps = _StatusSegment("0 шагов", tooltip="Число шагов в применённом сценарии")
        self._gherkin = _StatusSegment("Ошибка в сценарии", tooltip="В тексте сценария есть синтаксические ошибки")
        self._panel = _StatusSegment(
            "Журнал",
            icon_name="log",
            clickable=True,
            tooltip="Открыть журнал выполнения",
        )
        self._project = _StatusSegment(
            "Открыть проект…",
            icon_name="explorer",
            clickable=True,
            tooltip="Выбрать папку проекта",
        )

        self._panel.clicked.connect(self.panel_clicked.emit)
        self._project.clicked.connect(self.project_clicked.emit)

        for segment in (self._session, self._browser, self._steps, self._gherkin, self._panel, self._project):
            right_layout.addWidget(segment)

        root.addWidget(right)
        self._session.hide()
        self._gherkin.hide()

    def set_message(self, text: str, tone: str = "normal") -> None:
        self._message.setText(text)
        color = COLOR_TEXT
        if tone == "error":
            color = "#f48771"
        elif tone == "success":
            color = COLOR_SUCCESS
        elif tone == "warning":
            color = COLOR_WARNING
        elif tone in ("busy", "muted", "info"):
            color = COLOR_MUTED
        self._message.setStyleSheet(f"color: {color}; padding: 0 12px; font-size: 8pt;")

    def set_progress(self, state: ProgressState | None) -> None:
        if state is None or not state.active:
            self._progress_task_id = ""
            self._progress_wrap.hide()
            return
        self._progress_task_id = state.task_id
        self._progress_bar.setRange(0, state.total)
        self._progress_bar.setValue(max(0, min(state.current, state.total)))
        self._progress_cancel.setVisible(state.cancellable)
        self._progress_wrap.show()
        self.set_message(state.step_label(), "busy")

    def _on_progress_cancel(self) -> None:
        if self._progress_task_id:
            self.progress_cancelled.emit(self._progress_task_id)

    def set_session_state(self, text: str) -> None:
        if not text.strip():
            self._session.hide()
            return
        self._session.show()
        self._session.set_text(text)
        recording = "Запись" in text or "Пауза" in text
        playing = text == "Тест"
        self._session.set_accent(recording=recording, playing=playing)

    def sync(
        self,
        *,
        browser_open: bool,
        recording: bool,
        step_count: int,
        gherkin_unapplied: bool,
        project_label: str,
    ) -> None:
        if browser_open:
            self._browser.set_text("Браузер · открыт")
            self._browser.set_led(True)
            self._browser.set_success()
        else:
            self._browser.set_text("Браузер · закрыт")
            self._browser.set_led(False)
            self._browser.set_muted(True)

        steps_word = "шаг" if step_count % 10 == 1 and step_count % 100 != 11 else "шагов"
        if step_count % 10 in {2, 3, 4} and step_count % 100 not in {12, 13, 14}:
            steps_word = "шага"
        self._steps.set_text(f"{step_count} {steps_word}")
        self._steps.set_muted(step_count == 0)

        if gherkin_unapplied:
            self._gherkin.set_text("Ошибка в сценарии")
            self._gherkin.set_warning()
            self._gherkin.show()
        else:
            self._gherkin.hide()

        if project_label:
            label = project_label
            if len(label) > 28:
                label = "…" + label[-25:]
            self._project.set_text(label)
            self._project.set_muted(False)
            self._project.set_icon("explorer", color=COLOR_TEXT)
        else:
            self._project.set_text("Открыть проект…")
            self._project.set_muted(True)
            self._project.set_icon("explorer", color=COLOR_MUTED)
