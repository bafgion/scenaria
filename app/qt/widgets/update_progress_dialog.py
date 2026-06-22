"""Modal progress dialog for portable application updates."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QLabel, QProgressBar, QVBoxLayout

from app.update.progress import (
    PHASE_LABELS_RU,
    UpdatePhase,
    format_bytes,
    weighted_percent,
)


class UpdateProgressDialog(QDialog):
    def __init__(
        self,
        parent,
        *,
        from_version: str,
        to_version: str,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Загрузка обновления")
        self.setMinimumWidth(420)
        self.setModal(True)
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 18, 20, 18)
        root.setSpacing(10)

        self._phase = QLabel(PHASE_LABELS_RU[UpdatePhase.DOWNLOAD])
        self._phase.setStyleSheet("font-size: 14px; font-weight: 600;")
        root.addWidget(self._phase)

        self._detail = QLabel(f"{from_version} → {to_version}")
        self._detail.setWordWrap(True)
        self._detail.setStyleSheet("color: #858585;")
        root.addWidget(self._detail)

        self._bar = QProgressBar()
        self._bar.setRange(0, 100)
        self._bar.setValue(0)
        self._bar.setTextVisible(True)
        self._bar.setFixedHeight(22)
        root.addWidget(self._bar)

        self._version_line = f"{from_version} → {to_version}"

    def set_phase(self, phase_name: str, current: int, total: int, detail: str = "") -> None:
        phase = UpdatePhase(phase_name)
        self._phase.setText(PHASE_LABELS_RU[phase])
        percent = weighted_percent(phase, current, total)
        self._bar.setValue(percent)
        self._bar.setFormat(f"{percent} %")
        self._detail.setText(self._detail_text(phase, current, total, detail))

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
