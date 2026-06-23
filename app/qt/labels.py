"""Role-based QLabel helpers — prefer over inline setStyleSheet."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QWidget


def repolish(widget: QWidget) -> None:
    style = widget.style()
    style.unpolish(widget)
    style.polish(widget)
    widget.update()


def caption_label(text: str = "", *, word_wrap: bool = False, padding_top: bool = False) -> QLabel:
    label = QLabel(text)
    label.setProperty("role", "ui-caption")
    if word_wrap:
        label.setWordWrap(True)
    if padding_top:
        label.setProperty("padding", "top")
    return label


def body_label(text: str = "", *, selectable: bool = False) -> QLabel:
    label = QLabel(text)
    label.setProperty("role", "ui-body")
    if selectable:
        label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
    return label


def body_secondary_label(text: str = "") -> QLabel:
    label = QLabel(text)
    label.setProperty("role", "ui-body-secondary")
    return label


def section_label(text: str, *, compact: bool = False) -> QLabel:
    label = QLabel(text)
    label.setProperty("role", "ui-section-sm" if compact else "ui-section")
    return label


def strip_title_label(text: str) -> QLabel:
    label = QLabel(text)
    label.setProperty("role", "ui-strip-title")
    return label


def dialog_title_label(text: str, *, selectable: bool = False) -> QLabel:
    label = QLabel(text)
    label.setProperty("role", "dialog-title")
    if selectable:
        label.setWordWrap(True)
        label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
    return label


def error_label(text: str = "", *, word_wrap: bool = False) -> QLabel:
    label = QLabel(text)
    label.setProperty("role", "ui-error")
    if word_wrap:
        label.setWordWrap(True)
    return label


def code_preview_label(text: str = "") -> QLabel:
    label = QLabel(text)
    label.setProperty("role", "code-preview")
    label.setWordWrap(True)
    label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
    label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
    return label


def link_label(text: str, *, tooltip: str = "") -> QLabel:
    label = QLabel(f'<a href="#">{text}</a>')
    label.setProperty("role", "link-label")
    label.setTextFormat(Qt.TextFormat.RichText)
    label.setOpenExternalLinks(False)
    if tooltip:
        label.setToolTip(tooltip)
    return label


def welcome_title_label(text: str) -> QLabel:
    label = QLabel(text)
    label.setProperty("role", "welcome-title")
    return label


def welcome_section_label(text: str) -> QLabel:
    label = QLabel(text)
    label.setProperty("role", "welcome-section")
    return label


def welcome_heading_label(text: str) -> QLabel:
    label = QLabel(text)
    label.setProperty("role", "welcome-muted-heading")
    return label


def set_label_tone(label: QLabel, tone: str | None) -> None:
    """Set semantic color: muted, success, warning, error, active, or None."""
    label.setProperty("tone", tone or "")
    repolish(label)


def muted_label(text: str = "", *, word_wrap: bool = False) -> QLabel:
    label = QLabel(text)
    label.setProperty("muted", True)
    if word_wrap:
        label.setWordWrap(True)
    return label


def dialog_hint_label(text: str) -> QLabel:
    label = QLabel(text)
    label.setProperty("role", "dialog-hint")
    label.setWordWrap(True)
    return label
