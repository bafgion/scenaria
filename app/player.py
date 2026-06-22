"""Replay recorded scenarios."""

from __future__ import annotations

import queue
import threading
import time
from datetime import datetime
import re
from pathlib import Path
from typing import Any, Callable, TypedDict

from playwright.sync_api import Page, sync_playwright

from app.browser_config import browser_context_options, launch_browser, load_browser_engine
from app.download_helpers import file_contains_substring, save_playwright_download
from app.run_variables import RunContext, normalize_generator_name
from app.paths import configure_playwright_browsers, screenshots_dir, traces_dir
from app.play_log import format_click_log, format_fill_generated_log, format_fill_log, step_log_target
from app.playwright_lifecycle import release_playwright_session
from app.selector_picker import SelectorPickerSession
from app.selector_resolve import resolve_chained_locator, resolve_hover_locator
from app.signature_draw import draw_signature_on_canvas
from app.steps import NAV_TIMEOUT_MS, NAV_WAIT_UNTIL, normalize_steps, urls_match

LogCallback = Callable[[str], None]
DoneCallback = Callable[[bool, str], None]
StepCallback = Callable[[int, int, dict], None]
CloseBrowserCallback = Callable[[], None]
BetweenStepsCallback = Callable[["Page"], None]
PickerCallback = Callable[[str | None], None]
ErrorCallback = Callable[[Exception], None]

_PICK_CANCEL = object()

HIGHLIGHT_SCRIPT = """
(selector) => {
  const prev = document.getElementById('__shopRecorderHighlight');
  if (prev) prev.remove();
  const el = document.querySelector(selector);
  if (!el) return false;
  const rect = el.getBoundingClientRect();
  const box = document.createElement('div');
  box.id = '__shopRecorderHighlight';
  box.style.cssText = [
    'position:fixed',
    'pointer-events:none',
    'z-index:2147483646',
    `left:${rect.left}px`,
    `top:${rect.top}px`,
    `width:${rect.width}px`,
    `height:${rect.height}px`,
    'border:3px solid #ff9800',
    'background:rgba(255,152,0,0.15)',
    'box-shadow:0 0 0 2px rgba(255,152,0,0.4)',
    'border-radius:4px',
    'transition:all 0.15s ease',
  ].join(';');
  document.body.appendChild(box);
  el.scrollIntoView({ block: 'center', inline: 'center', behavior: 'smooth' });
  return true;
}
"""

REMOVE_HIGHLIGHT_SCRIPT = """
() => {
  const prev = document.getElementById('__shopRecorderHighlight');
  if (prev) prev.remove();
}
"""

HIGHLIGHT_CLEANUP_INIT_SCRIPT = """
(() => {
  if (window.__shopHighlightCleanup) return;
  window.__shopHighlightCleanup = true;
  const remove = () => {
    document.getElementById('__shopRecorderHighlight')?.remove();
  };
  window.addEventListener('popstate', remove);
  window.addEventListener('hashchange', remove);
  for (const method of ['pushState', 'replaceState']) {
    const original = history[method];
    history[method] = function(...args) {
      remove();
      return original.apply(this, args);
    };
  }
  document.addEventListener('click', (event) => {
    const link = event.target.closest('a[href]');
    if (!link) return;
    const target = (link.getAttribute('target') || '_self').toLowerCase();
    if (target === '_self' || target === '') remove();
  }, true);
})();
"""

_highlight_cleanup_contexts: set[int] = set()
_highlight_cleanup_pages: set[int] = set()


def setup_highlight_cleanup(page: Page) -> None:
    context_id = id(page.context)
    if context_id not in _highlight_cleanup_contexts:
        try:
            page.context.add_init_script(HIGHLIGHT_CLEANUP_INIT_SCRIPT)
            _highlight_cleanup_contexts.add(context_id)
        except Exception:
            pass

    page_id = id(page)
    if page_id in _highlight_cleanup_pages:
        return

    try:
        page.evaluate(HIGHLIGHT_CLEANUP_INIT_SCRIPT)
    except Exception:
        pass

    def on_nav(frame) -> None:
        if frame == page.main_frame:
            remove_highlight(page)

    page.on("framenavigated", on_nav)
    _highlight_cleanup_pages.add(page_id)


def reset_highlight_cleanup_state() -> None:
    _highlight_cleanup_contexts.clear()
    _highlight_cleanup_pages.clear()


class PlayResult(TypedDict):
    success: bool
    message: str
    executed_count: int
    total_count: int
    failed_step: int | None
    failed_step_index: int | None
    screenshot_path: str | None
    trace_path: str | None
    log_lines: list[str]
    step_results: list[dict[str, Any]]


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


def resolve_email_for_code_prompt(
    page: Page,
    step: dict,
    prior_steps: list[dict],
    run_context: RunContext | None = None,
) -> str:
    explicit = str(step.get("email", "") or "").strip()
    if explicit:
        if run_context is not None and "{{" in explicit:
            return run_context.resolve_text(explicit)
        return explicit

    if run_context is not None:
        for key in ("email", "почта", "mail"):
            value = run_context.get(key)
            if value and _looks_like_email(value):
                return value

    for prev in reversed(prior_steps):
        if prev.get("action") not in {"fill", "fill_generated"}:
            continue
        if prev.get("action") == "fill_generated" and prev.get("generator") == "email":
            if run_context is not None:
                try:
                    return run_context.generate("email")
                except ValueError:
                    pass
            continue
        value = str(prev.get("value", "") or "").strip()
        selector = str(prev.get("selector", "") or "")
        if _looks_like_email(value):
            return value
        if value and _selector_suggests_email(selector):
            return value

    page_text_email = _extract_email_from_page_text(page)
    if page_text_email:
        return page_text_email

    for selector in _EMAIL_FIELD_SELECTORS:
        try:
            locator = page.locator(selector).first
            if locator.count() == 0:
                continue
            value = str(locator.input_value(timeout=2000) or "").strip()
            if _looks_like_email(value):
                return value
        except Exception:  # noqa: BLE001
            continue

    return ""


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


def highlight_selector(page: Page, selector: str) -> bool:
    if not selector:
        return False
    try:
        return bool(page.evaluate(HIGHLIGHT_SCRIPT, selector))
    except Exception:
        return False


def _maybe_highlight(page: Page, selector: str, *, enabled: bool, pause_ms: int = 200) -> None:
    if not enabled or not selector:
        return
    if highlight_selector(page, selector):
        page.wait_for_timeout(pause_ms)


def remove_highlight(page: Page) -> None:
    try:
        page.evaluate(REMOVE_HIGHLIGHT_SCRIPT)
    except Exception:
        pass


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


def capture_failure_trace(context, scenario_name: str, step_index: int) -> str | None:
    try:
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        safe_name = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in scenario_name)[:40] or "run"
        path = traces_dir() / f"{safe_name}-step{step_index}-{stamp}.zip"
        context.tracing.stop(path=str(path))
        return str(path)
    except Exception:
        return None


def start_play_trace(context, *, scenario_name: str) -> None:
    try:
        context.tracing.start(screenshots=True, snapshots=True, sources=True, title=scenario_name)
    except Exception:
        pass


def stop_play_trace(context, *, keep: bool, scenario_name: str, step_index: int) -> str | None:
    if keep:
        return capture_failure_trace(context, scenario_name, step_index)
    try:
        context.tracing.stop()
    except Exception:
        pass
    return None


def capture_failure_screenshot(page: Page, scenario_name: str, step_index: int) -> str | None:
    try:
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        safe_name = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in scenario_name)[:40] or "run"
        path = screenshots_dir() / f"{safe_name}-step{step_index}-{stamp}.png"
        page.screenshot(path=str(path), full_page=True)
        return str(path)
    except Exception:
        return None


def validate_scenario_on_page(page: Page, scenario: dict[str, Any], on_log: LogCallback | None = None) -> list[str]:
    from app.selector_validate import validate_results_to_issues, validate_scenario_selectors

    results = validate_scenario_selectors(page, scenario, on_log=on_log)
    return validate_results_to_issues(results)


def _fill_locator(page: Page, selector: str, value: str) -> None:
    locator = page.locator(selector).first
    locator.click(timeout=15000)
    locator.fill(value, timeout=15000)
    locator.evaluate(_INPUT_EVENTS_JS)
    remove_highlight(page)


def _evaluate_condition(page: Page, condition: dict, ctx: RunContext) -> bool:
    kind = str(condition.get("type", "") or "")
    try:
        if kind == "visible":
            selector = ctx.resolve_text(str(condition.get("selector", "") or ""))
            return page.locator(selector).first.is_visible()
        if kind == "hidden":
            selector = ctx.resolve_text(str(condition.get("selector", "") or ""))
            locator = page.locator(selector).first
            return not locator.is_visible()
        if kind == "url_contains":
            needle = ctx.resolve_text(str(condition.get("value", "") or ""))
            return needle in page.url
        if kind == "page_text":
            needle = ctx.resolve_text(str(condition.get("value", "") or ""))
            return needle in page.content()
    except Exception:  # noqa: BLE001
        return False
    return False


def execute_step(
    page: Page,
    step: dict,
    index: int,
    on_log: LogCallback,
    *,
    highlight: bool = True,
    interactive: bool = True,
    prior_steps: list[dict] | None = None,
    on_close_browser: CloseBrowserCallback | None = None,
    run_context: RunContext | None = None,
) -> None:
    ctx = run_context or RunContext()
    page = ctx.current_page(page)
    action = step.get("action")

    if action == "if":
        condition = step.get("condition") or {}
        nested = list(step.get("steps") or [])
        if _evaluate_condition(page, condition, ctx):
            on_log(f"{index}. Если → выполняю блок ({len(nested)} шаг.)")
            for sub_index, sub_step in enumerate(nested, start=1):
                execute_step(
                    page,
                    sub_step,
                    index,
                    on_log,
                    highlight=highlight,
                    interactive=interactive,
                    prior_steps=prior_steps,
                    on_close_browser=on_close_browser,
                    run_context=ctx,
                )
        else:
            on_log(f"{index}. Если → пропуск блока")
        remove_highlight(page)
        return

    if action == "repeat":
        from app.settings import load_settings

        max_iterations = max(1, int(load_settings().get("max_loop_iterations", 100)))
        count = min(max(1, int(step.get("count") or 1)), max_iterations)
        nested = list(step.get("steps") or [])
        on_log(f"{index}. Повторяю {count} раз(а), {len(nested)} шаг. в теле")
        for iteration in range(1, count + 1):
            on_log(f"{index}.{iteration} итерация")
            for sub_step in nested:
                execute_step(
                    page,
                    sub_step,
                    index,
                    on_log,
                    highlight=highlight,
                    interactive=interactive,
                    prior_steps=prior_steps,
                    on_close_browser=on_close_browser,
                    run_context=ctx,
                )
        remove_highlight(page)
        return

    if action == "while":
        from app.settings import load_settings

        max_iterations = max(1, int(load_settings().get("max_loop_iterations", 100)))
        condition = step.get("condition") or {}
        nested = list(step.get("steps") or [])
        iterations = 0
        while _evaluate_condition(page, condition, ctx) and iterations < max_iterations:
            iterations += 1
            on_log(f"{index}.{iterations} Пока → тело ({len(nested)} шаг.)")
            for sub_step in nested:
                page = ctx.current_page(page)
                execute_step(
                    page,
                    sub_step,
                    index,
                    on_log,
                    highlight=highlight,
                    interactive=interactive,
                    prior_steps=prior_steps,
                    on_close_browser=on_close_browser,
                    run_context=ctx,
                )
        page = ctx.current_page(page)
        if iterations >= max_iterations and _evaluate_condition(page, condition, ctx):
            raise RuntimeError("Превышен лимит итераций цикла «пока»")
        on_log(f"{index}. Пока → завершено ({iterations} ит.)")
        remove_highlight(page)
        return

    if action == "for_each":
        selector = ctx.resolve_text(str(step.get("selector", "") or ""))
        variable = str(step.get("variable", "") or "")
        nested = list(step.get("steps") or [])
        locators = page.locator(selector).all()
        on_log(f"{index}. Для каждого «{selector}» → {len(locators)} элемент(ов)")
        for item_index, locator in enumerate(locators, start=1):
            try:
                value = (locator.inner_text(timeout=3000) or "").strip()
            except Exception:  # noqa: BLE001
                value = str(item_index)
            if not value:
                value = str(item_index)
            ctx.remember(variable, value)
            on_log(f"{index}.{item_index} «{variable}» = «{value}»")
            for sub_step in nested:
                page = ctx.current_page(page)
                execute_step(
                    page,
                    sub_step,
                    index,
                    on_log,
                    highlight=highlight,
                    interactive=interactive,
                    prior_steps=prior_steps,
                    on_close_browser=on_close_browser,
                    run_context=ctx,
                )
        page = ctx.current_page(page)
        remove_highlight(page)
        return

    if action == "switch_tab":
        from app.tab_helpers import resolve_tab_page

        mode = str(step.get("mode", "") or "")
        value = ctx.resolve_text(str(step.get("value", "") or ""))
        target = resolve_tab_page(page.context, mode=mode, value=value)
        if target is None:
            raise RuntimeError(f"Вкладка не найдена ({mode}: {value})".rstrip(": "))
        ctx.set_current_page(target)
        try:
            target.bring_to_front()
        except Exception:  # noqa: BLE001
            pass
        on_log(f"{index}. Переключение вкладки → {mode}")
        remove_highlight(target)
        return

    if action == "close_tab":
        from app.tab_helpers import open_pages

        pages = open_pages(page.context)
        if len(pages) <= 1:
            raise RuntimeError("Нельзя закрыть единственную вкладку")
        current = page
        remaining = [item for item in pages if item != current]
        current.close()
        fallback = remaining[-1] if remaining else pages[0]
        ctx.set_current_page(fallback)
        on_log(f"{index}. Закрыта текущая вкладка")
        remove_highlight(fallback)
        return

    if action == "assert_tab_count":
        from app.tab_helpers import open_pages

        expected = int(step.get("count", 0))
        actual = len(open_pages(page.context))
        on_log(f"{index}. Проверка вкладок → {actual} из {expected}")
        if actual != expected:
            raise AssertionError(f"Ожидалось вкладок: {expected}, открыто: {actual}")
        remove_highlight(page)
        return

    if action == "goto":
        url = ctx.resolve_text(str(step.get("url", "")))
        if urls_match(page.url, url):
            on_log(f"{index}. Уже на странице → {url}")
            return
        on_log(f"{index}. Переход → {url}")
        remove_highlight(page)
        page.goto(url, wait_until=NAV_WAIT_UNTIL, timeout=NAV_TIMEOUT_MS)
        return

    if action in {"remember_text", "remember_field", "remember_url"}:
        if action == "remember_text":
            variable = str(step.get("variable", "") or "")
            value = ctx.resolve_text(str(step.get("value", "") or ""))
            ctx.remember(variable, value)
            on_log(f"{index}. Запомнено «{variable}» = «{value}»")
        elif action == "remember_field":
            variable = str(step.get("variable", "") or "")
            field_selector = str(step.get("selector", "") or "")
            locator = page.locator(field_selector).first
            locator.wait_for(state="visible", timeout=10000)
            try:
                value = locator.input_value(timeout=3000)
            except Exception:  # noqa: BLE001
                value = (locator.inner_text(timeout=3000) or "").strip()
            ctx.remember(variable, value)
            on_log(f"{index}. Запомнено «{variable}» из поля {field_selector}")
        else:
            variable = str(step.get("variable", "") or "")
            ctx.remember(variable, page.url)
            on_log(f"{index}. Запомнено «{variable}» = текущий URL")
        remove_highlight(page)
        return

    if action == "assert_url":
        expected = ctx.resolve_text(str(step.get("url", "")))
        on_log(f"{index}. Проверка URL → {expected}")
        if not urls_match(page.url, expected):
            raise AssertionError(f"Ожидался URL «{expected}», сейчас: {page.url}")
        remove_highlight(page)
        return

    if action == "reload":
        on_log(f"{index}. Обновление страницы")
        remove_highlight(page)
        page.reload(wait_until=NAV_WAIT_UNTIL, timeout=NAV_TIMEOUT_MS)
        return

    if action == "go_back":
        on_log(f"{index}. Назад в истории")
        remove_highlight(page)
        page.go_back(wait_until=NAV_WAIT_UNTIL, timeout=NAV_TIMEOUT_MS)
        return

    if action == "close_browser":
        on_log(f"{index}. Закрываю браузер")
        remove_highlight(page)
        if on_close_browser is not None:
            on_close_browser()
        else:
            browser = page.context.browser
            if browser is not None:
                browser.close()
        return

    if action == "wait":
        ms = max(0, int(step.get("ms", 1000)))
        on_log(f"{index}. Пауза {ms} мс")
        remove_highlight(page)
        page.wait_for_timeout(ms)
        return

    if action == "wait_for":
        selector = step.get("selector", "")
        timeout_ms = max(1000, int(step.get("timeout_ms", 30000)))
        on_log(f"{index}. Жду появления → {step_log_target(step, selector)}")
        _maybe_highlight(page, selector, enabled=highlight, pause_ms=200)
        page.locator(selector).first.wait_for(state="visible", timeout=timeout_ms)
        remove_highlight(page)
        return

    if action == "wait_for_hidden":
        selector = step.get("selector", "")
        timeout_ms = max(1000, int(step.get("timeout_ms", 30000)))
        on_log(f"{index}. Жду исчезновения → {step_log_target(step, selector)}")
        _maybe_highlight(page, selector, enabled=highlight, pause_ms=200)
        page.locator(selector).first.wait_for(state="hidden", timeout=timeout_ms)
        remove_highlight(page)
        return

    if action == "press":
        key = str(step.get("key", "Enter"))
        target_selector = str(step.get("selector", "") or "").strip()
        if target_selector:
            on_log(f"{index}. Клавиша «{key}» → {step_log_target(step, target_selector)}")
            _maybe_highlight(page, target_selector, enabled=highlight, pause_ms=200)
            page.locator(target_selector).first.press(key, timeout=15000)
        else:
            on_log(f"{index}. Клавиша «{key}»")
            page.keyboard.press(key)
        remove_highlight(page)
        return

    selector = step.get("selector", "")
    if action not in {"press"} and not selector:
        on_log(f"{index}. Пропуск шага без селектора")
        return

    if action not in {"press"} and not selector:
        on_log(f"{index}. Пропуск шага без селектора")
        return

    if action == "hover":
        on_log(f"{index}. Наведение → {step_log_target(step, selector)}")
        _maybe_highlight(page, selector, enabled=highlight, pause_ms=200)
        locator = resolve_hover_locator(page, selector)
        locator.scroll_into_view_if_needed(timeout=5000)
        locator.hover(timeout=15000, force=True)
        page.wait_for_timeout(400)
        remove_highlight(page)
        return

    if action == "click":
        on_log(format_click_log(index, step))
        _maybe_highlight(page, selector, enabled=highlight, pause_ms=200)
        _prepare_click_target(page, step, on_log, index)
        locator = resolve_chained_locator(page, selector)
        try:
            locator.click(timeout=9000)
        except Exception:
            if _reveal_hover_menu(page, selector, on_log, index):
                resolve_chained_locator(page, selector).click(timeout=9000)
            else:
                raise
        remove_highlight(page)
        page.wait_for_load_state("domcontentloaded")
        return

    if action == "fill":
        selector = step.get("selector", "")
        raw_value = str(step.get("value", "") or "")
        value = ctx.resolve_text(raw_value)
        masked = "***" if step.get("inputType") in {"password"} else value
        _maybe_highlight(page, selector, enabled=highlight, pause_ms=200)
        on_log(format_fill_log(index, step, masked))
        _fill_locator(page, selector, value)
        return

    if action == "fill_generated":
        selector = step.get("selector", "")
        generator = str(step.get("generator", "") or "")
        value = ctx.generate(generator)
        _maybe_highlight(page, selector, enabled=highlight, pause_ms=200)
        on_log(format_fill_generated_log(index, step, generator, value))
        _fill_locator(page, selector, value)
        return

    if action == "prompt_email_code":
        import os

        selector = step.get("selector", "")
        timeout_ms = max(1000, int(step.get("timeout_ms", 60000)))
        on_log(f"{index}. Жду поля кода → {selector}")
        try:
            page.locator(selector).first.wait_for(state="visible", timeout=timeout_ms)
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(
                f"Поля кода не появились за {timeout_ms // 1000} с — "
                f"возможно, шаг стоит слишком рано в сценарии ({selector})"
            ) from exc

        email = resolve_email_for_code_prompt(page, step, prior_steps or [], run_context=ctx)
        if not email:
            raise RuntimeError(
                'Не удалось определить email для кода. '
                'Укажите в шаге: ввожу код из почты "user@mail.com" в "селектор"'
            )

        env_code = os.environ.get("SCENARIA_EMAIL_CODE", "").strip()
        if env_code:
            on_log(f"{index}. Код из SCENARIA_EMAIL_CODE ({email}) → {selector}")
            code = env_code
        elif interactive:
            from app.qt.sync_prompts import prompt_email_code_blocking

            on_log(f"{index}. Код из почты ({email}) → {selector}")
            code = prompt_email_code_blocking(email=email, selector=selector)
        else:
            raise RuntimeError(
                "Шаг «код из почты» в headless: задайте переменную окружения SCENARIA_EMAIL_CODE"
            )
        if code is None:
            raise RuntimeError("Ввод кода из почты отменён")
        value = code.strip()
        if not value:
            raise RuntimeError("Код из почты не введён")
        digits = step.get("digits")
        parsed_digits = int(digits) if digits else None
        input_method = str(step.get("inputMethod", "") or "").strip() or None
        locator = page.locator(selector)
        if not _otp_fields_visible(locator):
            on_log(f"{index}. Экран кода уже закрыт — продолжаем сценарий")
            remove_highlight(page)
            return
        fill_mode = fill_verification_code(
            page,
            selector,
            value,
            digits=parsed_digits,
            input_method=input_method,
            allow_advancing=True,
        )
        if fill_mode.endswith("-submit") or fill_mode == "already-submitted":
            on_log(f"{index}. Код принят, форма перешла дальше ({fill_mode})")
        else:
            on_log(f"{index}. Ввод кода ({fill_mode}) → {selector}")
        remove_highlight(page)
        return

    if action == "select":
        value = step.get("value", "")
        on_log(f"{index}. Выбор «{value}» → {selector}")
        page.locator(selector).first.select_option(value=value, timeout=15000)
        remove_highlight(page)
        return

    if action == "double_click":
        on_log(f"{index}. Двойной клик → {selector}")
        page.locator(selector).first.dblclick(timeout=9000)
        remove_highlight(page)
        return

    if action == "clear":
        on_log(f"{index}. Очистка → {selector}")
        page.locator(selector).first.clear(timeout=15000)
        remove_highlight(page)
        return

    if action == "check":
        on_log(f"{index}. Отметка → {selector}")
        page.locator(selector).first.check(timeout=15000)
        remove_highlight(page)
        return

    if action == "uncheck":
        on_log(f"{index}. Снятие отметки → {selector}")
        page.locator(selector).first.uncheck(timeout=15000)
        remove_highlight(page)
        return

    if action == "scroll_to":
        on_log(f"{index}. Скролл → {selector}")
        page.locator(selector).first.scroll_into_view_if_needed()
        remove_highlight(page)
        return

    if action == "draw_signature":
        on_log(f"{index}. Подпись")
        draw_signature_on_canvas(page, selector)
        remove_highlight(page)
        return

    if action == "upload":
        from app.upload_helpers import resolve_upload_path, validate_upload_path

        path = str(step.get("path", "") or "")
        missing = validate_upload_path(path, ctx.project_root)
        if missing:
            raise FileNotFoundError(missing)
        resolved = resolve_upload_path(path, ctx.project_root)
        on_log(f"{index}. Загрузка файла → {resolved}")
        page.locator(selector).first.set_input_files(str(resolved))
        remove_highlight(page)
        return

    if action == "download_click":
        on_log(f"{index}. Скачивание по клику → {selector}")
        _maybe_highlight(page, selector, enabled=highlight, pause_ms=200)
        with page.expect_download(timeout=60000) as download_info:
            page.locator(selector).first.click(timeout=15000)
        saved = save_playwright_download(download_info.value, ctx.download_dir())
        ctx.set_last_download(saved)
        on_log(f"{index}. Файл сохранён → {saved.name}")
        remove_highlight(page)
        return

    if action == "assert_download_contains":
        needle = str(step.get("value", "") or "")
        downloaded = ctx.last_download
        if downloaded is None or not downloaded.is_file():
            raise AssertionError("Нет скачанного файла — сначала выполните «скачиваю по клику на …»")
        on_log(f"{index}. Проверка скачанного файла «{downloaded.name}»")
        if downloaded.stat().st_size <= 0:
            raise AssertionError(f"Скачанный файл пуст: {downloaded.name}")
        if not file_contains_substring(downloaded, needle):
            raise AssertionError(f"Файл «{downloaded.name}» не содержит «{needle}»")
        remove_highlight(page)
        return

    if action == "assert_visible":
        on_log(f"{index}. Проверка видимости → {selector}")
        page.locator(selector).first.wait_for(state="visible", timeout=10000)
        remove_highlight(page)
        return

    if action == "assert_text":
        expected = ctx.resolve_text(str(step.get("value", "") or ""))
        on_log(f"{index}. Проверка текста «{expected}» → {selector}")
        locator = page.locator(selector).first
        locator.wait_for(state="visible", timeout=10000)
        actual = (locator.inner_text(timeout=5000) or "").strip()
        if expected not in actual:
            raise AssertionError(f"Ожидался текст «{expected}», получено: «{actual[:120]}»")
        remove_highlight(page)
        return

    if action == "assert_hidden":
        on_log(f"{index}. Проверка скрытия → {selector}")
        locator = page.locator(selector)
        if locator.count() > 0 and locator.first.is_visible(timeout=2000):
            raise AssertionError(f"Элемент всё ещё виден: {selector}")
        remove_highlight(page)
        return

    on_log(f"{index}. Неизвестное действие: {action}")
    remove_highlight(page)


def run_scenario_on_page(
    page: Page,
    scenario: dict,
    on_log: LogCallback,
    *,
    stop_event: threading.Event | None = None,
    focus_event: threading.Event | None = None,
    highlight: bool = True,
    interactive: bool = True,
    screenshot_on_error: bool = True,
    on_step: StepCallback | None = None,
    on_close_browser: CloseBrowserCallback | None = None,
    on_between_steps: BetweenStepsCallback | None = None,
    trace_context=None,
    start_step: int = 0,
    end_step: int | None = None,
    run_initial_goto: bool = True,
    project_root: Path | None = None,
) -> PlayResult:
    log_lines: list[str] = []

    def _log(message: str) -> None:
        log_lines.append(message)
        on_log(message)

    steps = normalize_steps(list(scenario.get("steps", [])))
    total_steps = len(steps)
    if total_steps == 0:
        start_index = 0
        end_index = -1
    else:
        start_index = max(0, min(start_step, total_steps - 1))
        end_index = total_steps - 1 if end_step is None else max(0, min(end_step, total_steps - 1))
        if end_index < start_index:
            end_index = start_index

    start_url = scenario.get("startUrl") or (
        steps[0].get("url") if steps and steps[0].get("action") == "goto" else ""
    )
    scenario_name = str(scenario.get("name", ""))

    if trace_context is not None:
        start_play_trace(trace_context, scenario_name=scenario_name)

    if start_index > 0 and end_index >= start_index:
        _log(
            f"Запуск теста «{scenario_name}» (шаги {start_index + 1}–{end_index + 1} из {total_steps})"
        )
        _log(f"Пропуск шагов 1–{start_index}")
    elif total_steps:
        _log(f"Запуск теста «{scenario_name}» ({total_steps} шагов)")

    run_context = RunContext(seed=scenario.get("runSeed"), project_root=project_root)
    run_context.set_initial_variables(dict(scenario.get("variables") or {}))
    run_context.bind_page(page)
    from app.download_helpers import new_download_run_dir

    _, download_dir = new_download_run_dir()
    run_context.set_download_dir(download_dir)
    setup_highlight_cleanup(page)

    def _maybe_focus_browser() -> None:
        if focus_event is None or not focus_event.is_set():
            return
        focus_event.clear()
        from app.browser_focus import focus_browser_context

        focus_browser_context(page.context)

    if start_index == 0 and start_url and not urls_match(page.url, start_url):
        _log(f"Открываю {start_url}")
        remove_highlight(page)
        page.goto(start_url, wait_until=NAV_WAIT_UNTIL, timeout=NAV_TIMEOUT_MS)
    elif start_index > 0 and run_initial_goto:
        for prep_step in steps:
            if prep_step.get("action") == "goto":
                url = str(prep_step.get("url", "") or "")
                if url and not urls_match(page.url, url):
                    _log(f"Подготовка: открываю {url}")
                    remove_highlight(page)
                    page.goto(url, wait_until=NAV_WAIT_UNTIL, timeout=NAV_TIMEOUT_MS)
                break

    playable: list[tuple[int, dict]] = []
    for step_index, step in enumerate(steps):
        if step_index < start_index or step_index > end_index:
            continue
        if (
            step_index == 0
            and step.get("action") == "goto"
            and urls_match(page.url, step.get("url", ""))
        ):
            continue
        playable.append((step_index, step))

    skipped_count = total_steps - len(playable)
    executed = 0
    step_results: list[dict[str, Any]] = []
    for display_index, (step_index, step) in enumerate(playable, start=1):
        _maybe_focus_browser()
        if on_between_steps is not None:
            on_between_steps(page)
        if stop_event and stop_event.is_set():
            remove_highlight(page)
            return {
                "success": False,
                "message": "Остановлено пользователем",
                "executed_count": executed,
                "total_count": len(playable),
                "skipped_count": skipped_count,
                "failed_step": None,
                "failed_step_index": None,
                "screenshot_path": None,
                "trace_path": None,
                "log_lines": log_lines,
                "step_results": step_results,
            }
        started = time.perf_counter()
        try:
            if on_step:
                on_step(display_index, step_index, step)
            page = run_context.current_page(page)
            execute_step(
                page,
                step,
                display_index,
                _log,
                highlight=highlight,
                interactive=interactive,
                prior_steps=steps[:step_index],
                on_close_browser=on_close_browser,
                run_context=run_context,
            )
            duration_ms = int((time.perf_counter() - started) * 1000)
            step_results.append(
                {
                    "index": step_index,
                    "action": str(step.get("action", "") or ""),
                    "selector": str(step.get("selector", "") or step.get("url", "") or ""),
                    "success": True,
                    "message": "",
                    "duration_ms": duration_ms,
                }
            )
            executed += 1
            if step.get("action") == "close_browser":
                break
        except Exception as exc:  # noqa: BLE001
            duration_ms = int((time.perf_counter() - started) * 1000)
            step_results.append(
                {
                    "index": step_index,
                    "action": str(step.get("action", "") or ""),
                    "selector": str(step.get("selector", "") or step.get("url", "") or ""),
                    "success": False,
                    "message": str(exc),
                    "duration_ms": duration_ms,
                }
            )
            remove_highlight(page)
            screenshot_path = None
            trace_path = None
            if screenshot_on_error:
                screenshot_path = capture_failure_screenshot(page, scenario_name, display_index)
                if screenshot_path:
                    _log(f"Скриншот ошибки: {screenshot_path}")
            if trace_context is not None:
                trace_path = stop_play_trace(
                    trace_context,
                    keep=True,
                    scenario_name=scenario_name,
                    step_index=display_index,
                )
                if trace_path:
                    _log(f"Trace: {trace_path}")
            return {
                "success": False,
                "message": str(exc),
                "executed_count": executed,
                "total_count": len(playable),
                "skipped_count": skipped_count,
                "failed_step": display_index,
                "failed_step_index": step_index,
                "screenshot_path": screenshot_path,
                "trace_path": trace_path,
                "log_lines": log_lines,
                "step_results": step_results,
            }

    remove_highlight(page)
    if trace_context is not None:
        stop_play_trace(trace_context, keep=False, scenario_name=scenario_name, step_index=0)
    return {
        "success": True,
        "message": "Готово",
        "executed_count": executed,
        "total_count": len(playable),
        "skipped_count": skipped_count,
        "failed_step": None,
        "failed_step_index": None,
        "screenshot_path": None,
        "trace_path": None,
        "log_lines": log_lines,
        "step_results": step_results,
    }


class ScenarioPlayer:
    def __init__(self) -> None:
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self._focus = threading.Event()
        self._playwright = None
        self._browser = None
        self._context = None
        self._page = None
        self._shutdown_done = False
        self._picker = SelectorPickerSession()
        self._pick_requests: queue.Queue[object] = queue.Queue()
        self._on_browser_lost: Callable[[], None] | None = None
        self._browser_lost_notified = False
        self._session_releasing = False

    def set_browser_lost_handler(self, handler: Callable[[], None] | None) -> None:
        self._on_browser_lost = handler

    @property
    def browser_open(self) -> bool:
        browser = self._browser
        if browser is None or not browser.is_connected():
            return False
        context = self._context
        if context is not None:
            return any(not page.is_closed() for page in context.pages)
        page = self._page
        return page is not None and not page.is_closed()

    @property
    def worker_alive(self) -> bool:
        thread = self._thread
        return thread is not None and thread.is_alive()

    def play(
        self,
        scenario: dict,
        on_log: LogCallback,
        on_done: Callable[[PlayResult], None],
        *,
        headless: bool = False,
        slow_mo_ms: int = 200,
        on_started: Callable[[], None] | None = None,
        start_step: int = 0,
        end_step: int | None = None,
        project_root: Path | None = None,
    ) -> None:
        if self._thread and self._thread.is_alive():
            raise RuntimeError("Воспроизведение уже запущено")
        if self._thread is not None:
            self._release_detached_session()
            self._thread = None
        self._stop.clear()
        self._browser_lost_notified = False
        self._thread = threading.Thread(
            target=self._run,
            args=(
                scenario,
                on_log,
                on_done,
                headless,
                slow_mo_ms,
                on_started,
                start_step,
                end_step,
                project_root,
            ),
            daemon=True,
        )
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        self._pick_requests.put(_PICK_CANCEL)
        thread = self._thread
        if thread is not None and thread.is_alive():
            thread.join(timeout=30)
        self._release_detached_session()
        if thread is None or not thread.is_alive():
            self._thread = None

    def focus_browser(self) -> bool:
        if not self.browser_open or self._context is None:
            return False
        thread = self._thread
        if thread is not None and thread.is_alive():
            self._focus.set()
            return True
        from app.browser_focus import focus_browser_context

        return focus_browser_context(self._context)

    def pick_selector(
        self,
        on_complete: PickerCallback,
        on_error: ErrorCallback | None = None,
    ) -> None:
        if not self.browser_open:
            raise RuntimeError("Браузер теста не открыт")
        self._pick_requests.put((on_complete, on_error))

    def cancel_pick_selector(self) -> None:
        self._pick_requests.put(_PICK_CANCEL)

    def _cancel_pending_picks(self, page: Page) -> None:
        self._picker.cancel_active(page)
        while True:
            try:
                item = self._pick_requests.get_nowait()
            except queue.Empty:
                break
            if item is _PICK_CANCEL:
                continue
            on_complete, _on_error = item
            on_complete(None)

    def _active_page(self) -> Page:
        page = self._page
        if page is not None and not page.is_closed():
            return page
        context = self._context
        if context is None:
            raise RuntimeError("Браузер теста не открыт")
        pages = [item for item in context.pages if not item.is_closed()]
        if not pages:
            raise RuntimeError("Нет открытых вкладок")
        self._page = pages[-1]
        return self._page

    def _pick_pump(self, page: Page) -> None:
        if self._stop.is_set():
            self._picker.cancel_active(page)
            return
        try:
            item = self._pick_requests.get_nowait()
        except queue.Empty:
            item = None
        if item is _PICK_CANCEL:
            self._picker.cancel_active(page)
            return
        if item is not None:
            self._pick_requests.put(item)
        try:
            if not page.is_closed():
                page.wait_for_timeout(25)
        except Exception:
            pass

    def _service_pick_requests(self, page: Page) -> None:
        while True:
            try:
                item = self._pick_requests.get_nowait()
            except queue.Empty:
                return
            if item is _PICK_CANCEL:
                self._cancel_pending_picks(page)
                continue
            on_complete, on_error = item
            try:
                active = self._active_page()
                selector = self._picker.pick(
                    active,
                    active.context,
                    pump=lambda: self._pick_pump(active),
                )
                on_complete(selector)
            except Exception as exc:  # noqa: BLE001
                if on_error is not None:
                    on_error(exc)
                else:
                    on_complete(None)

    def _idle_loop(self, page: Page) -> None:
        while not self._stop.is_set() and self.browser_open:
            if self._poll_browser_lost():
                break
            try:
                active = self._active_page()
            except RuntimeError:
                self._handle_browser_disconnected()
                break
            if self._focus.is_set():
                self._focus.clear()
                from app.browser_focus import focus_browser_context

                focus_browser_context(active.context)
            self._service_pick_requests(active)
            if self._stop.is_set():
                break
            try:
                active.wait_for_timeout(50)
            except Exception:
                self._handle_browser_disconnected()
                break

    def _attach_session_watchers(self) -> None:
        browser = self._browser
        if browser is None:
            return
        try:
            browser.on("disconnected", lambda _: self._handle_browser_disconnected())
        except Exception:
            pass
        context = self._context
        if context is not None:
            try:
                context.on("close", lambda _: self._handle_browser_disconnected())
            except Exception:
                pass

    def _poll_browser_lost(self) -> bool:
        if self.browser_open:
            return False
        self._handle_browser_disconnected()
        return True

    def _handle_browser_disconnected(self) -> None:
        if self._session_releasing:
            return
        if self._browser is None and self._browser_lost_notified:
            return
        was_open = self._browser is not None
        self._browser = None
        self._context = None
        self._page = None
        if was_open and not self._browser_lost_notified:
            self._browser_lost_notified = True
            if self._on_browser_lost:
                self._on_browser_lost()

    def shutdown(self) -> None:
        if self._shutdown_done:
            return
        self._shutdown_done = True
        self._stop.set()
        thread = self._thread
        if thread is not None and thread.is_alive():
            thread.join(timeout=15)
        self._release_detached_session()

    def _release_detached_session(self) -> None:
        if self._session_releasing:
            return
        self._session_releasing = True
        playwright = self._playwright
        browser = self._browser
        context = self._context
        page = self._page
        self._browser = None
        self._context = None
        self._playwright = None
        self._page = None
        try:
            release_playwright_session(
                playwright=playwright,
                browser=browser,
                context=context,
                before_close=lambda: self._picker.cancel_active(page),
            )
        finally:
            self._session_releasing = False

    def _run(
        self,
        scenario: dict,
        on_log: LogCallback,
        on_done: Callable[[PlayResult], None],
        headless: bool,
        slow_mo_ms: int,
        on_started: Callable[[], None] | None,
        start_step: int = 0,
        end_step: int | None = None,
        project_root: Path | None = None,
    ) -> None:
        configure_playwright_browsers()
        result: PlayResult
        session_closed = False
        playwright = None
        browser = None
        context = None
        page = None

        def close_session() -> None:
            nonlocal session_closed
            if session_closed:
                return
            session_closed = True
            self._session_releasing = True
            try:
                if page is not None:
                    remove_highlight(page)
                self._picker.cancel_active(page)
                release_playwright_session(
                    playwright=playwright,
                    browser=browser,
                    context=context,
                )
            finally:
                self._session_releasing = False
                self._browser = None
                self._context = None
                self._playwright = None
                self._page = None

        try:
            playwright = sync_playwright().start()
            engine = str(scenario.get("browserEngine") or "") or load_browser_engine()
            browser = launch_browser(
                playwright,
                engine=engine,
                headless=headless,
                slow_mo_ms=slow_mo_ms,
                on_status=on_log,
            )
            start_url = scenario.get("startUrl") or ""
            steps = scenario.get("steps") or []
            if not start_url and steps and steps[0].get("action") == "goto":
                start_url = str(steps[0].get("url") or "")
            context = browser.new_context(
                **browser_context_options(start_url, headless=headless, project_root=project_root)
            )
            page = context.new_page()
            self._playwright = playwright
            self._browser = browser
            self._context = context
            self._page = page
            self._browser_lost_notified = False
            self._attach_session_watchers()
            if on_started is not None:
                on_started()

            result = run_scenario_on_page(
                page,
                scenario,
                on_log,
                stop_event=self._stop,
                focus_event=self._focus,
                highlight=not headless,
                interactive=not headless,
                trace_context=context,
                on_close_browser=close_session,
                on_between_steps=self._service_pick_requests,
                start_step=start_step,
                end_step=end_step,
                project_root=project_root,
            )
        except Exception as exc:  # noqa: BLE001
            result = {
                "success": False,
                "message": str(exc),
                "executed_count": 0,
                "total_count": len(scenario.get("steps", [])),
                "failed_step": None,
                "failed_step_index": None,
                "screenshot_path": None,
                "trace_path": None,
                "log_lines": [f"Ошибка: {exc}"],
                "step_results": [],
            }
            on_log(f"Ошибка: {exc}")

        on_done(result)

        if session_closed:
            return

        if page is None:
            return

        self._playwright = playwright
        self._browser = browser
        self._context = context
        self._page = page

        if headless:
            close_session()
            return

        if not result.get("success"):
            on_log(
                "Тест завершён с ошибкой. Браузер остаётся открытым — исправьте шаги и запустите снова."
            )
            self._idle_loop(page)
            if not session_closed and not self.browser_open:
                close_session()
            return

        on_log(
            "Тест завершён. Браузер остаётся открытым — добавьте шаг «закрываю браузер» для закрытия."
        )
        self._idle_loop(page)
        if not session_closed and not self.browser_open:
            close_session()
