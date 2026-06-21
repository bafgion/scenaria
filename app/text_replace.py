"""Text find/replace helpers for Gherkin editors and project refactor."""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.gherkin_ru import _STEP_HEADER_RE, _TAG_LINE_RE


@dataclass(frozen=True)
class ReplaceMatch:
    start: int
    end: int
    line_index: int  # 0-based


def line_is_replaceable(line: str, *, steps_only: bool) -> bool:
    if not steps_only:
        return True
    stripped = line.strip()
    if not stripped or stripped.startswith("#"):
        return False
    if _STEP_HEADER_RE.match(stripped):
        return False
    if _TAG_LINE_RE.match(stripped):
        return False
    return True


def find_matches(
    text: str,
    needle: str,
    *,
    case_sensitive: bool = False,
    steps_only: bool = False,
) -> list[ReplaceMatch]:
    if not needle:
        return []
    flags = 0 if case_sensitive else re.IGNORECASE
    pattern = re.compile(re.escape(needle), flags)
    matches: list[ReplaceMatch] = []
    line_start = 0
    for line_index, line in enumerate(text.splitlines(keepends=True)):
        if line_is_replaceable(line.rstrip("\r\n"), steps_only=steps_only):
            for match in pattern.finditer(line):
                matches.append(
                    ReplaceMatch(
                        start=line_start + match.start(),
                        end=line_start + match.end(),
                        line_index=line_index,
                    )
                )
        line_start += len(line)
    return matches


def replace_all(
    text: str,
    needle: str,
    replacement: str,
    *,
    case_sensitive: bool = False,
    steps_only: bool = False,
) -> tuple[str, int]:
    if not needle:
        return text, 0
    flags = 0 if case_sensitive else re.IGNORECASE
    pattern = re.compile(re.escape(needle), flags)
    count = 0
    parts: list[str] = []
    for line in text.splitlines(keepends=True):
        body = line.rstrip("\r\n")
        ending = line[len(body) :]
        if line_is_replaceable(body, steps_only=steps_only):
            new_line, n = pattern.subn(replacement, body)
            count += n
            parts.append(new_line + ending)
        else:
            parts.append(line)
    return "".join(parts), count
