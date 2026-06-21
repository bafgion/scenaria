"""Indented Gherkin blocks: ``Если`` / ``Повторяю``."""

from __future__ import annotations

import re
from typing import Any

from app.gherkin_ru import GherkinParseError, leading_indent

_IF_HEADER_RE = re.compile(r"^если\s+(.+)$", re.IGNORECASE)
_REPEAT_HEADER_RE = re.compile(r"^повторяю\s+(\d+)\s+раз(?:а)?$", re.IGNORECASE)
_WHILE_HEADER_RE = re.compile(r"^пока\s+(.+)$", re.IGNORECASE)
_FOR_EACH_HEADER_RE = re.compile(
    r'^для\s+каждого\s+"((?:\\.|[^"])*)"\s+как\s+"((?:\\.|[^"])*)"$',
    re.IGNORECASE,
)
_QSTR = r'"((?:\\.|[^"])*)"'


def line_indent_level(raw: str) -> int:
    """Return indent depth for a step line (-1 for blank/comment)."""
    stripped = raw.strip()
    if not stripped or stripped.startswith("#"):
        return -1
    indent = leading_indent(raw)
    if "\t" in indent:
        return indent.count("\t")
    spaces = len(indent)
    return max(1, spaces // 2) if spaces >= 2 else (1 if spaces > 0 else 0)


def parse_if_condition(expr: str, *, line_no: int, line_text: str) -> dict[str, Any]:
    """Parse ``вижу`` / ``не вижу`` / ``url содержит`` / ``текст на странице``."""
    from app.gherkin_ru import _unquote

    visible = re.fullmatch(rf"вижу\s+{_QSTR}", expr, flags=re.IGNORECASE)
    if visible:
        return {"type": "visible", "selector": _unquote(visible.group(1))}

    hidden = re.fullmatch(rf"не\s+вижу\s+{_QSTR}", expr, flags=re.IGNORECASE)
    if hidden:
        return {"type": "hidden", "selector": _unquote(hidden.group(1))}

    url_contains = re.fullmatch(rf"url\s+содержит\s+{_QSTR}", expr, flags=re.IGNORECASE)
    if url_contains:
        return {"type": "url_contains", "value": _unquote(url_contains.group(1))}

    page_text = re.fullmatch(rf"текст\s+на\s+странице\s+{_QSTR}", expr, flags=re.IGNORECASE)
    if page_text:
        return {"type": "page_text", "value": _unquote(page_text.group(1))}

    raise GherkinParseError(
        line_no,
        line_text,
        "Неизвестное условие — поддерживаются: вижу, не вижу, url содержит, текст на странице",
    )


def parse_while_header(body: str, *, line_no: int, line_text: str) -> dict[str, Any] | None:
    match = _WHILE_HEADER_RE.match(body.strip())
    if not match:
        return None
    return parse_if_condition(match.group(1).strip(), line_no=line_no, line_text=line_text)


def parse_for_each_header(body: str) -> dict[str, str] | None:
    from app.gherkin_ru import _unquote

    match = _FOR_EACH_HEADER_RE.match(body.strip())
    if not match:
        return None
    return {
        "selector": _unquote(match.group(1)),
        "variable": _unquote(match.group(2)),
    }


def parse_if_header(body: str, *, line_no: int, line_text: str) -> dict[str, Any] | None:
    match = _IF_HEADER_RE.match(body.strip())
    if not match:
        return None
    return parse_if_condition(match.group(1).strip(), line_no=line_no, line_text=line_text)


def parse_repeat_header(body: str) -> int | None:
    match = _REPEAT_HEADER_RE.match(body.strip())
    if not match:
        return None
    return max(1, int(match.group(1)))


def condition_to_gherkin(condition: dict[str, Any]) -> str:
    from app.gherkin_ru import _quote

    kind = str(condition.get("type", "") or "")
    if kind == "visible":
        return f'вижу "{_quote(condition.get("selector", ""))}"'
    if kind == "hidden":
        return f'не вижу "{_quote(condition.get("selector", ""))}"'
    if kind == "url_contains":
        return f'url содержит "{_quote(condition.get("value", ""))}"'
    if kind == "page_text":
        return f'текст на странице "{_quote(condition.get("value", ""))}"'
    return str(condition.get("type", "условие"))
