"""Scenario Outline / Examples parsing and expansion."""

from __future__ import annotations

import copy
import re
from dataclasses import dataclass
from typing import Any

from app.gherkin_ru import gherkin_to_steps

_OUTLINE_HEADER_RE = re.compile(r"^структура\s+сценария\s*:\s*(.*)$", re.IGNORECASE)
_EXAMPLES_HEADER_RE = re.compile(r"^примеры\s*:\s*$", re.IGNORECASE)
_PLACEHOLDER_RE = re.compile(r"<([^>]+)>")


@dataclass(frozen=True)
class OutlineScenario:
    scenario_name: str
    template_steps: list[dict[str, Any]]
    headers: tuple[str, ...]
    rows: tuple[dict[str, str], ...]


def _parse_pipe_table(lines: list[str], start: int) -> tuple[list[str], list[list[str]]]:
    headers: list[str] = []
    rows: list[list[str]] = []
    index = start
    while index < len(lines):
        stripped = lines[index].strip()
        if not stripped:
            if headers:
                break
            index += 1
            continue
        if not stripped.startswith("|"):
            if headers:
                break
            index += 1
            continue
        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        if not headers:
            headers = cells
        else:
            rows.append(cells)
        index += 1
    return headers, rows


def parse_outline(text: str) -> OutlineScenario | None:
    """Return outline metadata when the feature uses ``Структура сценария`` + ``Примеры``."""
    lines = text.replace("\r\n", "\n").splitlines()
    scenario_name = ""
    outline_index: int | None = None
    examples_index: int | None = None

    for index, raw in enumerate(lines):
        stripped = raw.strip()
        match = _OUTLINE_HEADER_RE.match(stripped)
        if match:
            scenario_name = match.group(1).strip() or "Сценарий"
            outline_index = index
            continue
        if outline_index is not None and examples_index is None and _EXAMPLES_HEADER_RE.match(stripped):
            examples_index = index
            break

    if outline_index is None or examples_index is None:
        return None

    body_lines = lines[:examples_index]
    body_text = "\n".join(body_lines)
    template_steps = gherkin_to_steps(body_text)

    headers, raw_rows = _parse_pipe_table(lines, examples_index + 1)
    if not headers or not raw_rows:
        return None

    rows: list[dict[str, str]] = []
    for raw_row in raw_rows:
        row: dict[str, str] = {}
        for header_index, header in enumerate(headers):
            key = header.strip()
            if not key:
                continue
            value = raw_row[header_index] if header_index < len(raw_row) else ""
            row[key] = value.strip()
        if row:
            rows.append(row)

    if not rows:
        return None

    return OutlineScenario(
        scenario_name=scenario_name,
        template_steps=template_steps,
        headers=tuple(headers),
        rows=tuple(rows),
    )


def substitute_outline_value(text: str, row: dict[str, str]) -> str:
    def repl(match: re.Match[str]) -> str:
        key = match.group(1).strip()
        return row.get(key, match.group(0))

    return _PLACEHOLDER_RE.sub(repl, text)


def substitute_outline_step(step: dict[str, Any], row: dict[str, str]) -> dict[str, Any]:
    result = copy.deepcopy(step)
    action = result.get("action")
    if action == "if":
        condition = dict(result.get("condition") or {})
        for key, value in list(condition.items()):
            if isinstance(value, str):
                condition[key] = substitute_outline_value(value, row)
        result["condition"] = condition
        result["steps"] = [substitute_outline_step(item, row) for item in result.get("steps") or []]
        return result
    if action == "repeat":
        result["steps"] = [substitute_outline_step(item, row) for item in result.get("steps") or []]
        return result
    for key, value in list(result.items()):
        if isinstance(value, str):
            result[key] = substitute_outline_value(value, row)
    return result


def expand_outline_steps(template_steps: list[dict[str, Any]], row: dict[str, str]) -> list[dict[str, Any]]:
    return [substitute_outline_step(step, row) for step in template_steps]


def outline_example_count(text: str) -> int:
    outline = parse_outline(text)
    return len(outline.rows) if outline else 0
