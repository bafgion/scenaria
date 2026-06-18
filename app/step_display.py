"""Human-readable scenario step formatting for the UI."""

from __future__ import annotations

import json
from typing import Any

ACTION_ICONS = {
    "goto": "🔗",
    "hover": "🖱",
    "click": "👆",
    "double_click": "👆👆",
    "fill": "⌨️",
    "fill_generated": "🎲",
    "clear": "🧹",
    "select": "📋",
    "check": "☑️",
    "uncheck": "⬜",
    "press": "⌨",
    "upload": "📎",
    "scroll_to": "↕️",
    "draw_signature": "✍️",
    "reload": "🔄",
    "go_back": "◀️",
    "close_browser": "🚪",
    "assert_visible": "👁",
    "assert_hidden": "🙈",
    "assert_text": "📝",
    "assert_url": "🌐",
    "wait": "⏱",
    "wait_for": "⏳",
    "wait_for_hidden": "💨",
    "prompt_email_code": "📧",
}


def format_step_table_cells(step: dict[str, Any]) -> tuple[str, str, str]:
    """Return action label, target summary, value column for table view."""
    action = step.get("action", "")
    icon = ACTION_ICONS.get(action, "•")
    labels = {
        "goto": "Переход",
        "hover": "Наведение",
        "click": "Клик",
        "double_click": "Двойной клик",
        "fill": "Ввод",
        "fill_generated": "Генерация",
        "clear": "Очистка",
        "select": "Выбор",
        "check": "Галочка",
        "uncheck": "Снять галочку",
        "press": "Клавиша",
        "upload": "Файл",
        "scroll_to": "Скролл",
        "draw_signature": "Подпись",
        "reload": "Обновление",
        "go_back": "Назад",
        "close_browser": "Закрыть",
        "assert_visible": "Видимость",
        "assert_hidden": "Скрыт",
        "assert_text": "Текст",
        "assert_url": "URL",
        "wait": "Пауза",
        "wait_for": "Ожидание",
        "wait_for_hidden": "Исчезновение",
        "prompt_email_code": "Код из почты",
    }
    action_label = f"{icon} {labels.get(action, action)}"
    if action == "goto":
        return action_label, step.get("url", ""), ""
    if action in {"hover", "click", "double_click"}:
        text = (step.get("text") or "").strip()
        target = step.get("selector", "")
        if text:
            target = f"{text} · {target}"
        return action_label, target, ""
    if action == "clear":
        return action_label, step.get("selector", ""), ""
    if action in {"check", "uncheck", "scroll_to", "draw_signature"}:
        return action_label, step.get("selector", ""), ""
    if action == "press":
        return action_label, step.get("selector", "") or "страница", step.get("key", "")
    if action == "upload":
        return action_label, step.get("selector", ""), step.get("path", "")
    if action == "reload":
        return action_label, "", ""
    if action == "go_back":
        return action_label, "", ""
    if action == "close_browser":
        return action_label, "", ""
    if action == "fill":
        value = step.get("value", "")
        if step.get("inputType") == "password":
            value = "***"
        return action_label, step.get("selector", ""), value
    if action == "fill_generated":
        from app.run_variables import generator_gherkin_phrase

        return action_label, step.get("selector", ""), generator_gherkin_phrase(str(step.get("generator", "")))
    if action == "prompt_email_code":
        digits = step.get("digits")
        email = step.get("email", "") or "из письма"
        method = step.get("inputMethod")
        suffix = f", {digits} полей" if digits else ""
        if method == "keyboard":
            suffix += ", клавиатура"
        elif method == "fill":
            suffix += ", fill"
        return action_label, step.get("selector", ""), f"{email}{suffix}"
    if action == "select":
        return action_label, step.get("selector", ""), step.get("value", "")
    if action == "assert_visible":
        return action_label, step.get("selector", ""), ""
    if action == "assert_hidden":
        return action_label, step.get("selector", ""), ""
    if action == "assert_text":
        return action_label, step.get("selector", ""), step.get("value", "")
    if action == "assert_url":
        return action_label, step.get("url", ""), ""
    if action == "wait":
        ms = int(step.get("ms", 0))
        if ms >= 1000 and ms % 1000 == 0:
            return action_label, f"{ms // 1000} сек", ""
        return action_label, f"{ms} мс", ""
    if action == "wait_for":
        return action_label, step.get("selector", ""), ""
    if action == "wait_for_hidden":
        return action_label, step.get("selector", ""), ""
    return action_label, str(step.get("selector", "")), step.get("value", "") or ""


def step_matches_query(step: dict[str, Any], query: str) -> bool:
    if not query:
        return True
    haystack = " ".join(
        str(step.get(key, "") or "")
        for key in ("action", "selector", "value", "url", "text", "hoverSelector", "key", "path", "email", "digits", "inputMethod")
    ).lower()
    return query in haystack


def collapse_duplicate_gotos(steps: list[dict[str, Any]]) -> list[dict[str, Any]]:
    from app.steps import normalize_steps

    return normalize_steps(list(steps))


def format_step_line(index: int, step: dict[str, Any]) -> str:
    action = step.get("action", "")
    icon = ACTION_ICONS.get(action, "•")
    if action == "goto":
        return f"{index}. {icon} Переход → {step.get('url', '')}"
    if action == "hover":
        text = (step.get("text") or "").strip()
        suffix = f' («{text}»)' if text else ""
        return f"{index}. {icon} Наведение → {step.get('selector', '')}{suffix}"
    if action == "click":
        text = (step.get("text") or "").strip()
        suffix = f' («{text}»)' if text else ""
        return f"{index}. {icon} Клик → {step.get('selector', '')}{suffix}"
    if action == "double_click":
        return f"{index}. {icon} Двойной клик → {step.get('selector', '')}"
    if action == "fill":
        value = step.get("value", "")
        if step.get("inputType") == "password":
            value = "***"
        return f"{index}. {icon} Ввод → {step.get('selector', '')} = {value}"
    if action == "fill_generated":
        from app.run_variables import generator_gherkin_phrase

        label = generator_gherkin_phrase(str(step.get("generator", "")))
        return f"{index}. {icon} {label} → {step.get('selector', '')}"
    if action == "prompt_email_code":
        email = str(step.get("email", "") or "").strip()
        digits = step.get("digits")
        method = str(step.get("inputMethod", "") or "").lower()
        suffix = f" ({email})" if email else ""
        cells = f", {digits} ячеек" if digits else ""
        input_hint = ", клавиатура" if method == "keyboard" else ", fill" if method == "fill" else ""
        return f"{index}. {icon} Код из почты{suffix}{cells}{input_hint} → {step.get('selector', '')}"
    if action == "select":
        return f"{index}. {icon} Выбор → {step.get('selector', '')} = {step.get('value', '')}"
    if action == "clear":
        return f"{index}. {icon} Очистка → {step.get('selector', '')}"
    if action == "check":
        return f"{index}. {icon} Галочка → {step.get('selector', '')}"
    if action == "uncheck":
        return f"{index}. {icon} Снять галочку → {step.get('selector', '')}"
    if action == "press":
        target = step.get("selector", "") or "страница"
        return f"{index}. {icon} Клавиша {step.get('key', '')} → {target}"
    if action == "upload":
        return f"{index}. {icon} Файл → {step.get('path', '')} в {step.get('selector', '')}"
    if action == "scroll_to":
        return f"{index}. {icon} Скролл → {step.get('selector', '')}"
    if action == "draw_signature":
        return f"{index}. {icon} Подпись → {step.get('selector', '')}"
    if action == "reload":
        return f"{index}. {icon} Обновление страницы"
    if action == "go_back":
        return f"{index}. {icon} Назад"
    if action == "close_browser":
        return f"{index}. {icon} Закрыть браузер"
    if action == "assert_visible":
        return f"{index}. {icon} Видимость → {step.get('selector', '')}"
    if action == "assert_hidden":
        return f"{index}. {icon} Скрыт → {step.get('selector', '')}"
    if action == "assert_text":
        return f"{index}. {icon} Текст «{step.get('value', '')}» → {step.get('selector', '')}"
    if action == "assert_url":
        return f"{index}. {icon} URL → {step.get('url', '')}"
    if action == "wait":
        ms = int(step.get("ms", 0))
        label = f"{ms // 1000} сек" if ms >= 1000 and ms % 1000 == 0 else f"{ms} мс"
        return f"{index}. {icon} Пауза → {label}"
    if action == "wait_for":
        return f"{index}. {icon} Ожидание → {step.get('selector', '')}"
    if action == "wait_for_hidden":
        return f"{index}. {icon} Исчезновение → {step.get('selector', '')}"
    return f"{index}. {icon} {action} → {step}"


def format_steps_human(steps: list[dict[str, Any]]) -> str:
    if not steps:
        return "Шагов пока нет. Начните запись и выполните действия в браузере."
    return "\n".join(format_step_line(i, step) for i, step in enumerate(steps, start=1))


def format_steps_json(steps: list[dict[str, Any]]) -> str:
    return json.dumps(steps, ensure_ascii=False, indent=2)
