"""Syntax highlighting for Russian Gherkin in the code editor."""

from __future__ import annotations

import re

from PySide6.QtGui import QColor, QFont, QSyntaxHighlighter, QTextCharFormat

from app.gherkin_ru import GHERKIN_KEYWORDS
from app.qt.theme import COLOR_ERROR, COLOR_MUTED, COLOR_TEXT

# VS Code–like token colors on dark background
_COLOR_KEYWORD = "#569cd6"
_COLOR_STRING = "#ce9178"
_COLOR_COMMENT = "#6a9955"
_COLOR_TAG = "#c586c0"
_COLOR_HEADER = "#4ec9b0"


class GherkinHighlighter(QSyntaxHighlighter):
    def __init__(self, document) -> None:
        super().__init__(document)
        self._error_line: int | None = None

        self._default = QTextCharFormat()
        self._default.setForeground(QColor(COLOR_TEXT))

        self._keyword = QTextCharFormat()
        self._keyword.setForeground(QColor(_COLOR_KEYWORD))
        self._keyword.setFontWeight(QFont.Weight.Bold)

        self._string = QTextCharFormat()
        self._string.setForeground(QColor(_COLOR_STRING))

        self._comment = QTextCharFormat()
        self._comment.setForeground(QColor(_COLOR_COMMENT))
        self._comment.setFontItalic(True)

        self._tag = QTextCharFormat()
        self._tag.setForeground(QColor(_COLOR_TAG))

        self._header = QTextCharFormat()
        self._header.setForeground(QColor(_COLOR_HEADER))
        self._header.setFontWeight(QFont.Weight.Bold)

        self._error = QTextCharFormat()
        self._error.setUnderlineColor(QColor(COLOR_ERROR))
        self._error.setUnderlineStyle(QTextCharFormat.UnderlineStyle.WaveUnderline)
        self._error.setForeground(QColor(COLOR_ERROR))

        kw_pattern = "|".join(re.escape(word) for word in GHERKIN_KEYWORDS)
        self._header_re = re.compile(r"^(Функционал|Сценарий|Функция)\s*:", re.IGNORECASE)
        self._tag_re = re.compile(r"^@[\w-]+")
        self._keyword_re = re.compile(rf"^(\t*)({kw_pattern})(\s+)", re.IGNORECASE)
        self._string_re = re.compile(r'"([^"\\]|\\.)*"')
        self._comment_re = re.compile(r"#.*$")

    def set_error_line(self, line_no: int | None) -> None:
        """1-based line number with parse error, or None to clear."""
        if line_no is not None and line_no < 1:
            line_no = None
        if self._error_line == line_no:
            return
        self._error_line = line_no
        self.rehighlight()

    def highlightBlock(self, text: str) -> None:  # noqa: N802
        if not text:
            self.setFormat(0, 0, self._default)
            return

        line_no = self.currentBlock().blockNumber() + 1
        if self._error_line == line_no:
            self.setFormat(0, len(text), self._error)

        stripped = text.lstrip()
        if not stripped:
            return

        offset = len(text) - len(stripped)

        if stripped.startswith("#"):
            self.setFormat(offset, len(text) - offset, self._comment)
            return

        header = self._header_re.match(stripped)
        if header:
            self.setFormat(offset, header.end(), self._header)
            rest = stripped[header.end() :]
            self._highlight_strings(offset + header.end(), rest)
            return

        tag = self._tag_re.match(stripped)
        if tag:
            self.setFormat(offset, tag.end(), self._tag)
            return

        keyword = self._keyword_re.match(text)
        if keyword:
            kw_start = keyword.start(2)
            kw_len = keyword.end(2) - kw_start
            self.setFormat(kw_start, kw_len, self._keyword)
            self._highlight_strings(0, text)
            self._highlight_comment(text)
            return

        self._highlight_strings(0, text)
        self._highlight_comment(text)

    def _highlight_strings(self, base_offset: int, text: str) -> None:
        for match in self._string_re.finditer(text):
            start = base_offset + match.start()
            self.setFormat(start, match.end() - match.start(), self._string)

    def _highlight_comment(self, text: str) -> None:
        match = self._comment_re.search(text)
        if match:
            self.setFormat(match.start(), match.end() - match.start(), self._comment)
