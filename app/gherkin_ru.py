"""Russian Gherkin-like parser/serializer for recorder steps."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Literal

_KEYWORD_RE = re.compile(r"^(?:(?:Допустим|Дано|Когда|Тогда|И|Но)\s+)?(.+)$", re.IGNORECASE)
_STEP_HEADER_RE = re.compile(r"^(?:функционал|сценарий|функция|контекст)\s*:", re.IGNORECASE)
_SCENARIO_LINE_RE = re.compile(r"^сценарий\s*:\s*(.*)$", re.IGNORECASE)
_FEATURE_LINE_RE = re.compile(r"^функционал\s*:\s*(.*)$", re.IGNORECASE)
_CONTEXT_LINE_RE = re.compile(r"^контекст\s*:\s*$", re.IGNORECASE)
_TAG_LINE_RE = re.compile(r"^@(\S+)$")
_LEGACY_HAS_TEXT_UNESCAPED = re.compile(r':has-text\("([^"\\]+)"\)')
_OUTLINE_HEADER_RE = re.compile(r"^структура\s+сценария\s*:", re.IGNORECASE)
_EXAMPLES_HEADER_RE = re.compile(r"^примеры\s*:", re.IGNORECASE)
_GHERKIN_KW_PREFIX_RE = re.compile(r"^(?:Допустим|Дано|Когда|Тогда|И|Но)\s+", re.IGNORECASE)

GHERKIN_KEYWORDS: tuple[str, ...] = ("Допустим", "Дано", "Когда", "Тогда", "И", "Но")

# One tab per step line (Gherkin body indent).
STEP_INDENT = "\t"


def leading_indent(line: str) -> str:
    return line[: len(line) - len(line.lstrip())]


def is_step_indented(line: str) -> bool:
    """True if the line uses tab or legacy two-space step indent."""
    indent = leading_indent(line)
    if indent.startswith("\t"):
        return True
    return len(indent) >= 2 and indent.strip() == ""


def format_step_line(keyword: str, body: str, *, indent: str = STEP_INDENT) -> str:
    return f"{indent}{keyword} {body}"


def line_has_step_keyword(line: str) -> bool:
    return bool(_GHERKIN_KW_PREFIX_RE.match(line.strip()))


def block_text_has_step_content(text: str) -> bool:
    stripped = text.strip()
    if not stripped or stripped.startswith("#"):
        return False
    return not bool(_STEP_HEADER_RE.match(stripped))


def suggest_step_keyword(
    *,
    current_line: str,
    cursor_column: int,
    has_steps_before: bool,
) -> str:
    """Pick Gherkin keyword for a new step at the cursor."""
    if current_line.strip() and line_has_step_keyword(current_line):
        return "И"
    prefix = current_line[:cursor_column]
    prefix_stripped = prefix.strip()
    if prefix_stripped and not prefix_stripped.startswith("#"):
        if line_has_step_keyword(prefix) or is_step_indented(prefix):
            return "И"
    if has_steps_before:
        return "И"
    return "Допустим"


def is_gherkin_step_line(line: str) -> bool:
    stripped = line.strip()
    if not stripped or stripped.startswith("#"):
        return False
    if _STEP_HEADER_RE.match(stripped):
        return False
    if _OUTLINE_HEADER_RE.match(stripped) or _EXAMPLES_HEADER_RE.match(stripped):
        return False
    if stripped.startswith("|"):
        return False
    if is_step_indented(line):
        return True
    return bool(re.match(r"^(?:Допустим|Дано|Когда|Тогда|И|Но)\s+", stripped, flags=re.IGNORECASE))


@dataclass
class GherkinParseError(ValueError):
    line_no: int
    line_text: str
    reason: str

    def __str__(self) -> str:
        return f"Строка {self.line_no}: {self.reason} → {self.line_text}"


@dataclass
class FeatureStructure:
    feature_line: str
    tags: list[str]
    scenario_name: str
    before_steps: list[str]
    step_lines: list[str]
    interstitial: list[list[str]]
    after_steps: list[str] = field(default_factory=list)
    has_context_block: bool = False
    context_lines: list[str] = field(default_factory=list)


def normalize_tag_name(raw: str) -> str:
    text = raw.strip()
    if text.startswith("@"):
        text = text[1:]
    return text.strip()


def extract_tags(lines: list[str], *, stop_at_scenario: bool = True) -> list[str]:
    """Return scenario tags from lines before ``Сценарий:`` (without ``@``)."""
    tags: list[str] = []
    for raw in lines:
        stripped = raw.strip()
        if not stripped:
            continue
        if stop_at_scenario and _SCENARIO_LINE_RE.match(stripped):
            break
        match = _TAG_LINE_RE.match(stripped)
        if match:
            name = normalize_tag_name(match.group(1))
            if name:
                tags.append(name)
    return tags


def parse_feature_structure(text: str) -> FeatureStructure:
    """Parse headers, tags, comments and step lines from a `.feature` file."""
    lines = text.replace("\r\n", "\n").splitlines()
    feature_line = "Функционал: UI сценарий"
    tags: list[str] = []
    scenario_name = "Сценарий"
    before_steps: list[str] = []
    step_lines: list[str] = []
    interstitial: list[list[str]] = []
    after_steps: list[str] = []
    has_context_block = False
    context_lines: list[str] = []
    pending: list[str] = []
    phase: Literal["header", "context", "before_steps", "steps", "after"] = "header"
    saw_scenario = False
    skip_outline = False

    for raw in lines:
        stripped = raw.strip()
        if skip_outline:
            if _EXAMPLES_HEADER_RE.match(stripped):
                continue
            if stripped.startswith("|") or not stripped:
                continue
            skip_outline = False

        if phase == "header":
            if not stripped:
                continue
            if _OUTLINE_HEADER_RE.match(stripped):
                skip_outline = True
                continue
            feature_match = _FEATURE_LINE_RE.match(stripped)
            if feature_match:
                feature_line = raw.rstrip()
                continue
            if _CONTEXT_LINE_RE.match(stripped):
                has_context_block = True
                phase = "context"
                continue
            tag_match = _TAG_LINE_RE.match(stripped)
            if tag_match:
                name = normalize_tag_name(tag_match.group(1))
                if name:
                    tags.append(name)
                continue
            scenario_match = _SCENARIO_LINE_RE.match(stripped)
            if scenario_match:
                scenario_name = scenario_match.group(1).strip() or "Сценарий"
                saw_scenario = True
                phase = "before_steps"
                continue
            if _STEP_HEADER_RE.match(stripped):
                continue
            if is_gherkin_step_line(raw):
                saw_scenario = True
                phase = "steps"
            else:
                continue

        if phase == "context":
            if not stripped:
                context_lines.append(raw)
                continue
            if stripped.startswith("#"):
                context_lines.append(raw)
                continue
            if is_gherkin_step_line(raw):
                context_lines.append(raw)
                continue
            phase = "header"
            if _TAG_LINE_RE.match(stripped):
                name = normalize_tag_name(_TAG_LINE_RE.match(stripped).group(1))
                if name:
                    tags.append(name)
                continue
            if _SCENARIO_LINE_RE.match(stripped):
                scenario_name = _SCENARIO_LINE_RE.match(stripped).group(1).strip() or "Сценарий"
                saw_scenario = True
                phase = "before_steps"
                continue
            if _STEP_HEADER_RE.match(stripped):
                continue
            if is_gherkin_step_line(raw):
                saw_scenario = True
                phase = "steps"
            else:
                continue

        if phase == "before_steps":
            if not stripped:
                before_steps.append(raw)
                continue
            if stripped.startswith("#"):
                before_steps.append(raw)
                continue
            if is_gherkin_step_line(raw):
                phase = "steps"
            else:
                before_steps.append(raw)
                continue

        if phase == "steps":
            if skip_outline:
                continue
            if not stripped:
                if step_lines:
                    pending.append(raw)
                else:
                    before_steps.append(raw)
                continue
            if stripped.startswith("#"):
                pending.append(raw)
                continue
            if is_gherkin_step_line(raw):
                interstitial.append(list(pending))
                pending = []
                step_lines.append(raw)
                continue
            if step_lines:
                phase = "after"
                after_steps.append(raw)
            else:
                before_steps.append(raw)
            continue

        if phase == "after":
            after_steps.append(raw)

    if not saw_scenario and not step_lines:
        interstitial = []
    elif pending and step_lines:
        after_steps = pending + after_steps

    return FeatureStructure(
        feature_line=feature_line,
        tags=tags,
        scenario_name=scenario_name,
        before_steps=before_steps,
        step_lines=step_lines,
        interstitial=interstitial,
        after_steps=after_steps,
        has_context_block=has_context_block,
        context_lines=context_lines,
    )


def _unquote(value: str) -> str:
    return value.replace(r"\"", '"').replace(r"\\", "\\")


def _quote(value: str) -> str:
    return str(value).replace("\\", r"\\").replace('"', r"\"")


from app.gherkin_parse import (
    coalesce_mixed_step_indents_in_text,
    gherkin_to_steps,
    normalize_gherkin_text,
    normalize_legacy_has_text_escapes,
    parse_gherkin_steps,
    repair_unclosed_step_quotes,
    try_repair_step_quote_on_line,
    try_repair_terminal_step_quote,
)
from app.gherkin_serialize import (
    build_feature_text,
    merge_steps_into_feature_text,
    steps_to_gherkin,
    steps_to_gherkin_body_lines,
)

__all__ = [
    "GHERKIN_KEYWORDS",
    "STEP_INDENT",
    "FeatureStructure",
    "GherkinParseError",
    "block_text_has_step_content",
    "build_feature_text",
    "coalesce_mixed_step_indents_in_text",
    "extract_tags",
    "format_step_line",
    "gherkin_to_steps",
    "is_gherkin_step_line",
    "is_step_indented",
    "leading_indent",
    "line_has_step_keyword",
    "merge_steps_into_feature_text",
    "normalize_gherkin_text",
    "normalize_legacy_has_text_escapes",
    "normalize_tag_name",
    "parse_feature_structure",
    "parse_gherkin_steps",
    "repair_unclosed_step_quotes",
    "steps_to_gherkin",
    "steps_to_gherkin_body_lines",
    "suggest_step_keyword",
    "try_repair_step_quote_on_line",
    "try_repair_terminal_step_quote",
]
