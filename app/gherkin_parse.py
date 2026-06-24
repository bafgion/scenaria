"""Parse Russian Gherkin step lines into recorder step dicts."""

from __future__ import annotations

import re
from typing import Any

from app.gherkin_ru import (
    _CONTEXT_LINE_RE,
    _EXAMPLES_HEADER_RE,
    _FEATURE_LINE_RE,
    _KEYWORD_RE,
    _LEGACY_HAS_TEXT_UNESCAPED,
    _OUTLINE_HEADER_RE,
    _SCENARIO_LINE_RE,
    _STEP_HEADER_RE,
    _TAG_LINE_RE,
    STEP_INDENT,
    GherkinParseError,
    _unquote,
    is_gherkin_step_line,
    leading_indent,
)
from app.run_variables import (
    GENERATOR_GHERKIN_PHRASES,
    normalize_generator_name,
)


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


def _parse_step_body(line_no: int, line: str) -> dict[str, Any]:
    """Parse one step line into a step dictionary."""
    keyword_match = _KEYWORD_RE.match(line)
    if not keyword_match:
        raise GherkinParseError(line_no, line, "Не удалось разобрать шаг")
    body = keyword_match.group(1).strip()


    remember_text_match = re.fullmatch(
        r'запоминаю\s+текст\s+"((?:\\.|[^"])*)"\s+как\s+"((?:\\.|[^"])*)"',
        body,
        flags=re.IGNORECASE,
    )
    if remember_text_match:
        return {
            "action": "remember_text",
            "value": _unquote(remember_text_match.group(1)),
            "variable": _unquote(remember_text_match.group(2)),
        }

    remember_field_match = re.fullmatch(
        r'запоминаю\s+значение\s+поля\s+"((?:\\.|[^"])*)"\s+как\s+"((?:\\.|[^"])*)"',
        body,
        flags=re.IGNORECASE,
    )
    if remember_field_match:
        return {
            "action": "remember_field",
            "selector": _unquote(remember_field_match.group(1)),
            "variable": _unquote(remember_field_match.group(2)),
        }

    remember_url_match = re.fullmatch(
        r'запоминаю\s+url\s+как\s+"((?:\\.|[^"])*)"',
        body,
        flags=re.IGNORECASE,
    )
    if remember_url_match:
        return {
            "action": "remember_url",
            "variable": _unquote(remember_url_match.group(1)),
        }

    download_click_match = re.fullmatch(
        r'скачиваю\s+по\s+клику\s+на\s+"((?:\\.|[^"])*)"',
        body,
        flags=re.IGNORECASE,
    )
    if download_click_match:
        return {
            "action": "download_click",
            "selector": _unquote(download_click_match.group(1)),
        }

    assert_download_match = re.fullmatch(
        r'проверяю\s+что\s+скачанный\s+файл\s+содержит\s+"((?:\\.|[^"])*)"',
        body,
        flags=re.IGNORECASE,
    )
    if assert_download_match:
        return {
            "action": "assert_download_contains",
            "value": _unquote(assert_download_match.group(1)),
        }

    goto_match = re.fullmatch(r'открыт[а]?\s+"((?:\\.|[^"])*)"', body, flags=re.IGNORECASE)
    if goto_match:
        return {"action": "goto", "url": _unquote(goto_match.group(1))}

    double_click_match = re.fullmatch(
        r'дважды\s+нажимаю\s+"((?:\\.|[^"])*)"',
        body,
        flags=re.IGNORECASE,
    )
    if double_click_match:
        return {"action": "double_click", "selector": _unquote(double_click_match.group(1))}

    press_in_match = re.fullmatch(
        r'нажимаю\s+клавишу\s+"((?:\\.|[^"])*)"\s+в\s+"((?:\\.|[^"])*)"',
        body,
        flags=re.IGNORECASE,
    )
    if press_in_match:
        return {
                "action": "press",
                "key": _unquote(press_in_match.group(1)),
                "selector": _unquote(press_in_match.group(2)),
            }

    press_match = re.fullmatch(
        r'нажимаю\s+клавишу\s+"((?:\\.|[^"])*)"',
        body,
        flags=re.IGNORECASE,
    )
    if press_match:
        return {"action": "press", "key": _unquote(press_match.group(1))}

    click_match = re.fullmatch(r'нажимаю\s+"((?:\\.|[^"])*)"', body, flags=re.IGNORECASE)
    if click_match:
        return {"action": "click", "selector": _unquote(click_match.group(1))}

    hover_match = re.fullmatch(r'навожу\s+"((?:\\.|[^"])*)"', body, flags=re.IGNORECASE)
    if hover_match:
        return {"action": "hover", "selector": _unquote(hover_match.group(1))}

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
        return step

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
        return step

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
        return step

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
        return step

    fill_generated_step = _parse_generated_fill(body)
    if fill_generated_step is not None:
        return fill_generated_step

    fill_match = re.fullmatch(
        r'ввожу\s+"((?:\\.|[^"])*)"\s+в\s+"((?:\\.|[^"])*)"',
        body,
        flags=re.IGNORECASE,
    )
    if fill_match:
        return {
                "action": "fill",
                "value": _unquote(fill_match.group(1)),
                "selector": _unquote(fill_match.group(2)),
            }

    select_match = re.fullmatch(
        r'выбираю\s+"((?:\\.|[^"])*)"\s+в\s+"((?:\\.|[^"])*)"',
        body,
        flags=re.IGNORECASE,
    )
    if select_match:
        return {
                "action": "select",
                "value": _unquote(select_match.group(1)),
                "selector": _unquote(select_match.group(2)),
            }

    upload_match = re.fullmatch(
        r'загружаю\s+файл\s+"((?:\\.|[^"])*)"\s+в\s+"((?:\\.|[^"])*)"',
        body,
        flags=re.IGNORECASE,
    )
    if upload_match:
        return {
                "action": "upload",
                "path": _unquote(upload_match.group(1)),
                "selector": _unquote(upload_match.group(2)),
            }

    clear_match = re.fullmatch(r'очищаю\s+"((?:\\.|[^"])*)"', body, flags=re.IGNORECASE)
    if clear_match:
        return {"action": "clear", "selector": _unquote(clear_match.group(1))}

    sign_match = re.fullmatch(
        r'рисую\s+подпись\s+в\s+"((?:\\.|[^"])*)"',
        body,
        flags=re.IGNORECASE,
    )
    if sign_match:
        return {"action": "draw_signature", "selector": _unquote(sign_match.group(1))}

    uncheck_match = re.fullmatch(
        r'снимаю\s+отметку\s+с\s+"((?:\\.|[^"])*)"',
        body,
        flags=re.IGNORECASE,
    )
    if uncheck_match:
        return {"action": "uncheck", "selector": _unquote(uncheck_match.group(1))}

    check_match = re.fullmatch(r'отмечаю\s+"((?:\\.|[^"])*)"', body, flags=re.IGNORECASE)
    if check_match:
        return {"action": "check", "selector": _unquote(check_match.group(1))}

    hidden_match = re.fullmatch(r'не\s+вижу\s+"((?:\\.|[^"])*)"', body, flags=re.IGNORECASE)
    if hidden_match:
        return {"action": "assert_hidden", "selector": _unquote(hidden_match.group(1))}

    visible_match = re.fullmatch(r'вижу\s+"((?:\\.|[^"])*)"', body, flags=re.IGNORECASE)
    if visible_match:
        return {"action": "assert_visible", "selector": _unquote(visible_match.group(1))}

    text_match = re.fullmatch(
        r'проверяю\s+текст\s+"((?:\\.|[^"])*)"\s+в\s+"((?:\\.|[^"])*)"',
        body,
        flags=re.IGNORECASE,
    )
    if text_match:
        return {
                "action": "assert_text",
                "value": _unquote(text_match.group(1)),
                "selector": _unquote(text_match.group(2)),
            }

    url_match = re.fullmatch(r'проверяю\s+url\s+"((?:\\.|[^"])*)"', body, flags=re.IGNORECASE)
    if url_match:
        return {"action": "assert_url", "url": _unquote(url_match.group(1))}

    scroll_match = re.fullmatch(
        r'скроллю\s+к\s+"((?:\\.|[^"])*)"',
        body,
        flags=re.IGNORECASE,
    )
    if scroll_match:
        return {"action": "scroll_to", "selector": _unquote(scroll_match.group(1))}

    if re.fullmatch(r"обновляю\s+страницу", body, flags=re.IGNORECASE):
        return {"action": "reload"}

    if re.fullmatch(r"возвращаюсь\s+назад", body, flags=re.IGNORECASE):
        return {"action": "go_back"}

    if re.fullmatch(r"закрываю\s+браузер", body, flags=re.IGNORECASE):
        return {"action": "close_browser"}

    switch_tab_index_match = re.fullmatch(
        r"переключаюсь\s+на\s+вкладку\s+(\d+)",
        body,
        flags=re.IGNORECASE,
    )
    if switch_tab_index_match:
        user_index = int(switch_tab_index_match.group(1))
        if user_index < 1:
            raise GherkinParseError(
                line_no,
                line,
                "Номер вкладки должен быть не меньше 1",
            )
        return {
            "action": "switch_tab",
            "mode": "index",
            "value": str(user_index - 1),
        }

    switch_tab_title_match = re.fullmatch(
        r'переключаюсь\s+на\s+вкладку\s+"((?:\\.|[^"])*)"',
        body,
        flags=re.IGNORECASE,
    )
    if switch_tab_title_match:
        return {
            "action": "switch_tab",
            "mode": "title",
            "value": _unquote(switch_tab_title_match.group(1)),
        }

    switch_tab_url_match = re.fullmatch(
        r'переключаюсь\s+на\s+вкладку\s+с\s+url\s+"((?:\\.|[^"])*)"',
        body,
        flags=re.IGNORECASE,
    )
    if switch_tab_url_match:
        return {
            "action": "switch_tab",
            "mode": "url",
            "value": _unquote(switch_tab_url_match.group(1)),
        }

    if re.fullmatch(r"переключаюсь\s+на\s+первую\s+вкладку", body, flags=re.IGNORECASE):
        return {"action": "switch_tab", "mode": "first"}

    if re.fullmatch(r"переключаюсь\s+на\s+новую\s+вкладку", body, flags=re.IGNORECASE):
        return {"action": "switch_tab", "mode": "new"}

    if re.fullmatch(r"закрываю\s+текущую\s+вкладку", body, flags=re.IGNORECASE):
        return {"action": "close_tab"}

    assert_tab_count_match = re.fullmatch(
        r"проверяю\s+что\s+открыто\s+(\d+)\s+вкладк\w*",
        body,
        flags=re.IGNORECASE,
    )
    if assert_tab_count_match:
        return {"action": "assert_tab_count", "count": int(assert_tab_count_match.group(1))}

    wait_hidden_match = re.fullmatch(
        r'жду\s+исчезновения\s+"((?:\\.|[^"])*)"',
        body,
        flags=re.IGNORECASE,
    )
    if wait_hidden_match:
        return {"action": "wait_for_hidden", "selector": _unquote(wait_hidden_match.group(1))}

    wait_sec_match = re.fullmatch(
        r"жду\s+([\d.,]+)\s*(?:сек|секунд|сек|с)\b",
        body,
        flags=re.IGNORECASE,
    )
    if wait_sec_match:
        seconds = float(wait_sec_match.group(1).replace(",", "."))
        return {"action": "wait", "ms": max(0, int(seconds * 1000))}

    wait_ms_match = re.fullmatch(r"жду\s+(\d+)\s*(?:мс|мсек)\b", body, flags=re.IGNORECASE)
    if wait_ms_match:
        return {"action": "wait", "ms": max(0, int(wait_ms_match.group(1)))}

    wait_for_match = re.fullmatch(
        r'жду\s+появления\s+"((?:\\.|[^"])*)"',
        body,
        flags=re.IGNORECASE,
    )
    if wait_for_match:
        return {"action": "wait_for", "selector": _unquote(wait_for_match.group(1))}

    raise GherkinParseError(
        line_no,
        line,
        "Неизвестный шаг — откройте Ctrl+Space для списка поддерживаемых шагов",
    )

def _collect_step_lines(text: str) -> list[tuple[int, str]]:
    """Collect step lines with source line numbers, skipping headers and outline tables."""
    collected: list[tuple[int, str]] = []
    skip_outline = False
    in_context = False
    for line_no, raw in enumerate(text.splitlines(), start=1):
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if _TAG_LINE_RE.match(stripped):
            in_context = False
            continue
        if _FEATURE_LINE_RE.match(stripped) or _SCENARIO_LINE_RE.match(stripped):
            in_context = False
            continue
        if _CONTEXT_LINE_RE.match(stripped):
            in_context = True
            continue
        if in_context:
            continue
        if _OUTLINE_HEADER_RE.match(stripped):
            skip_outline = True
            continue
        if skip_outline:
            if _EXAMPLES_HEADER_RE.match(stripped):
                continue
            if stripped.startswith("|") or not stripped:
                continue
            skip_outline = False
        if not is_gherkin_step_line(raw):
            continue
        collected.append((line_no, raw))
    return collected


def _parse_indented_steps(
    items: list[tuple[int, str]],
    *,
    start: int = 0,
    base_level: int = 1,
) -> tuple[list[dict[str, Any]], int]:
    from app.gherkin_blocks import (
        line_indent_level,
        parse_for_each_header,
        parse_if_header,
        parse_repeat_header,
        parse_while_header,
    )

    steps: list[dict[str, Any]] = []
    index = start
    while index < len(items):
        line_no, raw = items[index]
        level = line_indent_level(raw)
        if level < 0:
            index += 1
            continue
        if level <= 0:
            level = base_level
        if level < base_level:
            break
        if level > base_level:
            indent = leading_indent(raw)
            if "\t" not in indent and indent.strip() == "":
                raise GherkinParseError(
                    line_no,
                    raw.strip(),
                    "Отступ пробелами вместо таба — используйте таб или Рефакторинг → Нормализовать отступы",
                )
            raise GherkinParseError(line_no, raw.strip(), "Неожиданный отступ")

        line = raw.strip()
        keyword_match = _KEYWORD_RE.match(line)
        body = keyword_match.group(1).strip() if keyword_match else line

        if_header = parse_if_header(body, line_no=line_no, line_text=line)
        if if_header is not None:
            nested, next_index = _parse_indented_steps(
                items, start=index + 1, base_level=base_level + 1
            )
            steps.append({"action": "if", "condition": if_header, "steps": nested})
            index = next_index
            continue

        while_header = parse_while_header(body, line_no=line_no, line_text=line)
        if while_header is not None:
            nested, next_index = _parse_indented_steps(
                items, start=index + 1, base_level=base_level + 1
            )
            steps.append({"action": "while", "condition": while_header, "steps": nested})
            index = next_index
            continue

        for_each_header = parse_for_each_header(body)
        if for_each_header is not None:
            nested, next_index = _parse_indented_steps(
                items, start=index + 1, base_level=base_level + 1
            )
            steps.append(
                {
                    "action": "for_each",
                    "selector": for_each_header["selector"],
                    "variable": for_each_header["variable"],
                    "steps": nested,
                }
            )
            index = next_index
            continue

        repeat_count = parse_repeat_header(body)
        if repeat_count is not None:
            nested, next_index = _parse_indented_steps(
                items, start=index + 1, base_level=base_level + 1
            )
            steps.append({"action": "repeat", "count": repeat_count, "steps": nested})
            index = next_index
            continue

        steps.append(_parse_step_body(line_no, line))
        index += 1
    return steps, index


def _coalesce_mixed_step_indents(items: list[tuple[int, str]]) -> list[tuple[int, str]]:
    """If the scenario uses tab-indented steps, normalize stray 2/4-space indents to one tab."""
    if not items:
        return items
    if not any(leading_indent(raw).startswith("\t") for _, raw in items):
        return items
    coalesced: list[tuple[int, str]] = []
    for line_no, raw in items:
        indent = leading_indent(raw)
        if "\t" not in indent and indent.strip() == "" and len(indent) in (2, 4):
            raw = f"{STEP_INDENT}{raw.lstrip()}"
        coalesced.append((line_no, raw))
    return coalesced


def coalesce_mixed_step_indents_in_text(text: str) -> str:
    """Rewrite stray 2/4-space step indents to tabs when the file already uses tab indents."""
    if not text:
        return text
    lines = text.replace("\r\n", "\n").splitlines()
    if not any(is_gherkin_step_line(raw) and leading_indent(raw).startswith("\t") for raw in lines):
        return text
    changed = False
    result: list[str] = []
    for raw in lines:
        if not is_gherkin_step_line(raw):
            result.append(raw)
            continue
        indent = leading_indent(raw)
        if "\t" not in indent and indent.strip() == "" and len(indent) in (2, 4):
            raw = f"{STEP_INDENT}{raw.lstrip()}"
            changed = True
        result.append(raw)
    if not changed:
        return text
    suffix = "\n" if text.endswith("\n") else ""
    payload = "\n".join(result)
    if suffix and payload:
        payload += "\n"
    return payload


def _parse_gherkin_to_steps(text: str) -> list[dict[str, Any]]:
    """Parse already-normalized Gherkin-like text into step dictionaries."""
    items = _coalesce_mixed_step_indents(_collect_step_lines(text))
    steps, _ = _parse_indented_steps(items)
    return steps


def normalize_gherkin_text(text: str) -> str:
    """Normalize editor/file text before parsing."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    for fancy, plain in (
        ("\u201c", '"'),
        ("\u201d", '"'),
        ("\u2018", "'"),
        ("\u2019", "'"),
    ):
        text = text.replace(fancy, plain)
    for ch in "\u200b\u2060\ufffc\ufeff":
        text = text.replace(ch, "")
    return text


def normalize_legacy_has_text_escapes(text: str) -> str:
    """Escape inner quotes in legacy ``:has-text("…")`` selectors inside step strings."""
    if ':has-text("' not in text:
        return text
    lines = text.splitlines()
    changed = False
    for index, line in enumerate(lines):
        if ':has-text("' not in line:
            continue
        fixed = _LEGACY_HAS_TEXT_UNESCAPED.sub(
            lambda match: f':has-text(\\"{match.group(1)}\\")',
            line,
        )
        if fixed != line:
            lines[index] = fixed
            changed = True
    if not changed:
        return text
    suffix = "\n" if text.endswith("\n") else ""
    return "\n".join(lines) + suffix


def try_repair_step_quote_on_line(text: str, exc: GherkinParseError) -> str | None:
    """If a step line lost a closing quote, append it."""
    lines = text.splitlines()
    if exc.line_no < 1 or exc.line_no > len(lines):
        return None
    raw_line = lines[exc.line_no - 1]
    repaired_line = _repair_unclosed_quote_line(raw_line)
    if repaired_line is None:
        return None
    lines[exc.line_no - 1] = repaired_line
    suffix = "\n" if text.endswith("\n") else ""
    return "\n".join(lines) + suffix


def try_repair_terminal_step_quote(text: str, exc: GherkinParseError) -> str | None:
    """Backward-compatible alias — repairs the failing line, not only the last one."""
    return try_repair_step_quote_on_line(text, exc)


def _repair_unclosed_quote_line(raw_line: str) -> str | None:
    stripped = raw_line.strip()
    if not stripped or stripped.startswith("#"):
        return None
    if _STEP_HEADER_RE.match(stripped) or _TAG_LINE_RE.match(stripped):
        return None
    if stripped.endswith('"'):
        return None
    if stripped.count('"') % 2 == 0:
        return None
    return raw_line + '"'


def repair_unclosed_step_quotes(text: str) -> str:
    """Repair legacy step lines that lost the closing double quote."""
    lines = text.splitlines()
    changed = False
    for index, raw_line in enumerate(lines):
        repaired = _repair_unclosed_quote_line(raw_line)
        if repaired is None:
            continue
        lines[index] = repaired
        changed = True
    if not changed:
        return text
    suffix = "\n" if text.endswith("\n") else ""
    return "\n".join(lines) + suffix


def parse_gherkin_steps(text: str) -> tuple[list[dict[str, Any]], str]:
    """Parse steps and return canonical text (normalized or repaired)."""
    normalized = repair_unclosed_step_quotes(
        normalize_legacy_has_text_escapes(normalize_gherkin_text(text))
    )
    current = normalized
    while True:
        try:
            steps = _parse_gherkin_to_steps(current)
            canonical = coalesce_mixed_step_indents_in_text(current)
            return steps, canonical
        except GherkinParseError as exc:
            repaired = try_repair_step_quote_on_line(current, exc)
            if repaired is None or repaired == current:
                raise
            current = repaired


def gherkin_to_steps(text: str) -> list[dict[str, Any]]:
    """Parse Russian Gherkin-like text into step dictionaries."""
    steps, _ = parse_gherkin_steps(text)
    return steps

