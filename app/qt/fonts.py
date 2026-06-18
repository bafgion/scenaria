"""Monospace fonts for code editors and log panels."""

from __future__ import annotations

from PySide6.QtGui import QFont, QFontDatabase

EDITOR_FONT_CANDIDATES: tuple[str, ...] = (
    "Cascadia Code",
    "Cascadia Mono",
    "JetBrains Mono",
    "Fira Code",
    "Source Code Pro",
    "IBM Plex Mono",
    "Consolas",
    "Courier New",
)

EDITOR_FONT_SIZE_PT = 10

_resolved_family: str | None = None


def editor_font_family() -> str:
    global _resolved_family
    if _resolved_family is not None:
        return _resolved_family

    available = {name.lower(): name for name in QFontDatabase.families()}
    for candidate in EDITOR_FONT_CANDIDATES:
        match = available.get(candidate.lower())
        if match is not None:
            _resolved_family = match
            return match

    _resolved_family = "monospace"
    return _resolved_family


def editor_font(*, size_pt: int | None = None) -> QFont:
    font = QFont(editor_font_family())
    font.setPointSize(size_pt if size_pt is not None else EDITOR_FONT_SIZE_PT)
    font.setStyleHint(QFont.StyleHint.Monospace)
    font.setFixedPitch(True)
    return font


def editor_font_css(*, size_pt: int | None = None) -> str:
    size = size_pt if size_pt is not None else EDITOR_FONT_SIZE_PT
    return f"{editor_font_family_css()}; font-size: {size}pt"


def editor_font_family_css() -> str:
    family = editor_font_family()
    return f'"{family}", "Cascadia Code", Consolas, monospace'
