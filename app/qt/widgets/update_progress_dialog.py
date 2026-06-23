"""Modal progress dialog for portable application updates."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QLabel, QProgressBar

from app.qt.labels import muted_label
from app.qt.widgets.base_dialog import BaseAppDialog, dialog_action_button
from app.update.progress import (
    PHASE_LABELS_RU,
    UpdatePhase,
    format_bytes,
    weighted_percent,
)


class UpdateProgressDialog(BaseAppDialog):
    cancel_requested = Signal()

    def __init__(
        self,
        parent,
        *,
        from_version: str,
        to_version: str,
    ) -> None:
        super().__init__(parent, title="Загрузка обновления", min_width=420)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self._indeterminate = False

        self._phase = QLabel(PHASE_LABELS_RU[UpdatePhase.DOWNLOAD])
        self._phase.setProperty("role", "dialog-phase")
        self.content_layout.addWidget(self._phase)

        self._version_line = f"{from_version} → {to_version}"
        self._detail = muted_label(self._version_line, word_wrap=True)
        self.content_layout.addWidget(self._detail)

        self._slow_hint = muted_label("", word_wrap=True)
        self._slow_hint.hide()
        self.content_layout.addWidget(self._slow_hint)

        self._bar = QProgressBar()
        self._bar.setRange(0, 100)
        self._bar.setValue(0)
        self._bar.setTextVisible(True)
        self._bar.setFixedHeight(22)
        self.content_layout.addWidget(self._bar)

        self._cancel_btn = dialog_action_button("Отмена")
        self._cancel_btn.clicked.connect(self.cancel_requested.emit)
        self.add_button_row(self._cancel_btn)

    def set_cancel_enabled(self, enabled: bool) -> None:
        self._cancel_btn.setEnabled(enabled)
        self._cancel_btn.setVisible(enabled)

    def set_slow_hint(self, visible: bool) -> None:
        if visible:
            self._slow_hint.setText("Это может занять несколько минут…")
            self._slow_hint.show()
        else:
            self._slow_hint.hide()

    def set_phase(self, phase_name: str, current: int, total: int, detail: str = "") -> None:
        phase = UpdatePhase(phase_name)
        self._phase.setText(PHASE_LABELS_RU[phase])
        self.set_cancel_enabled(phase == UpdatePhase.DOWNLOAD)
        self.set_slow_hint(False)

        if phase == UpdatePhase.DOWNLOAD and total <= 0:
            self._set_indeterminate(True)
            if current > 0:
                self._bar.setFormat(f"Скачано {format_bytes(current)}")
            else:
                self._bar.setFormat("Скачивание…")
        else:
            self._set_indeterminate(False)
            percent = weighted_percent(phase, current, total)
            self._bar.setValue(percent)
            self._bar.setFormat(f"{percent} %")

        self._detail.setText(self._detail_text(phase, current, total, detail))

    def _set_indeterminate(self, enabled: bool) -> None:
        if enabled == self._indeterminate:
            return
        self._indeterminate = enabled
        if enabled:
            self._bar.setRange(0, 0)
        else:
            self._bar.setRange(0, 100)

    def _detail_text(self, phase: UpdatePhase, current: int, total: int, detail: str) -> str:
        if phase == UpdatePhase.DOWNLOAD:
            if total > 0:
                return f"{self._version_line} · {format_bytes(current)} / {format_bytes(total)}"
            if current > 0:
                return f"{self._version_line} · скачано {format_bytes(current)}"
            if detail:
                return f"{self._version_line} · {detail}"
            return self._version_line
        if detail:
            return f"{self._version_line} · {detail}"
        return self._version_line
