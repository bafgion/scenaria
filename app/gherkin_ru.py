"""Russian Gherkin-like parser/serializer for recorder steps."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Literal

from app.run_variables import GENERATOR_GHERKIN_PHRASES, generator_gherkin_phrase, normalize_generator_name

_KEYWORD_RE = re.compile(r"^(?:(?:Допустим|Когда|Тогда|И|Но)\s+)?(.+)$", re.IGNORECASE)
_STEP_HEADER_RE = re.compile(r"^(?:функционал|сценарий|функция)\s*:", re.IGNORECASE)
_SCENARIO_LINE_RE = re.compile(r"^сценарий\s*:\s*(.*)$", re.IGNORECASE)
_FEATURE_LINE_RE = re.compile(r"^функционал\s*:\s*(.*)$", re.IGNORECASE)
_TAG_LINE_RE = re.compile(r"^@(\S+)$")
_OUTLINE_HEADER_RE = re.compile(r"^структура\s+сценария\s*:", re.IGNORECASE)
_EXAMPLES_HEADER_RE = re.compile(r"^примеры\s*:", re.IGNORECASE)
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
    return bool(re.match(r"^(?:Допустим|Когда|Тогда|И|Но)\s+", stripped, flags=re.IGNORECASE))


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
    pending: list[str] = []
    phase: Literal["header", "before_steps", "steps", "after"] = "header"
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
    )


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
    for line_no, raw in enumerate(text.splitlines(), start=1):
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if _TAG_LINE_RE.match(stripped):
            continue
        if _FEATURE_LINE_RE.match(stripped) or _SCENARIO_LINE_RE.match(stripped):
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


def _parse_gherkin_to_steps(text: str) -> list[dict[str, Any]]:
    """Parse already-normalized Gherkin-like text into step dictionaries."""
    items = _collect_step_lines(text)
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


def try_repair_terminal_step_quote(text: str, exc: GherkinParseError) -> str | None:
    """If the last step line lost a closing quote, append it."""
    lines = text.splitlines()
    if not lines or exc.line_no != len(lines):
        return None
    raw_line = lines[exc.line_no - 1]
    stripped = raw_line.strip()
    if not stripped or stripped.startswith("#"):
        return None
    if _STEP_HEADER_RE.match(stripped) or _TAG_LINE_RE.match(stripped):
        return None
    if stripped.endswith('"'):
        return None
    if stripped.count('"') % 2 == 0:
        return None
    lines[exc.line_no - 1] = raw_line + '"'
    suffix = "\n" if text.endswith("\n") else ""
    return "\n".join(lines) + suffix


def parse_gherkin_steps(text: str) -> tuple[list[dict[str, Any]], str]:
    """Parse steps and return canonical text (normalized or repaired)."""
    normalized = normalize_gherkin_text(text)
    try:
        return _parse_gherkin_to_steps(normalized), normalized
    except GherkinParseError as exc:
        repaired = try_repair_terminal_step_quote(normalized, exc)
        if repaired is not None:
            return _parse_gherkin_to_steps(repaired), repaired
        raise


def gherkin_to_steps(text: str) -> list[dict[str, Any]]:
    """Parse Russian Gherkin-like text into step dictionaries."""
    steps, _ = parse_gherkin_steps(text)
    return steps

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
