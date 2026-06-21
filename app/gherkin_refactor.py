"""Quick Gherkin refactorings (A2-3)."""

from __future__ import annotations

import re

from app.gherkin_ru import STEP_INDENT, _KEYWORD_RE, is_gherkin_step_line, leading_indent

_GOTO_BODY_RE = re.compile(r'^открыт[а]?\s+"((?:\\.|[^"])*)"$', re.IGNORECASE)
_HEADER_RE = re.compile(r"^(?:функционал|сценарий|структура\s+сценария)\s*:", re.IGNORECASE)
_TAG_RE = re.compile(r"^@\S+$")
_EXAMPLES_RE = re.compile(r"^примеры\s*:", re.IGNORECASE)


def _is_step_block_line(stripped: str, raw: str) -> bool:
    if not stripped or stripped.startswith("#"):
        return False
    if _HEADER_RE.match(stripped) or _TAG_RE.match(stripped) or _EXAMPLES_RE.match(stripped):
        return False
    if stripped.startswith("|"):
        return False
    return is_gherkin_step_line(raw) or bool(_KEYWORD_RE.match(stripped))


def update_start_urls(text: str, new_url: str) -> tuple[str, int]:
    """Replace URL in every ``открыт`` / goto step. Returns (text, count)."""
    url = new_url.strip()
    if not url:
        return text, 0
    changed = 0
    lines: list[str] = []
    for raw in text.replace("\r\n", "\n").splitlines():
        stripped = raw.strip()
        if not _is_step_block_line(stripped, raw):
            lines.append(raw)
            continue
        match = _KEYWORD_RE.match(stripped)
        if not match:
            lines.append(raw)
            continue
        body = match.group(1).strip()
        goto = _GOTO_BODY_RE.fullmatch(body)
        if goto is None:
            lines.append(raw)
            continue
        keyword = stripped[: len(stripped) - len(body)].strip()
        prefix = f"{keyword} " if keyword else ""
        indent = leading_indent(raw)
        lines.append(f'{indent}{prefix}открыт "{url}"')
        changed += 1
    suffix = "\n" if text.endswith("\n") else ""
    payload = "\n".join(lines)
    if suffix and payload:
        payload += "\n"
    return payload, changed


def normalize_step_indents(text: str) -> str:
    """Convert step lines to a single tab indent."""
    lines: list[str] = []
    for raw in text.replace("\r\n", "\n").splitlines():
        stripped = raw.strip()
        if not _is_step_block_line(stripped, raw):
            lines.append(raw)
            continue
        lines.append(f"{STEP_INDENT}{stripped}")
    suffix = "\n" if text.endswith("\n") else ""
    payload = "\n".join(lines)
    if suffix and payload:
        payload += "\n"
    return payload


def collapse_blank_lines_between_steps(text: str) -> str:
    """Remove empty lines that sit between consecutive step lines."""
    lines = text.replace("\r\n", "\n").splitlines()
    if not lines:
        return text
    result: list[str] = []
    index = 0
    while index < len(lines):
        raw = lines[index]
        stripped = raw.strip()
        result.append(raw)
        if not _is_step_block_line(stripped, raw):
            index += 1
            continue
        next_index = index + 1
        while next_index < len(lines):
            peek = lines[next_index]
            if peek.strip():
                break
            next_index += 1
        if next_index < len(lines) and _is_step_block_line(lines[next_index].strip(), lines[next_index]):
            index = next_index
            continue
        index += 1
    suffix = "\n" if text.endswith("\n") else ""
    payload = "\n".join(result)
    if suffix and payload:
        payload += "\n"
    return payload
