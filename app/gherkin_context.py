"""Gherkin ``Контекст`` block and ``TestClient`` connection steps."""

from __future__ import annotations

import re

from app.gherkin_ru import (
    GHERKIN_KEYWORDS,
    GherkinParseError,
    STEP_INDENT,
    _KEYWORD_RE,
    _quote,
    _unquote,
    is_gherkin_step_line,
    parse_feature_structure,
)

_CONTEXT_HEADER_RE = re.compile(r"^контекст\s*:\s*$", re.IGNORECASE)
_CONNECT_BODY_RE = re.compile(
    r'^я\s+подключаю\s+TestClient\s+"((?:\\.|[^"])*)"\s*$',
    re.IGNORECASE,
)


def is_context_header_line(line: str) -> bool:
    return bool(_CONTEXT_HEADER_RE.match(line.strip()))


def parse_connect_test_client_body(body: str) -> str | None:
    match = _CONNECT_BODY_RE.match(body.strip())
    if not match:
        return None
    return _unquote(match.group(1))


def parse_test_client_from_context_lines(
    context_lines: list[str],
    *,
    line_offset: int = 1,
) -> str:
    names: list[str] = []
    for index, raw in enumerate(context_lines, start=line_offset):
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if not is_gherkin_step_line(raw):
            raise GherkinParseError(
                index,
                raw,
                "В блоке «Контекст» ожидается шаг: Дано я подключаю TestClient \"…\"",
            )
        keyword_match = _KEYWORD_RE.match(stripped)
        body = keyword_match.group(1).strip() if keyword_match else stripped
        name = parse_connect_test_client_body(body)
        if name is None:
            raise GherkinParseError(
                index,
                raw,
                "Неизвестный шаг контекста — поддерживается: Дано я подключаю TestClient \"…\"",
            )
        names.append(name)
    if not names:
        raise GherkinParseError(
            line_offset,
            "Контекст:",
            "В блоке «Контекст» укажите: Дано я подключаю TestClient \"…\"",
        )
    if len(names) > 1:
        raise GherkinParseError(
            line_offset,
            "Контекст:",
            "В контексте допускается только один TestClient",
        )
    return names[0]


def parse_feature_test_client(text: str) -> str | None:
    """Return TestClient name from feature text, or ``None`` if no context block."""
    structure = parse_feature_structure(text)
    if not structure.has_context_block:
        return None
    return parse_test_client_from_context_lines(structure.context_lines)


def format_context_lines(client_name: str) -> list[str]:
    safe = _quote(client_name)
    return [
        "Контекст:",
        format_step_line(f'я подключаю TestClient "{safe}"'),
    ]


def format_step_line(body: str) -> str:
    return f"{STEP_INDENT}Дано {body}"


def gherkin_keywords_with_dano() -> tuple[str, ...]:
    return GHERKIN_KEYWORDS + ("Дано",)
