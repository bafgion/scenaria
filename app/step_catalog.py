"""Step knowledge base: categories, parameters, and line-to-entry resolution."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Literal

from app.gherkin_ru import GherkinParseError, STEP_INDENT, parse_gherkin_steps
from app.gherkin_snippets import GherkinSnippet, STEP_SNIPPETS

_ACTION_RE = re.compile(r"\(action:\s*(\w+)\)", re.IGNORECASE)
_KEYWORD_PREFIX_RE = re.compile(
    r"^(?:Допустим|Когда|Тогда|И|Но)\s+",
    re.IGNORECASE,
)

StepCategory = Literal["navigation", "forms", "assert", "wait", "session", "files", "generators"]

CATEGORY_LABELS: dict[str, str] = {
    "all": "Все",
    "navigation": "Навигация",
    "forms": "Формы и ввод",
    "assert": "Проверки",
    "wait": "Ожидание",
    "session": "Сессия",
    "files": "Файлы",
    "generators": "Генераторы",
}

ACTION_CATEGORY: dict[str, StepCategory] = {
    "goto": "navigation",
    "go_back": "navigation",
    "reload": "navigation",
    "scroll_to": "navigation",
    "click": "forms",
    "double_click": "forms",
    "hover": "forms",
    "fill": "forms",
    "fill_generated": "generators",
    "clear": "forms",
    "select": "forms",
    "check": "forms",
    "uncheck": "forms",
    "press": "forms",
    "prompt_email_code": "forms",
    "upload": "files",
    "download_click": "files",
    "assert_download_contains": "files",
    "remember_text": "forms",
    "remember_field": "forms",
    "remember_url": "navigation",
    "assert_visible": "assert",
    "assert_hidden": "assert",
    "assert_text": "assert",
    "assert_url": "assert",
    "wait": "wait",
    "wait_for": "wait",
    "wait_for_hidden": "wait",
    "close_browser": "session",
}

ACTION_PARAMS: dict[str, tuple[str, ...]] = {
    "goto": ('url — адрес страницы в кавычках',),
    "click": ('selector — CSS/XPath селектор элемента',),
    "double_click": ('selector — элемент для двойного клика',),
    "hover": ('selector — элемент для наведения',),
    "fill": ('value — текст; selector — поле ввода',),
    "fill_generated": ('generator — тип данных; selector — поле ввода',),
    "clear": ('selector — поле ввода',),
    "select": ('value — значение option; selector — элемент select',),
    "check": ('selector — checkbox или radio',),
    "uncheck": ('selector — checkbox',),
    "press": ('key — имя клавиши (Enter, Tab…); selector — опционально',),
    "prompt_email_code": ('digits/selector — ячейки OTP; email — опционально',),
    "upload": ('file_path — путь к файлу; selector — input[type=file]',),
    "download_click": ('selector — ссылка или кнопка скачивания',),
    "assert_download_contains": ('text — подстрока в скачанном файле',),
    "remember_text": ('value — текст; variable — имя переменной',),
    "remember_field": ('selector — поле; variable — имя переменной',),
    "remember_url": ('variable — имя для текущего URL',),
    "draw_signature": ('selector — элемент canvas',),
    "scroll_to": ('selector — элемент, к которому прокрутить',),
    "assert_visible": ('selector — видимый элемент',),
    "assert_hidden": ('selector — скрытый элемент',),
    "assert_text": ('text — ожидаемый текст; selector — контейнер',),
    "assert_url": ('url — ожидаемый адрес страницы',),
    "wait": ('seconds — длительность паузы',),
    "wait_for": ('selector — элемент, появление которого ждём',),
    "wait_for_hidden": ('selector — элемент, исчезновение которого ждём',),
}


@dataclass(frozen=True)
class StepEntry:
    id: str
    label: str
    action: str
    category: StepCategory
    description: str
    example: str
    parameters: tuple[str, ...]
    snippet: GherkinSnippet


def _action_from_description(description: str) -> str:
    match = _ACTION_RE.search(description)
    return match.group(1) if match else ""


def _plain_description(description: str) -> str:
    return _ACTION_RE.sub("", description).strip(" .") or description


def _build_catalog() -> tuple[StepEntry, ...]:
    entries: list[StepEntry] = []
    for index, snippet in enumerate(STEP_SNIPPETS):
        action = _action_from_description(snippet.description)
        category: StepCategory = ACTION_CATEGORY.get(action, "forms")
        params = ACTION_PARAMS.get(action, ())
        entries.append(
            StepEntry(
                id=f"{action or 'step'}-{index}",
                label=snippet.label,
                action=action,
                category=category,
                description=_plain_description(snippet.description),
                example=snippet.insert,
                parameters=params,
                snippet=snippet,
            )
        )
    return tuple(entries)


CATALOG: tuple[StepEntry, ...] = _build_catalog()


def list_step_entries(
    *,
    query: str = "",
    category: str = "all",
) -> list[StepEntry]:
    needle = query.strip().lower()
    result: list[StepEntry] = []
    for entry in CATALOG:
        if category != "all" and entry.category != category:
            continue
        if needle:
            haystack = " ".join(
                (entry.label, entry.action, entry.description, entry.example, entry.category)
            ).lower()
            if needle not in haystack:
                continue
        result.append(entry)
    return result


def entry_by_id(entry_id: str) -> StepEntry | None:
    for entry in CATALOG:
        if entry.id == entry_id:
            return entry
    return None


def entry_for_action(action: str, *, line_body: str = "") -> StepEntry | None:
    candidates = [entry for entry in CATALOG if entry.action == action]
    if not candidates:
        return None
    if len(candidates) == 1:
        return candidates[0]
    body = line_body.lower()
    for entry in candidates:
        if body.startswith(entry.label.lower()):
            return entry
    if action == "fill_generated":
        for entry in candidates:
            if entry.label.lower() in body:
                return entry
    return candidates[0]


def _normalize_line_for_parse(line: str) -> str:
    stripped = line.strip()
    if not stripped or stripped.startswith("#"):
        return ""
    if _KEYWORD_PREFIX_RE.match(stripped):
        return f"{STEP_INDENT}{stripped}"
    return f"{STEP_INDENT}Допустим {stripped}"


def _step_body(line: str) -> str:
    stripped = line.strip()
    return _KEYWORD_PREFIX_RE.sub("", stripped, count=1).strip()


def parse_step_dict_from_line(line: str) -> dict[str, Any] | None:
    normalized = _normalize_line_for_parse(line)
    if not normalized:
        return None
    wrapper = f"Функционал: _\nСценарий: _\n{normalized}"
    try:
        steps, _ = parse_gherkin_steps(wrapper)
    except GherkinParseError:
        return None
    return steps[-1] if steps else None


def resolve_step_entry(*, text: str = "", line_no: int | None = None, line: str = "") -> StepEntry | None:
    if line_no is not None and text:
        lines = text.splitlines()
        if 1 <= line_no <= len(lines):
            line = lines[line_no - 1]
    if not line.strip():
        return None
    step = parse_step_dict_from_line(line)
    if step is not None:
        found = entry_for_action(str(step.get("action", "")), line_body=_step_body(line))
        if found is not None:
            return found
    body = _step_body(line).lower()
    for entry in CATALOG:
        if body.startswith(entry.label.lower()):
            return entry
    return None


def format_entry_help(entry: StepEntry) -> str:
    lines = [
        f"<h3>{entry.label}</h3>",
        f"<p><b>Действие:</b> <code>{entry.action or '—'}</code></p>",
        f"<p><b>Категория:</b> {CATEGORY_LABELS.get(entry.category, entry.category)}</p>",
        f"<p>{entry.description}</p>",
    ]
    if entry.parameters:
        items = "".join(f"<li>{param}</li>" for param in entry.parameters)
        lines.append(f"<p><b>Параметры:</b></p><ul>{items}</ul>")
    lines.append(f'<p><b>Пример:</b></p><pre>{entry.example}</pre>')
    return "\n".join(lines)
