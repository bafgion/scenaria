"""Serialize recorder step dicts to Russian Gherkin-like text."""

from __future__ import annotations

from typing import Any

from app.gherkin_ru import (
    STEP_INDENT,
    FeatureStructure,
    _quote,
    format_step_line,
    normalize_tag_name,
    parse_feature_structure,
)
from app.run_variables import generator_gherkin_phrase


def steps_to_gherkin_body_lines(steps: list[dict[str, Any]]) -> list[str]:
    """Serialize only indented step lines (no feature/scenario header)."""
    if not steps:
        return []
    full = steps_to_gherkin(steps, scenario_name="__body__")
    body: list[str] = []
    for line in full.splitlines():
        if line.startswith("Функционал:") or line.startswith("Сценарий:"):
            continue
        if line.strip():
            body.append(line)
    return body


def build_feature_text(
    structure: FeatureStructure,
    steps: list[dict[str, Any]],
    *,
    tags: list[str] | None = None,
    scenario_name: str | None = None,
) -> str:
    """Rebuild feature text, preserving comments and replacing step lines."""
    resolved_tags = list(tags if tags is not None else structure.tags)
    resolved_name = (scenario_name or structure.scenario_name or "Сценарий").strip() or "Сценарий"
    new_step_lines = steps_to_gherkin_body_lines(steps)

    lines: list[str] = [structure.feature_line]
    if structure.has_context_block:
        lines.append("Контекст:")
        lines.extend(structure.context_lines)
    for tag in resolved_tags:
        lines.append(f"@{tag}")
    lines.append(f"Сценарий: {resolved_name}")
    lines.extend(structure.before_steps)

    for index, step_line in enumerate(new_step_lines):
        if index < len(structure.interstitial):
            lines.extend(structure.interstitial[index])
        lines.append(step_line)
    if len(structure.interstitial) > len(new_step_lines):
        for extra in structure.interstitial[len(new_step_lines) :]:
            lines.extend(extra)
    lines.extend(structure.after_steps)
    return "\n".join(lines)


def merge_steps_into_feature_text(
    source_text: str | None,
    steps: list[dict[str, Any]],
    *,
    tags: list[str] | None = None,
    scenario_name: str = "Сценарий",
) -> str:
    """Update steps (and optional tags) while keeping comments from *source_text*."""
    structure = parse_feature_structure(source_text or "")
    if not source_text or not source_text.strip():
        return steps_to_gherkin(steps, scenario_name=scenario_name, tags=tags or [])
    return build_feature_text(
        structure,
        steps,
        tags=tags,
        scenario_name=scenario_name,
    )


def _email_code_method_prefix(step: dict[str, Any]) -> str:
    method = str(step.get("inputMethod", "") or "").lower()
    if method == "keyboard":
        return "с клавиатуры "
    if method == "fill":
        return "заполнением "
    return ""


def _append_step_lines(
    lines: list[str],
    steps: list[dict[str, Any]],
    *,
    indent: str = STEP_INDENT,
) -> None:
    """Append serialized Gherkin step lines."""
    first = True
    for index, step in enumerate(steps):
        action = step.get("action")
        prefix = "Допустим" if first else "И"

        if action == "if":
            from app.gherkin_blocks import condition_to_gherkin

            cond = condition_to_gherkin(step.get("condition") or {})
            lines.append(f"{indent}Если {cond}")
            nested = step.get("steps") or []
            if nested:
                _append_step_lines(lines, nested, indent=indent + STEP_INDENT)
            first = False
            continue

        if action == "repeat":
            count = max(1, int(step.get("count") or 1))
            lines.append(f"{indent}Повторяю {count} раза")
            nested = step.get("steps") or []
            if nested:
                _append_step_lines(lines, nested, indent=indent + STEP_INDENT)
            first = False
            continue

        if action == "while":
            from app.gherkin_blocks import condition_to_gherkin

            cond = condition_to_gherkin(step.get("condition") or {})
            lines.append(f"{indent}Пока {cond}")
            nested = step.get("steps") or []
            if nested:
                _append_step_lines(lines, nested, indent=indent + STEP_INDENT)
            first = False
            continue

        if action == "for_each":
            selector = _quote(step.get("selector", ""))
            variable = _quote(step.get("variable", ""))
            lines.append(f'{indent}Для каждого "{selector}" как "{variable}"')
            nested = step.get("steps") or []
            if nested:
                _append_step_lines(lines, nested, indent=indent + STEP_INDENT)
            first = False
            continue

        if action == "goto":
            lines.append(format_step_line(prefix, f'открыт "{_quote(step.get("url", ""))}"', indent=indent))
        elif action == "double_click":
            lines.append(
                format_step_line(prefix, f'дважды нажимаю "{_quote(step.get("selector", ""))}"', indent=indent)
            )
        elif action == "press":
            key = _quote(step.get("key", ""))
            selector = str(step.get("selector", "") or "").strip()
            if selector:
                lines.append(
                    format_step_line(prefix, f'нажимаю клавишу "{key}" в "{_quote(selector)}"', indent=indent)
                )
            else:
                lines.append(format_step_line(prefix, f'нажимаю клавишу "{key}"', indent=indent))
        elif action == "click":
            hover_selector = str(step.get("hoverSelector", "") or "").strip()
            prev = steps[index - 1] if index > 0 else None
            needs_hover_line = hover_selector and not (
                prev
                and prev.get("action") == "hover"
                and str(prev.get("selector", "") or "").strip() == hover_selector
            )
            if needs_hover_line:
                lines.append(format_step_line(prefix, f'навожу "{_quote(hover_selector)}"', indent=indent))
                prefix = "И"
            lines.append(format_step_line(prefix, f'нажимаю "{_quote(step.get("selector", ""))}"', indent=indent))
        elif action == "hover":
            lines.append(format_step_line(prefix, f'навожу "{_quote(step.get("selector", ""))}"', indent=indent))
        elif action == "fill":
            lines.append(
                format_step_line(
                    prefix,
                    f'ввожу "{_quote(step.get("value", ""))}" в "{_quote(step.get("selector", ""))}"',
                    indent=indent,
                )
            )
        elif action == "fill_generated":
            phrase = generator_gherkin_phrase(str(step.get("generator", "")))
            lines.append(
                format_step_line(
                    prefix,
                    f'ввожу {phrase} в "{_quote(step.get("selector", ""))}"',
                    indent=indent,
                )
            )
        elif action == "prompt_email_code":
            email = str(step.get("email", "") or "").strip()
            selector = _quote(step.get("selector", ""))
            digits = step.get("digits")
            method_prefix = _email_code_method_prefix(step)
            if digits:
                if email:
                    lines.append(
                        format_step_line(
                            prefix,
                            f'ввожу код из почты {method_prefix}"{_quote(email)}" в {digits} полей "{selector}"',
                            indent=indent,
                        )
                    )
                else:
                    lines.append(
                        format_step_line(
                            prefix,
                            f'ввожу код из почты {method_prefix}в {digits} полей "{selector}"',
                            indent=indent,
                        )
                    )
            elif email:
                lines.append(
                    format_step_line(
                        prefix,
                        f'ввожу код из почты {method_prefix}"{_quote(email)}" в "{selector}"',
                        indent=indent,
                    )
                )
            else:
                lines.append(
                    format_step_line(prefix, f'ввожу код из почты {method_prefix}в "{selector}"', indent=indent)
                )
        elif action == "select":
            lines.append(
                format_step_line(
                    prefix,
                    f'выбираю "{_quote(step.get("value", ""))}" в "{_quote(step.get("selector", ""))}"',
                    indent=indent,
                )
            )
        elif action == "upload":
            lines.append(
                format_step_line(
                    prefix,
                    f'загружаю файл "{_quote(step.get("path", ""))}" в "{_quote(step.get("selector", ""))}"',
                    indent=indent,
                )
            )
        elif action == "download_click":
            lines.append(
                format_step_line(
                    prefix,
                    f'скачиваю по клику на "{_quote(step.get("selector", ""))}"',
                    indent=indent,
                )
            )
        elif action == "assert_download_contains":
            lines.append(
                format_step_line(
                    prefix,
                    f'проверяю что скачанный файл содержит "{_quote(step.get("value", ""))}"',
                    indent=indent,
                )
            )
        elif action == "remember_text":
            lines.append(
                format_step_line(
                    prefix,
                    f'запоминаю текст "{_quote(step.get("value", ""))}" как "{_quote(step.get("variable", ""))}"',
                    indent=indent,
                )
            )
        elif action == "remember_field":
            lines.append(
                format_step_line(
                    prefix,
                    f'запоминаю значение поля "{_quote(step.get("selector", ""))}" как "{_quote(step.get("variable", ""))}"',
                    indent=indent,
                )
            )
        elif action == "remember_url":
            lines.append(
                format_step_line(
                    prefix,
                    f'запоминаю url как "{_quote(step.get("variable", ""))}"',
                    indent=indent,
                )
            )
        elif action == "clear":
            lines.append(format_step_line(prefix, f'очищаю "{_quote(step.get("selector", ""))}"', indent=indent))
        elif action == "draw_signature":
            lines.append(
                format_step_line(prefix, f'рисую подпись в "{_quote(step.get("selector", ""))}"', indent=indent)
            )
        elif action == "check":
            lines.append(format_step_line(prefix, f'отмечаю "{_quote(step.get("selector", ""))}"', indent=indent))
        elif action == "uncheck":
            lines.append(
                format_step_line(prefix, f'снимаю отметку с "{_quote(step.get("selector", ""))}"', indent=indent)
            )
        elif action == "assert_hidden":
            lines.append(format_step_line(prefix, f'не вижу "{_quote(step.get("selector", ""))}"', indent=indent))
        elif action == "assert_visible":
            lines.append(format_step_line(prefix, f'вижу "{_quote(step.get("selector", ""))}"', indent=indent))
        elif action == "assert_text":
            lines.append(
                format_step_line(
                    prefix,
                    f'проверяю текст "{_quote(step.get("value", ""))}" в "{_quote(step.get("selector", ""))}"',
                    indent=indent,
                )
            )
        elif action == "assert_url":
            lines.append(format_step_line(prefix, f'проверяю url "{_quote(step.get("url", ""))}"', indent=indent))
        elif action == "scroll_to":
            lines.append(format_step_line(prefix, f'скроллю к "{_quote(step.get("selector", ""))}"', indent=indent))
        elif action == "reload":
            lines.append(format_step_line(prefix, "обновляю страницу", indent=indent))
        elif action == "go_back":
            lines.append(format_step_line(prefix, "возвращаюсь назад", indent=indent))
        elif action == "close_browser":
            lines.append(format_step_line(prefix, "закрываю браузер", indent=indent))
        elif action == "switch_tab":
            mode = str(step.get("mode", "") or "")
            value = str(step.get("value", "") or "")
            if mode == "title":
                phrase = f'переключаюсь на вкладку "{_quote(value)}"'
            elif mode == "url":
                phrase = f'переключаюсь на вкладку с url "{_quote(value)}"'
            elif mode == "first":
                phrase = "переключаюсь на первую вкладку"
            elif mode == "new":
                phrase = "переключаюсь на новую вкладку"
            elif mode == "index":
                phrase = f"переключаюсь на вкладку {int(value) + 1}"
            else:
                phrase = f'переключаюсь на вкладку "{_quote(value)}"'
            lines.append(format_step_line(prefix, phrase, indent=indent))
        elif action == "close_tab":
            lines.append(format_step_line(prefix, "закрываю текущую вкладку", indent=indent))
        elif action == "assert_tab_count":
            count = int(step.get("count") or 0)
            lines.append(format_step_line(prefix, f"проверяю что открыто {count} вкладки", indent=indent))
        elif action == "wait":
            ms = max(0, int(step.get("ms", 1000)))
            if ms >= 1000 and ms % 1000 == 0:
                lines.append(format_step_line(prefix, f"жду {ms // 1000} сек", indent=indent))
            else:
                lines.append(format_step_line(prefix, f"жду {ms} мс", indent=indent))
        elif action == "wait_for":
            lines.append(
                format_step_line(prefix, f'жду появления "{_quote(step.get("selector", ""))}"', indent=indent)
            )
        elif action == "wait_for_hidden":
            lines.append(
                format_step_line(prefix, f'жду исчезновения "{_quote(step.get("selector", ""))}"', indent=indent)
            )
        else:
            lines.append(f'{indent}# Неподдерживаемый шаг "{action}"')
        first = False


def steps_to_gherkin(
    steps: list[dict[str, Any]],
    *,
    scenario_name: str = "Сценарий",
    include_template: bool = False,
    tags: list[str] | None = None,
) -> str:
    """Serialize recorder steps to Russian Gherkin-like text."""
    lines = ["Функционал: UI сценарий"]
    for tag in tags or []:
        name = normalize_tag_name(tag)
        if name:
            lines.append(f"@{name}")
    lines.append(f"Сценарий: {scenario_name or 'Сценарий'}")
    header_count = len(lines)
    _append_step_lines(lines, steps)
    if include_template and len(lines) == header_count:
        lines.append(f"{STEP_INDENT}# Добавьте шаги, например: Допустим открыт \"https://site.com\"")
    return "\n".join(lines)
