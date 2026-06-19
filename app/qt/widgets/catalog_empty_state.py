"""Centered empty-state card for the features catalog."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QSizePolicy, QVBoxLayout, QWidget

from app.mvc.models.catalog_model import EmptyKind
from app.qt import icons


class CatalogEmptyState(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setProperty("role", "catalog-empty")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._full_title = ""
        self._full_hint = ""

        outer = QVBoxLayout(self)
        outer.setContentsMargins(8, 12, 8, 12)
        outer.addStretch(1)
        self._outer_layout = outer

        card = QWidget(self)
        card.setProperty("role", "catalog-empty-card")
        card.setMinimumWidth(0)
        card.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Maximum)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(14, 16, 14, 16)
        card_layout.setSpacing(8)
        self._card_layout = card_layout

        self._icon = QLabel(card)
        self._icon.setProperty("role", "catalog-empty-icon")
        self._icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._icon.setFixedSize(52, 52)
        card_layout.addWidget(self._icon, alignment=Qt.AlignmentFlag.AlignHCenter)

        self._title = QLabel(card)
        self._title.setWordWrap(True)
        self._title.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        self._title.setProperty("role", "catalog-empty-title")
        self._title.setMinimumWidth(0)
        self._title.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        card_layout.addWidget(self._title)

        self._hint = QLabel(card)
        self._hint.setWordWrap(True)
        self._hint.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        self._hint.setProperty("role", "catalog-empty-hint")
        self._hint.setMinimumWidth(0)
        self._hint.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        card_layout.addWidget(self._hint)

        outer.addWidget(card)
        outer.addStretch(2)

    def set_state(self, title: str, hint: str, kind: EmptyKind | None) -> None:
        self._full_title = title
        self._full_hint = hint
        icon_kind = kind or "no_project"
        pixmap = icons.catalog_empty_icon(icon_kind, size=28).pixmap(icons.icon_size(28))
        self._icon.setPixmap(pixmap)
        self._apply_responsive_layout()

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        self._apply_responsive_layout()

    def _apply_responsive_layout(self) -> None:
        compact = self.width() < 210
        if compact:
            self._outer_layout.setContentsMargins(4, 8, 4, 8)
            self._card_layout.setContentsMargins(10, 12, 10, 12)
            self._card_layout.setSpacing(6)
            self._icon.setFixedSize(44, 44)
            self._title.setText(self._full_title)
            # Keep hint short on very narrow sidebars to avoid visual breakage.
            self._hint.setText(self._full_hint.splitlines()[0] if self._full_hint else "")
        else:
            self._outer_layout.setContentsMargins(8, 12, 8, 12)
            self._card_layout.setContentsMargins(14, 16, 14, 16)
            self._card_layout.setSpacing(8)
            self._icon.setFixedSize(52, 52)
            self._title.setText(self._full_title)
            self._hint.setText(self._full_hint)
