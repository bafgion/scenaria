"""Locator, OTP, and step helper utilities for playback (T8a)."""

from __future__ import annotations

import re
from collections.abc import Callable

from playwright.sync_api import Page

from app.play_log import step_log_target
from app.player_highlight import remove_highlight
from app.selector_resolve import resolve_hover_locator

LogCallback = Callable[[str], None]

_INTERACTIVE_ACTIONS = frozenset(
    {
        "click",
        "hover",
        "fill",
        "fill_generated",
        "select",
        "double_click",
        "clear",
        "check",
        "uncheck",
        "upload",
        "scroll_to",
        "press",
        "draw_signature",
    }
)
_ASSERT_ACTIONS = frozenset({"assert_visible", "assert_text", "assert_url", "assert_hidden"})
_WAIT_ACTIONS = frozenset({"wait", "wait_for", "wait_for_hidden"})
_NAV_ACTIONS = frozenset({"reload", "go_back"})
_SESSION_ACTIONS = frozenset({"close_browser"})
_PROMPT_ACTIONS = frozenset({"prompt_email_code"})
_EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
_EMAIL_FIELD_SELECTORS = (
    'input[type="email"]',
    'input[name*="email" i]',
    'input[id*="email" i]',
    'input[autocomplete="email"]',
    'input[placeholder*="@" i]',
)
_PAGE_EMAIL_PATTERNS = (
    re.compile(r"по адресу\s+[\"«]?([^\s\"«»,;<>]+@[^\s\"»»,;<>]+)", re.IGNORECASE),
    re.compile(r"код подтверждения[^\n@]{0,80}\b([^\s@]+@[^\s@]+)", re.IGNORECASE),
    re.compile(r"sent (?:a )?(?:verification )?code to\s+([^\s,<>]+@[^\s,<>]+)", re.IGNORECASE),
)
_INPUT_EVENTS_JS = """(el) => {
  el.dispatchEvent(new Event('input', { bubbles: true }));
  el.dispatchEvent(new Event('change', { bubbles: true }));
}"""
OTP_KEYBOARD_DELAY_MS = 80


def _looks_like_email(value: str) -> bool:
    return bool(_EMAIL_RE.match(str(value or "").strip()))


def _selector_suggests_email(selector: str) -> bool:
    lowered = str(selector or "").lower()
    return any(token in lowered for token in ("email", "e-mail", "почт", "mail"))


def _normalize_verification_code(code: str) -> str:
    return re.sub(r"[\s\-–—]", "", str(code or "").strip())


def _extract_email_from_page_text(page: Page) -> str:
    try:
        text = page.locator("body").inner_text(timeout=3000)
    except Exception:  # noqa: BLE001
        return ""
    if not isinstance(text, str):
        return ""
    for pattern in _PAGE_EMAIL_PATTERNS:
        match = pattern.search(text)
        if not match:
            continue
        candidate = match.group(1).strip().rstrip(".,;:!?»\"")
        if _looks_like_email(candidate):
            return candidate
    return ""


def _segmented_input_values(locator, field_count: int) -> str:
    values: list[str] = []
    for index in range(field_count):
        try:
            values.append(str(locator.nth(index).input_value(timeout=2000) or ""))
        except Exception:  # noqa: BLE001
            values.append("")
    return "".join(values)


def _otp_fields_visible(locator, *, min_count: int = 1) -> bool:
    try:
        count = locator.count()
    except Exception:  # noqa: BLE001
        return False
    if count < min_count:
        return False
    try:
        return locator.first.is_visible(timeout=500)
    except Exception:  # noqa: BLE001
        return False


def _otp_auto_submitted(locator, field_count: int, expected: str) -> bool:
    """OTP form often auto-advances after the last digit — fields disappear from DOM."""
    if not expected:
        return False
    try:
        count = locator.count()
    except Exception:  # noqa: BLE001
        return False
    if count == 0:
        return True
    filled = _segmented_input_values(locator, min(field_count, count))
    if filled == expected:
        return True
    try:
        for index in range(min(count, field_count)):
            if locator.nth(index).is_visible(timeout=300):
                return False
    except Exception:  # noqa: BLE001
        return True
    return True


def _fill_segmented_cells(locator, value: str) -> None:
    for index, char in enumerate(value):
        cell = locator.nth(index)
        cell.click(timeout=15000)
        cell.fill(char, timeout=15000)
        cell.evaluate(_INPUT_EVENTS_JS)


def _type_segmented_code_batch(page: Page, locator, value: str) -> None:
    first = locator.nth(0)
    first.click(timeout=15000)
    page.wait_for_timeout(120)
    page.keyboard.type(value, delay=OTP_KEYBOARD_DELAY_MS)


def _type_segmented_code_per_char(page: Page, locator, value: str) -> None:
    for index, char in enumerate(value):
        cell = locator.nth(index)
        cell.click(timeout=15000)
        page.wait_for_timeout(60)
        page.keyboard.type(char, delay=OTP_KEYBOARD_DELAY_MS)
        page.wait_for_timeout(40)


def _fill_verification_code_segmented(
    page: Page,
    locator,
    value: str,
    field_count: int,
    *,
    input_method: str | None = None,
) -> str:
    method = (input_method or "auto").lower()

    def _result_if_done(stage: str) -> str | None:
        if _segmented_input_values(locator, field_count) == value:
            return stage
        if _otp_auto_submitted(locator, field_count, value):
            return f"{stage}-submit"
        return None

    if method == "fill":
        _fill_segmented_cells(locator, value)
        result = _result_if_done(f"segmented-fill:{field_count}")
        if result:
            return result
        raise RuntimeError("Не удалось заполнить поля кода")

    _type_segmented_code_batch(page, locator, value)
    result = _result_if_done(f"segmented-keyboard:{field_count}")
    if result:
        return result

    if not _otp_fields_visible(locator):
        return f"segmented-keyboard:{field_count}-submit"

    try:
        _type_segmented_code_per_char(page, locator, value)
    except Exception:
        if _otp_auto_submitted(locator, field_count, value):
            return f"segmented-keyboard-char:{field_count}-submit"
        raise
    result = _result_if_done(f"segmented-keyboard-char:{field_count}")
    if result:
        return result

    if method == "keyboard":
        if _otp_auto_submitted(locator, field_count, value):
            return f"segmented-keyboard:{field_count}-submit"
        raise RuntimeError("Не удалось ввести код с клавиатуры")

    if not _otp_fields_visible(locator):
        return f"segmented-keyboard:{field_count}-submit"

    try:
        _fill_segmented_cells(locator, value)
    except Exception:
        if _otp_auto_submitted(locator, field_count, value):
            return f"segmented-fill:{field_count}-submit"
        raise
    result = _result_if_done(f"segmented-fill:{field_count}")
    if result:
        return result
    if _otp_auto_submitted(locator, field_count, value):
        return f"segmented-fill:{field_count}-submit"
    raise RuntimeError("Не удалось ввести код в поля")


def fill_verification_code(
    page: Page,
    selector: str,
    code: str,
    *,
    digits: int | None = None,
    input_method: str | None = None,
    allow_advancing: bool = False,
) -> str:
    """Fill OTP into one field or several segmented cells. Returns fill mode label."""
    value = _normalize_verification_code(code)
    if not value:
        raise ValueError("Код не введён")

    locator = page.locator(selector)
    count = locator.count()
    if count == 0:
        if allow_advancing:
            return "already-submitted"
        raise RuntimeError(f"Поля для кода не найдены → {selector}")

    segmented = bool(digits and digits > 1) or count > 1
    if segmented:
        field_count = int(digits) if digits and digits > 1 else count
        if field_count < 2:
            field_count = count
        if count < field_count:
            raise RuntimeError(f"Найдено полей: {count}, нужно {field_count} → {selector}")
        if len(value) > field_count:
            value = value[:field_count]
        return _fill_verification_code_segmented(
            page,
            locator,
            value,
            field_count,
            input_method=input_method,
        )

    method = (input_method or "fill").lower()
    target = locator.first
    target.click(timeout=15000)
    if method == "keyboard":
        page.keyboard.type(value, delay=OTP_KEYBOARD_DELAY_MS)
        return "single-keyboard"

    target.fill(value, timeout=15000)
    target.evaluate(_INPUT_EVENTS_JS)
    if method == "auto":
        try:
            current = str(target.input_value(timeout=2000) or "")
        except Exception:  # noqa: BLE001
            current = ""
        if current != value:
            target.click(timeout=15000)
            page.keyboard.type(value, delay=OTP_KEYBOARD_DELAY_MS)
            return "single-keyboard"
    return "single"


def _locator_issues_for_code_input(
    page: Page,
    selector: str,
    *,
    digits: int | None = None,
) -> list[str]:
    try:
        locator = page.locator(selector)
        count = locator.count()
    except Exception as exc:  # noqa: BLE001
        return [f"некорректный селектор: {exc}"]

    if count == 0:
        return ["элемент не найден"]

    field_count = int(digits) if digits and digits > 1 else count
    if digits and digits > 1 and count < digits:
        return [f"найдено полей: {count}, нужно {digits}"]

    checks = field_count if count > 1 else 1
    for index in range(checks):
        target = locator.nth(index) if count > 1 else locator.first
        try:
            if not target.is_visible(timeout=1500):
                return [f"поле {index + 1} скрыто"]
            if not target.is_enabled(timeout=500):
                return [f"поле {index + 1} недоступно"]
        except Exception:  # noqa: BLE001
            return [f"поле {index + 1} не видно"]
    return []

def _locator_issues(page: Page, selector: str, *, require_enabled: bool = False) -> list[str]:
    issues: list[str] = []
    try:
        locator = page.locator(selector)
        count = locator.count()
    except Exception as exc:  # noqa: BLE001
        return [f"некорректный селектор: {exc}"]

    if count == 0:
        issues.append("элемент не найден")
        return issues
    if count > 1:
        issues.append(f"найдено элементов: {count} (ожидался один)")

    target = locator.first
    try:
        if not target.is_visible(timeout=1500):
            issues.append("элемент скрыт")
    except Exception:  # noqa: BLE001
        issues.append("элемент не виден")

    if require_enabled:
        try:
            if not target.is_enabled(timeout=500):
                issues.append("элемент недоступен (disabled)")
        except Exception:  # noqa: BLE001
            issues.append("не удалось проверить доступность")

    return issues


def _locator_hidden_issues(page: Page, selector: str) -> list[str]:
    issues: list[str] = []
    try:
        locator = page.locator(selector)
        count = locator.count()
    except Exception as exc:  # noqa: BLE001
        return [f"некорректный селектор: {exc}"]

    if count == 0:
        return issues

    try:
        if locator.first.is_visible(timeout=1500):
            issues.append("элемент всё ещё виден")
    except Exception:  # noqa: BLE001
        pass

    return issues
def _extract_text_fragments(selector: str) -> list[str]:
    fragments: list[str] = []
    for pattern in (
        r':has-text\("([^"]+)"\)',
        r":has-text\('([^']+)'\)",
        r'\[name="([^"]+)"\]',
        r"\[name='([^']+)'\]",
    ):
        for match in re.findall(pattern, selector):
            text = match.strip()
            if text and text not in fragments:
                fragments.append(text)
    return fragments


def _hover_element(page: Page, selector: str, on_log: LogCallback, index: int, *, label: str = "Наведение") -> bool:
    if not selector:
        return False
    try:
        locator = resolve_hover_locator(page, selector)
        locator.scroll_into_view_if_needed(timeout=3000)
        locator.hover(timeout=5000, force=True)
        page.wait_for_timeout(400)
        on_log(f"{index}. {label} → {selector}")
        return True
    except Exception:
        return False


def _prepare_click_target(page: Page, step: dict, on_log: LogCallback, index: int) -> None:
    hover_selector = step.get("hoverSelector")
    if not hover_selector:
        return
    target = step_log_target(step, str(hover_selector))
    if not _hover_element(page, hover_selector, on_log, index, label="Наведение перед кликом"):
        on_log(f"{index}. Не удалось навести на «{target}»")


def _reveal_hover_menu(page: Page, selector: str, on_log: LogCallback, index: int) -> bool:
    targets: list[str] = []
    if " >> " in selector:
        targets.append(selector.split(" >> ", 1)[0].strip())
    for text in _extract_text_fragments(selector):
        targets.append(f'div:has-text("{text}")')
        targets.append(f'a:has-text("{text}")')

    for target in targets:
        try:
            locator = resolve_hover_locator(page, target)
            locator.scroll_into_view_if_needed(timeout=3000)
            locator.hover(timeout=2500, force=True)
            page.wait_for_timeout(400)
            return True
        except Exception:
            continue
    return False
def _fill_locator(page: Page, selector: str, value: str) -> None:
    locator = page.locator(selector).first
    locator.click(timeout=15000)
    locator.fill(value, timeout=15000)
    locator.evaluate(_INPUT_EVENTS_JS)
    remove_highlight(page)

