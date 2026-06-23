"""Structured selector validation for scenarios."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Literal

from playwright.sync_api import Page

from app.player import (
    _ASSERT_ACTIONS,
    _INTERACTIVE_ACTIONS,
    _NAV_ACTIONS,
    _PROMPT_ACTIONS,
    _SESSION_ACTIONS,
    _WAIT_ACTIONS,
    _locator_hidden_issues,
    _locator_issues,
    _locator_issues_for_code_input,
    urls_match,
)
from app.run_variables import normalize_generator_name
from app.selector_build import is_fragile_selector
from app.steps import NAV_TIMEOUT_MS, NAV_WAIT_UNTIL, normalize_steps

ValidateStatus = Literal[
    "ok",
    "not_found",
    "ambiguous",
    "hidden",
    "fragile",
    "skipped",
    "error",
    "no_selector",
]

_TAB_ACTIONS = frozenset({"switch_tab", "close_tab", "assert_tab_count"})


@dataclass
class StepValidateResult:
    step_index: int
    action: str
    selector: str
    status: ValidateStatus
    message: str


def _validate_tab_step(
    page: Page,
    step: dict[str, Any],
    *,
    step_index: int,
) -> StepValidateResult:
    from app.tab_helpers import open_pages, resolve_tab_page

    action = str(step.get("action", "") or "")
    if action == "switch_tab":
        mode = str(step.get("mode", "") or "")
        value = str(step.get("value", "") or "")
        label = f"{mode}:{value}" if value else mode
        target = resolve_tab_page(page.context, mode=mode, value=value)
        if target is None:
            return StepValidateResult(step_index, action, label, "error", "вкладка не найдена")
        return StepValidateResult(step_index, action, label, "ok", "")
    if action == "close_tab":
        if len(open_pages(page.context)) <= 1:
            return StepValidateResult(
                step_index,
                action,
                "",
                "error",
                "единственная вкладка — закрыть нельзя",
            )
        return StepValidateResult(step_index, action, "", "ok", "")
    expected = int(step.get("count", 0))
    actual = len(open_pages(page.context))
    if actual != expected:
        return StepValidateResult(
            step_index,
            action,
            str(expected),
            "error",
            f"открыто {actual}, ожидалось {expected}",
        )
    return StepValidateResult(step_index, action, str(expected), "ok", "")


def _for_each_selector_issues(page: Page, selector: str) -> list[str]:
    try:
        count = page.locator(selector).count()
    except Exception as exc:  # noqa: BLE001
        return [f"некорректный селектор: {exc}"]
    if count == 0:
        return ["элемент не найден"]
    return []


def _validate_block_condition(
    page: Page,
    condition: dict[str, Any],
    *,
    step_index: int,
    block_action: str,
) -> StepValidateResult | None:
    kind = str(condition.get("type", "") or "")
    result_action = f"{block_action}_condition"
    if kind in {"visible", "hidden"}:
        selector = str(condition.get("selector", "") or "")
        if not selector:
            return StepValidateResult(step_index, result_action, selector, "no_selector", "нет селектора в условии")
        if kind == "hidden":
            issues = _locator_hidden_issues(page, selector)
        else:
            issues = _locator_issues(page, selector)
        status, message = _issues_to_status(issues, selector=selector)
        return StepValidateResult(step_index, result_action, selector, status, message)
    if kind == "url_contains":
        needle = str(condition.get("value", "") or "")
        if needle and needle not in page.url:
            return StepValidateResult(
                step_index,
                result_action,
                needle,
                "error",
                f"URL не содержит «{needle}» — сейчас {page.url}",
            )
        return StepValidateResult(step_index, result_action, needle, "ok", "")
    if kind == "page_text":
        needle = str(condition.get("value", "") or "")
        if not needle:
            return StepValidateResult(step_index, result_action, needle, "ok", "")
        try:
            if needle not in page.content():
                return StepValidateResult(
                    step_index,
                    result_action,
                    needle,
                    "error",
                    f"текст «{needle}» не найден на странице",
                )
        except Exception as exc:  # noqa: BLE001
            return StepValidateResult(step_index, result_action, needle, "error", str(exc))
        return StepValidateResult(step_index, result_action, needle, "ok", "")
    return None


def _issues_to_status(issues: list[str], *, selector: str) -> tuple[ValidateStatus, str]:
    if not issues:
        if selector and is_fragile_selector(selector):
            return "fragile", "селектор хрупкий, но элемент найден"
        return "ok", ""
    text = ", ".join(issues)
    lowered = text.lower()
    if "не найден" in lowered:
        return "not_found", text
    if "найдено элементов" in lowered:
        return "ambiguous", text
    if "скрыт" in lowered or "не виден" in lowered or "не видно" in lowered:
        return "hidden", text
    return "error", text


def validate_step_selector(
    page: Page,
    step: dict[str, Any],
    *,
    step_index: int,
    project_root: Path | None = None,
    browser_engine: str | None = None,
) -> StepValidateResult | None:
    action = str(step.get("action", "") or "")
    selector = str(step.get("selector", "") or "")
    if action in {"if", "repeat", "while", "for_each"}:
        return StepValidateResult(step_index, action, selector, "skipped", "")
    if action in {"goto"} | _NAV_ACTIONS | _SESSION_ACTIONS | _WAIT_ACTIONS:
        return StepValidateResult(step_index, action, selector, "skipped", "")
    if action in _TAB_ACTIONS:
        return _validate_tab_step(page, step, step_index=step_index)
    if action in {"remember_text", "remember_url", "assert_download_contains"}:
        return StepValidateResult(step_index, action, selector, "skipped", "")
    if action == "remember_field":
        if not selector:
            return StepValidateResult(step_index, action, selector, "no_selector", "нет селектора")
        issues = _locator_issues(page, selector, require_enabled=False)
        status, message = _issues_to_status(issues, selector=selector)
        return StepValidateResult(step_index, action, selector, status, message)
    if action == "assert_url":
        expected = str(step.get("url", "") or "")
        if expected and not urls_match(page.url, expected):
            return StepValidateResult(step_index, action, expected, "error", f"URL не совпадает — сейчас {page.url}")
        return StepValidateResult(step_index, action, expected, "ok", "")
    if action in _WAIT_ACTIONS:
        if action in {"wait_for", "wait_for_hidden"} and not selector:
            return StepValidateResult(step_index, action, selector, "no_selector", "нет селектора")
        return StepValidateResult(step_index, action, selector, "skipped", "")
    if action == "press" and not selector:
        return StepValidateResult(step_index, action, selector, "skipped", "")
    if action in _ASSERT_ACTIONS and action != "assert_url":
        if not selector:
            return StepValidateResult(step_index, action, selector, "no_selector", "нет селектора")
        if action == "assert_hidden":
            issues = _locator_hidden_issues(page, selector)
        else:
            issues = _locator_issues(page, selector)
        status, message = _issues_to_status(issues, selector=selector)
        return StepValidateResult(step_index, action, selector, status, message)
    if action in _INTERACTIVE_ACTIONS:
        if not selector:
            return StepValidateResult(step_index, action, selector, "no_selector", "нет селектора")
        if action == "upload":
            from app.upload_helpers import validate_upload_path

            missing = validate_upload_path(str(step.get("path", "") or ""), project_root)
            if missing:
                return StepValidateResult(step_index, action, selector, "error", missing)
        require_enabled = action in {
            "click",
            "fill",
            "fill_generated",
            "select",
            "double_click",
            "clear",
            "check",
            "uncheck",
            "upload",
            "download_click",
        }
        if action == "fill_generated" and normalize_generator_name(str(step.get("generator", ""))) is None:
            return StepValidateResult(
                step_index,
                action,
                selector,
                "error",
                f"неизвестный генератор «{step.get('generator', '')}»",
            )
        issues = _locator_issues(page, selector, require_enabled=require_enabled)
        status, message = _issues_to_status(issues, selector=selector)
        return StepValidateResult(step_index, action, selector, status, message)
    if action in _PROMPT_ACTIONS:
        if not selector:
            return StepValidateResult(step_index, action, selector, "no_selector", "нет селектора")
        digits = step.get("digits")
        parsed_digits = int(digits) if digits else None
        issues = _locator_issues_for_code_input(page, selector, digits=parsed_digits)
        status, message = _issues_to_status(issues, selector=selector)
        return StepValidateResult(step_index, action, selector, status, message)
    if action not in _ASSERT_ACTIONS | _INTERACTIVE_ACTIONS | _WAIT_ACTIONS | _NAV_ACTIONS | _SESSION_ACTIONS | _PROMPT_ACTIONS | {"goto"}:
        return StepValidateResult(step_index, action, selector, "error", f"неизвестное действие «{action}»")
    return StepValidateResult(step_index, action, selector, "skipped", "")


def validate_scenario_selectors(
    page: Page,
    scenario: dict[str, Any],
    *,
    on_log: Any | None = None,
    project_root: Path | None = None,
    browser_engine: str | None = None,
) -> list[StepValidateResult]:
    results: list[StepValidateResult] = []
    steps = normalize_steps(list(scenario.get("steps", [])))
    if not steps:
        return results

    if browser_engine is None:
        from app.browser_config import load_browser_engine

        browser_engine = load_browser_engine()

    from app.browser_compat import compatibility_warning

    start_url = scenario.get("startUrl") or (
        steps[0].get("url") if steps and steps[0].get("action") == "goto" else ""
    )
    if start_url and not urls_match(page.url, start_url):
        if on_log:
            on_log(f"Переход для проверки → {start_url}")
        try:
            page.goto(start_url, wait_until=NAV_WAIT_UNTIL, timeout=NAV_TIMEOUT_MS)
        except Exception as exc:  # noqa: BLE001
            results.append(
                StepValidateResult(0, "goto", str(start_url), "error", f"не удалось открыть URL: {exc}")
            )
            return results

    def _append_result(item: StepValidateResult) -> None:
        warn = compatibility_warning(item.action, browser_engine)
        if warn and item.status in {"ok", "skipped"}:
            item = StepValidateResult(item.step_index, item.action, item.selector, "fragile", warn)
        results.append(item)

    def validate_one(index: int, step: dict[str, Any]) -> None:
        action = str(step.get("action", "") or "")
        if action in {"if", "repeat"}:
            for sub_step in step.get("steps") or []:
                validate_one(index, sub_step)
            return
        if action == "while":
            condition = step.get("condition") or {}
            cond_item = _validate_block_condition(page, condition, step_index=index, block_action="while")
            if cond_item is not None:
                _append_result(cond_item)
            for sub_step in step.get("steps") or []:
                validate_one(index, sub_step)
            return
        if action == "for_each":
            selector = str(step.get("selector", "") or "")
            if not selector:
                _append_result(
                    StepValidateResult(index, action, selector, "no_selector", "нет селектора списка")
                )
            else:
                issues = _for_each_selector_issues(page, selector)
                status, message = _issues_to_status(issues, selector=selector)
                _append_result(StepValidateResult(index, action, selector, status, message))
            for sub_step in step.get("steps") or []:
                validate_one(index, sub_step)
            return
        item = validate_step_selector(
            page,
            step,
            step_index=index,
            project_root=project_root,
            browser_engine=browser_engine,
        )
        if item is None:
            return
        _append_result(item)

    for index, step in enumerate(steps, start=1):
        validate_one(index, step)
    return results


def validate_results_to_issues(results: list[StepValidateResult]) -> list[str]:
    issues: list[str] = []
    if not results:
        issues.append("Сценарий не содержит шагов")
    for item in results:
        if item.status in {"ok", "skipped", "fragile"}:
            if item.status == "fragile":
                issues.append(f"Шаг {item.step_index}: хрупкий селектор → {item.selector}")
            continue
        if item.message:
            issues.append(f"Шаг {item.step_index}: {item.message} → {item.selector or item.action}")
        else:
            issues.append(f"Шаг {item.step_index}: {item.status} → {item.selector or item.action}")
    return issues


def validate_results_to_payload(results: list[StepValidateResult]) -> list[dict[str, Any]]:
    return [asdict(item) for item in results]


def format_validate_report_text(
    results: list[StepValidateResult],
    *,
    issues: list[str] | None = None,
) -> str:
    status_labels = {
        "ok": "OK",
        "fragile": "Хрупкий",
        "not_found": "Не найден",
        "ambiguous": "Несколько",
        "hidden": "Скрыт",
        "skipped": "—",
        "error": "Ошибка",
        "no_selector": "Нет селектора",
    }
    lines: list[str] = []
    if issues is not None:
        lines.append(f"Проблем: {len(issues)}")
        lines.extend(f"  • {issue}" for issue in issues)
        lines.append("")
    lines.append("Шаг | Действие | Статус | Селектор | Сообщение")
    for item in results:
        if item.status == "skipped":
            continue
        label = status_labels.get(item.status, item.status)
        target = item.selector or "—"
        message = item.message or ""
        lines.append(f"{item.step_index} | {item.action} | {label} | {target} | {message}")
    return "\n".join(lines).strip()
