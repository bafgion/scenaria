"""Russian Gherkin-like parser/serializer for recorder steps."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from app.run_variables import GENERATOR_GHERKIN_PHRASES, generator_gherkin_phrase, normalize_generator_name

_KEYWORD_RE = re.compile(r"^(?:(?:Допустим|Когда|Тогда|И|Но)\s+)?(.+)$", re.IGNORECASE)
_STEP_HEADER_RE = re.compile(r"^(?:функционал|сценарий|функция)\s*:", re.IGNORECASE)
_GHERKIN_KW_PREFIX_RE = re.compile(r"^(?:Допустим|Когда|Тогда|И|Но)\s+", re.IGNORECASE)

GHERKIN_KEYWORDS: tuple[str, ...] = ("Допустим", "Когда", "Тогда", "И", "Но")

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


def format_step_line(keyword: str, body: str) -> str:
    return f"{STEP_INDENT}{keyword} {body}"


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
    if is_step_indented(line):
        return True
    return bool(re.match(r"^(?:Допустим|Когда|Тогда|И|Но)\s+", stripped, flags=re.IGNORECASE))


@dataclass
class GherkinParseError(ValueError):
    line_no: int
    line_text: str
    reason: str

    def __str__(self) -> str:
        return f"Строка {self.line_no}: {self.reason} → {self.line_text}"


def _unquote(value: str) -> str:
    return value.replace(r"\"", '"').replace(r"\\", "\\")


def _quote(value: str) -> str:
    return str(value).replace("\\", r"\\").replace('"', r"\"")


def _split_email_code_input_method(body: str) -> tuple[str, str | None]:
    match = re.match(
        r"^(ввожу\s+код\s+из\s+почты)\s+(с клавиатуры|заполнением)\s+(.+)$",
        body,
        flags=re.IGNORECASE,
    )
    if not match:
        return body, None
    if match.group(2).lower().startswith("с"):
        return f"{match.group(1)} {match.group(3)}", "keyboard"
    return f"{match.group(1)} {match.group(3)}", "fill"


def _email_code_method_prefix(step: dict[str, Any]) -> str:
    method = str(step.get("inputMethod", "") or "").lower()
    if method == "keyboard":
        return "с клавиатуры "
    if method == "fill":
        return "заполнением "
    return ""


def _parse_generated_fill(body: str) -> dict[str, Any] | None:
    match = re.fullmatch(
        r'ввожу\s+(.+?)\s+в\s+"((?:\\.|[^"])*)"',
        body,
        flags=re.IGNORECASE,
    )
    if not match:
        return None
    phrase = match.group(1).strip().lower().replace("ё", "е")
    for generator, label in GENERATOR_GHERKIN_PHRASES.items():
        if phrase == label.replace("ё", "е"):
            return {
                "action": "fill_generated",
                "generator": generator,
                "selector": _unquote(match.group(2)),
            }
    stripped = re.sub(r"^случайн\w*\s+", "", phrase)
    generator = normalize_generator_name(stripped)
    if generator is None:
        return None
    return {
        "action": "fill_generated",
        "generator": generator,
        "selector": _unquote(match.group(2)),
    }


def gherkin_to_steps(text: str) -> list[dict[str, Any]]:
    """Parse Russian Gherkin-like text into step dictionaries."""
    steps: list[dict[str, Any]] = []
    for line_no, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.lower().startswith("функционал:") or line.lower().startswith("сценарий:"):
            continue

        keyword_match = _KEYWORD_RE.match(line)
        if not keyword_match:
            raise GherkinParseError(line_no, line, "Не удалось разобрать шаг")
        body = keyword_match.group(1).strip()

        goto_match = re.fullmatch(r'открыт[а]?\s+"((?:\\.|[^"])*)"', body, flags=re.IGNORECASE)
        if goto_match:
            steps.append({"action": "goto", "url": _unquote(goto_match.group(1))})
            continue

        double_click_match = re.fullmatch(
            r'дважды\s+нажимаю\s+"((?:\\.|[^"])*)"',
            body,
            flags=re.IGNORECASE,
        )
        if double_click_match:
            steps.append({"action": "double_click", "selector": _unquote(double_click_match.group(1))})
            continue

        press_in_match = re.fullmatch(
            r'нажимаю\s+клавишу\s+"((?:\\.|[^"])*)"\s+в\s+"((?:\\.|[^"])*)"',
            body,
            flags=re.IGNORECASE,
        )
        if press_in_match:
            steps.append(
                {
                    "action": "press",
                    "key": _unquote(press_in_match.group(1)),
                    "selector": _unquote(press_in_match.group(2)),
                }
            )
            continue

        press_match = re.fullmatch(
            r'нажимаю\s+клавишу\s+"((?:\\.|[^"])*)"',
            body,
            flags=re.IGNORECASE,
        )
        if press_match:
            steps.append({"action": "press", "key": _unquote(press_match.group(1))})
            continue

        click_match = re.fullmatch(r'нажимаю\s+"((?:\\.|[^"])*)"', body, flags=re.IGNORECASE)
        if click_match:
            steps.append({"action": "click", "selector": _unquote(click_match.group(1))})
            continue

        hover_match = re.fullmatch(r'навожу\s+"((?:\\.|[^"])*)"', body, flags=re.IGNORECASE)
        if hover_match:
            steps.append({"action": "hover", "selector": _unquote(hover_match.group(1))})
            continue

        otp_body, otp_input_method = _split_email_code_input_method(body)

        email_code_segmented_with_email_match = re.fullmatch(
            r'ввожу\s+код\s+из\s+почты\s+"((?:\\.|[^"])*)"\s+в\s+(\d+)\s+полей\s+"((?:\\.|[^"])*)"',
            otp_body,
            flags=re.IGNORECASE,
        )
        if email_code_segmented_with_email_match:
            step = {
                "action": "prompt_email_code",
                "email": _unquote(email_code_segmented_with_email_match.group(1)),
                "digits": int(email_code_segmented_with_email_match.group(2)),
                "selector": _unquote(email_code_segmented_with_email_match.group(3)),
            }
            if otp_input_method:
                step["inputMethod"] = otp_input_method
            steps.append(step)
            continue

        email_code_segmented_match = re.fullmatch(
            r'ввожу\s+код\s+из\s+почты\s+в\s+(\d+)\s+полей\s+"((?:\\.|[^"])*)"',
            otp_body,
            flags=re.IGNORECASE,
        )
        if email_code_segmented_match:
            step = {
                "action": "prompt_email_code",
                "digits": int(email_code_segmented_match.group(1)),
                "selector": _unquote(email_code_segmented_match.group(2)),
            }
            if otp_input_method:
                step["inputMethod"] = otp_input_method
            steps.append(step)
            continue

        email_code_with_email_match = re.fullmatch(
            r'ввожу\s+код\s+из\s+почты\s+"((?:\\.|[^"])*)"\s+в\s+"((?:\\.|[^"])*)"',
            otp_body,
            flags=re.IGNORECASE,
        )
        if email_code_with_email_match:
            step = {
                "action": "prompt_email_code",
                "email": _unquote(email_code_with_email_match.group(1)),
                "selector": _unquote(email_code_with_email_match.group(2)),
            }
            if otp_input_method:
                step["inputMethod"] = otp_input_method
            steps.append(step)
            continue

        email_code_match = re.fullmatch(
            r'ввожу\s+код\s+из\s+почты\s+в\s+"((?:\\.|[^"])*)"',
            otp_body,
            flags=re.IGNORECASE,
        )
        if email_code_match:
            step = {
                "action": "prompt_email_code",
                "selector": _unquote(email_code_match.group(1)),
            }
            if otp_input_method:
                step["inputMethod"] = otp_input_method
            steps.append(step)
            continue

        fill_generated_step = _parse_generated_fill(body)
        if fill_generated_step is not None:
            steps.append(fill_generated_step)
            continue

        fill_match = re.fullmatch(
            r'ввожу\s+"((?:\\.|[^"])*)"\s+в\s+"((?:\\.|[^"])*)"',
            body,
            flags=re.IGNORECASE,
        )
        if fill_match:
            steps.append(
                {
                    "action": "fill",
                    "value": _unquote(fill_match.group(1)),
                    "selector": _unquote(fill_match.group(2)),
                }
            )
            continue

        select_match = re.fullmatch(
            r'выбираю\s+"((?:\\.|[^"])*)"\s+в\s+"((?:\\.|[^"])*)"',
            body,
            flags=re.IGNORECASE,
        )
        if select_match:
            steps.append(
                {
                    "action": "select",
                    "value": _unquote(select_match.group(1)),
                    "selector": _unquote(select_match.group(2)),
                }
            )
            continue

        upload_match = re.fullmatch(
            r'загружаю\s+файл\s+"((?:\\.|[^"])*)"\s+в\s+"((?:\\.|[^"])*)"',
            body,
            flags=re.IGNORECASE,
        )
        if upload_match:
            steps.append(
                {
                    "action": "upload",
                    "path": _unquote(upload_match.group(1)),
                    "selector": _unquote(upload_match.group(2)),
                }
            )
            continue

        clear_match = re.fullmatch(r'очищаю\s+"((?:\\.|[^"])*)"', body, flags=re.IGNORECASE)
        if clear_match:
            steps.append({"action": "clear", "selector": _unquote(clear_match.group(1))})
            continue

        sign_match = re.fullmatch(
            r'рисую\s+подпись\s+в\s+"((?:\\.|[^"])*)"',
            body,
            flags=re.IGNORECASE,
        )
        if sign_match:
            steps.append({"action": "draw_signature", "selector": _unquote(sign_match.group(1))})
            continue

        uncheck_match = re.fullmatch(
            r'снимаю\s+отметку\s+с\s+"((?:\\.|[^"])*)"',
            body,
            flags=re.IGNORECASE,
        )
        if uncheck_match:
            steps.append({"action": "uncheck", "selector": _unquote(uncheck_match.group(1))})
            continue

        check_match = re.fullmatch(r'отмечаю\s+"((?:\\.|[^"])*)"', body, flags=re.IGNORECASE)
        if check_match:
            steps.append({"action": "check", "selector": _unquote(check_match.group(1))})
            continue

        hidden_match = re.fullmatch(r'не\s+вижу\s+"((?:\\.|[^"])*)"', body, flags=re.IGNORECASE)
        if hidden_match:
            steps.append({"action": "assert_hidden", "selector": _unquote(hidden_match.group(1))})
            continue

        visible_match = re.fullmatch(r'вижу\s+"((?:\\.|[^"])*)"', body, flags=re.IGNORECASE)
        if visible_match:
            steps.append({"action": "assert_visible", "selector": _unquote(visible_match.group(1))})
            continue

        text_match = re.fullmatch(
            r'проверяю\s+текст\s+"((?:\\.|[^"])*)"\s+в\s+"((?:\\.|[^"])*)"',
            body,
            flags=re.IGNORECASE,
        )
        if text_match:
            steps.append(
                {
                    "action": "assert_text",
                    "value": _unquote(text_match.group(1)),
                    "selector": _unquote(text_match.group(2)),
                }
            )
            continue

        url_match = re.fullmatch(r'проверяю\s+url\s+"((?:\\.|[^"])*)"', body, flags=re.IGNORECASE)
        if url_match:
            steps.append({"action": "assert_url", "url": _unquote(url_match.group(1))})
            continue

        scroll_match = re.fullmatch(
            r'скроллю\s+к\s+"((?:\\.|[^"])*)"',
            body,
            flags=re.IGNORECASE,
        )
        if scroll_match:
            steps.append({"action": "scroll_to", "selector": _unquote(scroll_match.group(1))})
            continue

        if re.fullmatch(r"обновляю\s+страницу", body, flags=re.IGNORECASE):
            steps.append({"action": "reload"})
            continue

        if re.fullmatch(r"возвращаюсь\s+назад", body, flags=re.IGNORECASE):
            steps.append({"action": "go_back"})
            continue

        if re.fullmatch(r"закрываю\s+браузер", body, flags=re.IGNORECASE):
            steps.append({"action": "close_browser"})
            continue

        wait_hidden_match = re.fullmatch(
            r'жду\s+исчезновения\s+"((?:\\.|[^"])*)"',
            body,
            flags=re.IGNORECASE,
        )
        if wait_hidden_match:
            steps.append({"action": "wait_for_hidden", "selector": _unquote(wait_hidden_match.group(1))})
            continue

        wait_sec_match = re.fullmatch(
            r"жду\s+([\d.,]+)\s*(?:сек|секунд|сек|с)\b",
            body,
            flags=re.IGNORECASE,
        )
        if wait_sec_match:
            seconds = float(wait_sec_match.group(1).replace(",", "."))
            steps.append({"action": "wait", "ms": max(0, int(seconds * 1000))})
            continue

        wait_ms_match = re.fullmatch(r"жду\s+(\d+)\s*(?:мс|мсек)\b", body, flags=re.IGNORECASE)
        if wait_ms_match:
            steps.append({"action": "wait", "ms": max(0, int(wait_ms_match.group(1)))})
            continue

        wait_for_match = re.fullmatch(
            r'жду\s+появления\s+"((?:\\.|[^"])*)"',
            body,
            flags=re.IGNORECASE,
        )
        if wait_for_match:
            steps.append({"action": "wait_for", "selector": _unquote(wait_for_match.group(1))})
            continue

        raise GherkinParseError(
            line_no,
            line,
            "Неизвестный шаг — откройте Ctrl+Space для списка поддерживаемых шагов",
        )

    return steps


def steps_to_gherkin(
    steps: list[dict[str, Any]], *, scenario_name: str = "Сценарий", include_template: bool = False
) -> str:
    """Serialize recorder steps to Russian Gherkin-like text."""
    lines = ["Функционал: UI сценарий", f"Сценарий: {scenario_name or 'Сценарий'}"]
    first = True
    for index, step in enumerate(steps):
        action = step.get("action")
        prefix = "Допустим" if first else "И"
        first = False
        if action == "goto":
            lines.append(format_step_line(prefix, f'открыт "{_quote(step.get("url", ""))}"'))
        elif action == "double_click":
            lines.append(format_step_line(prefix, f'дважды нажимаю "{_quote(step.get("selector", ""))}"'))
        elif action == "press":
            key = _quote(step.get("key", ""))
            selector = str(step.get("selector", "") or "").strip()
            if selector:
                lines.append(format_step_line(prefix, f'нажимаю клавишу "{key}" в "{_quote(selector)}"'))
            else:
                lines.append(format_step_line(prefix, f'нажимаю клавишу "{key}"'))
        elif action == "click":
            hover_selector = str(step.get("hoverSelector", "") or "").strip()
            prev = steps[index - 1] if index > 0 else None
            needs_hover_line = hover_selector and not (
                prev
                and prev.get("action") == "hover"
                and str(prev.get("selector", "") or "").strip() == hover_selector
            )
            if needs_hover_line:
                lines.append(format_step_line(prefix, f'навожу "{_quote(hover_selector)}"'))
                prefix = "И"
            lines.append(format_step_line(prefix, f'нажимаю "{_quote(step.get("selector", ""))}"'))
        elif action == "hover":
            lines.append(format_step_line(prefix, f'навожу "{_quote(step.get("selector", ""))}"'))
        elif action == "fill":
            lines.append(
                format_step_line(
                    prefix,
                    f'ввожу "{_quote(step.get("value", ""))}" в "{_quote(step.get("selector", ""))}"',
                )
            )
        elif action == "fill_generated":
            phrase = generator_gherkin_phrase(str(step.get("generator", "")))
            lines.append(
                format_step_line(
                    prefix,
                    f'ввожу {phrase} в "{_quote(step.get("selector", ""))}"',
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
                        )
                    )
                else:
                    lines.append(
                        format_step_line(
                            prefix,
                            f'ввожу код из почты {method_prefix}в {digits} полей "{selector}"',
                        )
                    )
            elif email:
                lines.append(
                    format_step_line(
                        prefix,
                        f'ввожу код из почты {method_prefix}"{_quote(email)}" в "{selector}"',
                    )
                )
            else:
                lines.append(
                    format_step_line(prefix, f'ввожу код из почты {method_prefix}в "{selector}"')
                )
        elif action == "select":
            lines.append(
                format_step_line(
                    prefix,
                    f'выбираю "{_quote(step.get("value", ""))}" в "{_quote(step.get("selector", ""))}"',
                )
            )
        elif action == "upload":
            lines.append(
                format_step_line(
                    prefix,
                    f'загружаю файл "{_quote(step.get("path", ""))}" в "{_quote(step.get("selector", ""))}"',
                )
            )
        elif action == "clear":
            lines.append(format_step_line(prefix, f'очищаю "{_quote(step.get("selector", ""))}"'))
        elif action == "draw_signature":
            lines.append(
                format_step_line(prefix, f'рисую подпись в "{_quote(step.get("selector", ""))}"')
            )
        elif action == "check":
            lines.append(format_step_line(prefix, f'отмечаю "{_quote(step.get("selector", ""))}"'))
        elif action == "uncheck":
            lines.append(format_step_line(prefix, f'снимаю отметку с "{_quote(step.get("selector", ""))}"'))
        elif action == "assert_hidden":
            lines.append(format_step_line(prefix, f'не вижу "{_quote(step.get("selector", ""))}"'))
        elif action == "assert_visible":
            lines.append(format_step_line(prefix, f'вижу "{_quote(step.get("selector", ""))}"'))
        elif action == "assert_text":
            lines.append(
                format_step_line(
                    prefix,
                    f'проверяю текст "{_quote(step.get("value", ""))}" в "{_quote(step.get("selector", ""))}"',
                )
            )
        elif action == "assert_url":
            lines.append(format_step_line(prefix, f'проверяю url "{_quote(step.get("url", ""))}"'))
        elif action == "scroll_to":
            lines.append(format_step_line(prefix, f'скроллю к "{_quote(step.get("selector", ""))}"'))
        elif action == "reload":
            lines.append(format_step_line(prefix, "обновляю страницу"))
        elif action == "go_back":
            lines.append(format_step_line(prefix, "возвращаюсь назад"))
        elif action == "close_browser":
            lines.append(format_step_line(prefix, "закрываю браузер"))
        elif action == "wait":
            ms = max(0, int(step.get("ms", 1000)))
            if ms >= 1000 and ms % 1000 == 0:
                lines.append(format_step_line(prefix, f"жду {ms // 1000} сек"))
            else:
                lines.append(format_step_line(prefix, f"жду {ms} мс"))
        elif action == "wait_for":
            lines.append(format_step_line(prefix, f'жду появления "{_quote(step.get("selector", ""))}"'))
        elif action == "wait_for_hidden":
            lines.append(format_step_line(prefix, f'жду исчезновения "{_quote(step.get("selector", ""))}"'))
        else:
            lines.append(f"{STEP_INDENT}# Неподдерживаемый шаг \"{action}\"")
    if len(lines) == 2 and include_template:
        lines.append(f"{STEP_INDENT}# Добавьте шаги, например: Допустим открыт \"https://site.com\"")
    return "\n".join(lines)
