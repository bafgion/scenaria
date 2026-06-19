"""Post-recording action banner."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QWidget

from app.qt.theme import COLOR_MUTED, COLOR_WARNING


class PostRecordBanner(QWidget):
    apply_and_test_clicked = Signal()
    save_clicked = Signal()
    fix_hover_clicked = Signal()
    dismiss_clicked = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setProperty("role", "post-record-banner")
        self.hide()

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(8)

        self._summary = QLabel("")
        layout.addWidget(self._summary, stretch=1)

        self._hover_hint = QLabel("")
        self._hover_hint.setStyleSheet(f"color: {COLOR_WARNING}; font-size: 8pt;")
        self._hover_hint.hide()
        layout.addWidget(self._hover_hint)

        self._fix_btn = QPushButton("Добавить наведение")
        self._fix_btn.hide()
        self._fix_btn.clicked.connect(self.fix_hover_clicked.emit)
        layout.addWidget(self._fix_btn)

        test_btn = QPushButton("Проверить")
        test_btn.setProperty("primary", True)
        test_btn.clicked.connect(self.apply_and_test_clicked.emit)
        layout.addWidget(test_btn)

        save_btn = QPushButton("Сохранить")
        save_btn.clicked.connect(self.save_clicked.emit)
        layout.addWidget(save_btn)

        close_btn = QPushButton("Закрыть")
        close_btn.setStyleSheet(f"color: {COLOR_MUTED};")
        close_btn.clicked.connect(self.dismiss_clicked.emit)
        layout.addWidget(close_btn)

    def show_recording(self, step_count: int, *, suspicious_clicks: int = 0) -> None:
        self._summary.setText(f"Записано шагов: {step_count}")
        if suspicious_clicks:
            self._hover_hint.setText(
                f"Похоже на hover-меню: {suspicious_clicks} клик(ов) без «навожу»"
            )
            self._hover_hint.show()
            self._fix_btn.show()
        else:
            self._hover_hint.hide()
            self._fix_btn.hide()
        self.show()

    def hide_banner(self) -> None:
        self.hide()
