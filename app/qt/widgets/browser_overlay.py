"""Floating always-on-top control panel while the browser session is active."""

from __future__ import annotations

from PySide6.QtCore import QPoint, Qt, Signal
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from app.qt import icons
from app.qt.theme import COLOR_BORDER, COLOR_MUTED, COLOR_RECORDING, COLOR_TEXT, COLOR_TOOLBAR
from app.brand import BRAND_NAME


class BrowserOverlayPanel(QWidget):
    record_clicked = Signal()
    stop_clicked = Signal()
    pause_clicked = Signal()
    picker_clicked = Signal()
    focus_browser_clicked = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(
            parent,
            Qt.WindowType.Tool
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.FramelessWindowHint,
        )
        self.setObjectName("browserOverlay")
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, False)
        self._drag_offset: QPoint | None = None

        self.setStyleSheet(
            f"""
            QWidget#browserOverlay {{
                background: {COLOR_TOOLBAR};
                border: 1px solid {COLOR_BORDER};
                border-radius: 8px;
            }}
            QPushButton {{
                min-height: 32px;
                padding: 4px 10px;
                border: 1px solid {COLOR_BORDER};
                border-radius: 6px;
            }}
            QPushButton:hover:enabled {{
                border-color: #5a5a5a;
            }}
            QPushButton:disabled {{
                color: {COLOR_MUTED};
            }}
            """
        )

        root = QVBoxLayout(self)
        root.setContentsMargins(8, 6, 8, 8)
        root.setSpacing(6)

        self._title = QLabel(BRAND_NAME)
        self._title.setStyleSheet(f"color: {COLOR_MUTED}; font-size: 8pt;")
        self._title.setCursor(Qt.CursorShape.SizeAllCursor)
        root.addWidget(self._title)

        row = QHBoxLayout()
        row.setSpacing(6)

        self._btn_record = QPushButton("Запись")
        self._btn_record.setIcon(icons.record_icon())
        self._btn_record.setToolTip("Начать запись действий на сайте")
        self._btn_record.clicked.connect(self.record_clicked.emit)
        row.addWidget(self._btn_record)

        self._btn_pause = QPushButton("Пауза")
        self._btn_pause.setIcon(icons.pause_icon())
        self._btn_pause.setToolTip("Приостановить запись")
        self._btn_pause.clicked.connect(self.pause_clicked.emit)
        row.addWidget(self._btn_pause)

        self._btn_stop = QPushButton("Стоп")
        self._btn_stop.setIcon(icons.stop_icon())
        self._btn_stop.setToolTip("Остановить запись или тест")
        self._btn_stop.clicked.connect(self.stop_clicked.emit)
        row.addWidget(self._btn_stop)

        self._btn_focus = QPushButton("Браузер")
        self._btn_focus.setIcon(icons.toolbar_icon("browser_focus"))
        self._btn_focus.setToolTip("Показать окно браузера")
        self._btn_focus.clicked.connect(self.focus_browser_clicked.emit)
        row.addWidget(self._btn_focus)

        self._btn_picker = QPushButton("Указать элемент")
        self._btn_picker.setIcon(icons.toolbar_icon("picker"))
        self._btn_picker.setToolTip("Выбрать элемент на странице для шага сценария")
        self._btn_picker.clicked.connect(self.picker_clicked.emit)
        row.addWidget(self._btn_picker)

        root.addLayout(row)
        self.adjustSize()
        self._place_default()

    def _place_default(self) -> None:
        screen = QGuiApplication.primaryScreen()
        if screen is None:
            return
        area = screen.availableGeometry()
        self.move(area.right() - self.width() - 20, area.top() + 80)

    def sync_state(
        self,
        *,
        visible: bool,
        recording: bool,
        playing: bool,
        paused: bool,
        recorder_browser: bool,
        player_browser: bool = False,
        picking: bool = False,
    ) -> None:
        if visible:
            if not self.isVisible():
                self.show()
            self.raise_()
        else:
            self.hide()
            return

        self._btn_record.setEnabled(recorder_browser and not recording and not playing and not picking)
        self._btn_pause.setEnabled(recording and not playing)
        self._btn_stop.setEnabled(recording or playing or player_browser)
        self._btn_focus.setEnabled(recorder_browser or player_browser or playing)
        self._btn_picker.setEnabled(
            (recorder_browser or player_browser)
            and not recording
            and not picking
            and (not playing or player_browser)
        )

        if recording:
            color = "#cca700" if paused else COLOR_RECORDING
            self._title.setText("● Идёт запись" if not paused else "⏸ Запись на паузе")
            self._title.setStyleSheet(f"color: {color}; font-size: 8pt; font-weight: 600;")
        elif playing:
            self._title.setText("▶ Идёт тест")
            self._title.setStyleSheet(f"color: {COLOR_TEXT}; font-size: 8pt; font-weight: 600;")
        else:
            self._title.setText(f"{BRAND_NAME} — перетащите панель")
            self._title.setStyleSheet(f"color: {COLOR_MUTED}; font-size: 8pt;")

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_offset = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        if self._drag_offset is not None and event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_offset)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        self._drag_offset = None
        super().mouseReleaseEvent(event)
