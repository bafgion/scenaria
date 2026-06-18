"""Visible 1px separators between IDE zones."""

from __future__ import annotations

from PySide6.QtWidgets import QFrame, QSizePolicy, QWidget


def zone_divider(parent: QWidget | None = None, *, vertical: bool = True) -> QFrame:
    line = QFrame(parent)
    line.setProperty("role", "zone-divider")
    line.setFrameShape(QFrame.Shape.NoFrame)
    if vertical:
        line.setFixedWidth(1)
        line.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)
    else:
        line.setFixedHeight(1)
        line.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
    return line
