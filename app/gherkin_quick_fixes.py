"""Quick fixes for the Gherkin editor (E2-1)."""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass

from app.gherkin_ru import (
    STEP_INDENT,
    GherkinParseError,
    coalesce_mixed_step_indents_in_text,
    gherkin_to_steps,
    is_step_indented,
    leading_indent,
)

_KEYWORD_FIXES: dict[str, str] = {
    "дапустим": "Допустим",
    "допустим": "Допустим",
    "когда": "Когда",
    "тогда": "Тогда",
    "но": "Но",
}

_GHERKIN_PREFIX_RE = re.compile(r"^(Допустим|Когда|Тогда|И|Но)(\s+)", re.IGNORECASE)
_ANY_PREFIX_RE = re.compile(r"^(\S+)(\s+)")


@dataclass(frozen=True)
class QuickFix:
    label: str
    description: str


@dataclass(frozen=True)
class QuickFixAction:
    fix: QuickFix
    apply: Callable[[], None]


def _line_at(text: str, line_no: int) -> tuple[str, int, int]:
    start = 0
    for index, line in enumerate(text.splitlines(keepends=True), start=1):
        end = start + len(line)
        if index == line_no:
            return line, start, end
        start = end
    return "", len(text), len(text)


def _replace_line(text: str, line_no: int, new_line: str) -> str:
    line, start, end = _line_at(text, line_no)
    ending = ""
    if line.endswith("\r\n"):
        ending = "\r\n"
    elif line.endswith("\n"):
        ending = "\n"
    body = line[: len(line) - len(ending)] if ending else line
    indent = leading_indent(body)
    stripped = body.strip()
    if stripped and not stripped.startswith("#"):
        if not new_line.startswith(indent) and not new_line.startswith("\t"):
            new_line = indent + new_line.lstrip()
    return text[:start] + new_line + ending + text[end:]


def suggest_quick_fixes(text: str, line_no: int) -> list[tuple[QuickFix, str]]:
    """Return (fix, new_text) pairs for the given line."""
    lines = text.splitlines()
    if line_no < 1 or line_no > len(lines):
        return []

    raw = lines[line_no - 1]
    stripped = raw.strip()
    if not stripped or stripped.startswith("#"):
        return []

    fixes: list[tuple[QuickFix, str]] = []

    match = _GHERKIN_PREFIX_RE.match(stripped) or _ANY_PREFIX_RE.match(stripped)
    if match:
        keyword = match.group(1)
        lowered = keyword.lower()
        replacement = _KEYWORD_FIXES.get(lowered)
        if replacement and replacement != keyword:
            new_stripped = replacement + stripped[len(keyword) :]
            new_line = leading_indent(raw) + new_stripped
            fixes.append(
                (
                    QuickFix(f"Заменить «{keyword}» → «{replacement}»", "Исправить опечатку в ключевом слове"),
                    _replace_line(text, line_no, new_line),
                )
            )

    if stripped.count('"') % 2 == 1 and not stripped.endswith('"'):
        fixes.append(
            (
                QuickFix('Добавить закрывающую «"»', "Закрыть незавершённую строку"),
                _replace_line(text, line_no, raw + '"'),
            )
        )

    if is_step_indented(raw) and not raw.startswith("\t"):
        normalized = STEP_INDENT + stripped
        fixes.append(
            (
                QuickFix("Заменить пробелы на таб", "Нормализовать отступ шага"),
                _replace_line(text, line_no, normalized),
            )
        )

    try:
        gherkin_to_steps(text)
    except GherkinParseError as exc:
        if exc.line_no == line_no:
            fixes.append(
                (
                    QuickFix("Открыть палитру шагов (Ctrl+Shift+Space)", "Вставить шаблон похожего шага"),
                    text,
                )
            )

    return fixes


def suggest_quick_fixes_for_error(text: str, line_no: int) -> list[tuple[QuickFix, str]]:
    """Line fixes plus whole-file indent repair when applicable."""
    fixes = list(suggest_quick_fixes(text, line_no))
    coalesced = coalesce_mixed_step_indents_in_text(text)
    if coalesced != text and not any(item[0].label == "Исправить отступы во всём файле" for item in fixes):
        fixes.insert(
            0,
            (
                QuickFix(
                    "Исправить отступы во всём файле",
                    "Заменить пробельные отступы шагов на табы",
                ),
                coalesced,
            ),
        )
    return fixes
