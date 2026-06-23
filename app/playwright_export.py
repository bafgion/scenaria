"""Export recorder scenarios to Playwright test scripts."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from app.run_variables import generator_gherkin_phrase
from app.steps import normalize_steps


class ExportFormat(str, Enum):
    TYPESCRIPT = "typescript"
    PYTHON = "python"


class ExportSupport(str, Enum):
    SUPPORTED = "supported"
    PARTIAL = "partial"
    UNSUPPORTED = "unsupported"


# Catalog web steps → Playwright export coverage (VA-only steps are out of scope).
EXPORT_ACTION_SUPPORT: dict[str, ExportSupport] = {
    "goto": ExportSupport.SUPPORTED,
    "go_back": ExportSupport.SUPPORTED,
    "reload": ExportSupport.SUPPORTED,
    "scroll_to": ExportSupport.SUPPORTED,
    "click": ExportSupport.SUPPORTED,
    "double_click": ExportSupport.SUPPORTED,
    "hover": ExportSupport.SUPPORTED,
    "fill": ExportSupport.SUPPORTED,
    "fill_generated": ExportSupport.PARTIAL,
    "clear": ExportSupport.SUPPORTED,
    "select": ExportSupport.SUPPORTED,
    "check": ExportSupport.SUPPORTED,
    "uncheck": ExportSupport.SUPPORTED,
    "press": ExportSupport.SUPPORTED,
    "upload": ExportSupport.SUPPORTED,
    "draw_signature": ExportSupport.SUPPORTED,
    "assert_visible": ExportSupport.SUPPORTED,
    "assert_hidden": ExportSupport.SUPPORTED,
    "assert_text": ExportSupport.SUPPORTED,
    "assert_url": ExportSupport.SUPPORTED,
    "wait": ExportSupport.SUPPORTED,
    "wait_for": ExportSupport.SUPPORTED,
    "wait_for_hidden": ExportSupport.SUPPORTED,
    "close_browser": ExportSupport.SUPPORTED,
    "prompt_email_code": ExportSupport.UNSUPPORTED,
    "download_click": ExportSupport.UNSUPPORTED,
    "assert_download_contains": ExportSupport.UNSUPPORTED,
    "remember_text": ExportSupport.UNSUPPORTED,
    "remember_field": ExportSupport.UNSUPPORTED,
    "remember_url": ExportSupport.UNSUPPORTED,
    "switch_tab": ExportSupport.UNSUPPORTED,
    "close_tab": ExportSupport.UNSUPPORTED,
    "assert_tab_count": ExportSupport.UNSUPPORTED,
    "if": ExportSupport.UNSUPPORTED,
    "repeat": ExportSupport.UNSUPPORTED,
    "while": ExportSupport.UNSUPPORTED,
    "for_each": ExportSupport.UNSUPPORTED,
}


@dataclass
class ExportAnalysis:
    supported: list[str] = field(default_factory=list)
    partial: list[str] = field(default_factory=list)
    unsupported: list[str] = field(default_factory=list)

    @property
    def has_blocking_issues(self) -> bool:
        return bool(self.unsupported)

    @property
    def has_warnings(self) -> bool:
        return bool(self.partial or self.unsupported)


def export_support_for_action(action: str) -> ExportSupport:
    return EXPORT_ACTION_SUPPORT.get(str(action or ""), ExportSupport.UNSUPPORTED)


def analyze_export(scenario: dict[str, Any]) -> ExportAnalysis:
    """Classify scenario steps by Playwright export coverage."""
    steps = normalize_steps(list(scenario.get("steps", [])))
    analysis = ExportAnalysis()
    seen: set[str] = set()
    for step in steps:
        action = str(step.get("action", "") or "")
        if not action or action in seen:
            continue
        seen.add(action)
        level = export_support_for_action(action)
        if level == ExportSupport.SUPPORTED:
            analysis.supported.append(action)
        elif level == ExportSupport.PARTIAL:
            analysis.partial.append(action)
        else:
            analysis.unsupported.append(action)
    return analysis


def format_export_warnings(analysis: ExportAnalysis) -> str:
    """Multi-line warning for GUI confirm dialogs."""
    lines: list[str] = []
    if analysis.partial:
        lines.append(
            "Частичный экспорт: " + ", ".join(analysis.partial)
            + " (нужны фикстуры или переменные окружения)."
        )
    if analysis.unsupported:
        lines.append(
            "Не экспортируется в Playwright: " + ", ".join(analysis.unsupported)
            + " (в файле останутся комментарии unsupported)."
        )
    return "\n".join(lines)


def format_export_warning_lines(analysis: ExportAnalysis) -> list[str]:
    """Single-line warnings for CLI stderr."""
    lines: list[str] = []
    if analysis.partial:
        lines.append(f"warning: partial export for actions: {', '.join(analysis.partial)}")
    if analysis.unsupported:
        lines.append(f"warning: unsupported actions: {', '.join(analysis.unsupported)}")
    return lines


def _ts_literal(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def _py_literal(value: str) -> str:
    return repr(value)


def _safe_test_name(name: str) -> str:
    cleaned = re.sub(r"[^\w\-]+", "_", name.strip(), flags=re.UNICODE).strip("_")
    return cleaned or "scenario"


def _generator_env_name(generator: str) -> str:
    safe = re.sub(r"[^a-zA-Z0-9_]", "_", generator).upper()
    return f"SCENARIA_GEN_{safe or 'VALUE'}"


def _locator_expr(fmt: ExportFormat, selector: str) -> str:
    if fmt == ExportFormat.TYPESCRIPT:
        return f"page.locator({_ts_literal(selector)}).first()"
    return f"page.locator({_py_literal(selector)}).first()"


def _signature_export_ts(selector: str) -> list[str]:
    loc = _locator_expr(ExportFormat.TYPESCRIPT, selector)
    return [
        "  {",
        f"    const box = await {loc}.boundingBox();",
        "    if (!box) throw new Error('Canvas not found');",
        "    const { x, y, width: w, height: h } = box;",
        "    await page.mouse.move(x + w * 0.12, y + h * 0.55);",
        "    await page.mouse.down();",
        "    for (const [px, py] of [[0.28, 0.38], [0.42, 0.62], [0.58, 0.35], [0.72, 0.58], [0.86, 0.42]]) {",
        "      await page.mouse.move(x + w * px, y + h * py, { steps: 8 });",
        "    }",
        "    await page.mouse.up();",
        "  }",
    ]


def _signature_export_py(selector: str) -> list[str]:
    loc = _locator_expr(ExportFormat.PYTHON, selector)
    return [
        "    box = " + loc + ".bounding_box()",
        "    if not box:",
        f"        raise RuntimeError('Canvas not found: {_py_literal(selector)}')",
        "    x, y, w, h = box['x'], box['y'], box['width'], box['height']",
        "    page.mouse.move(x + w * 0.12, y + h * 0.55)",
        "    page.mouse.down()",
        "    for px, py in ((0.28, 0.38), (0.42, 0.62), (0.58, 0.35), (0.72, 0.58), (0.86, 0.42)):",
        "        page.mouse.move(x + w * px, y + h * py, steps=8)",
        "    page.mouse.up()",
    ]


def _unsupported_lines(action: str, fmt: ExportFormat) -> list[str]:
    if fmt == ExportFormat.TYPESCRIPT:
        return [f"  // unsupported action: {action}"]
    return [f"    # unsupported action: {action}"]


def _step_lines(step: dict[str, Any], fmt: ExportFormat) -> list[str]:
    action = step.get("action")
    support = export_support_for_action(str(action or ""))
    if support == ExportSupport.UNSUPPORTED:
        return _unsupported_lines(str(action), fmt)

    lines: list[str] = []

    if action == "goto":
        url = str(step.get("url", ""))
        if fmt == ExportFormat.TYPESCRIPT:
            lines.append(f"  await page.goto({_ts_literal(url)});")
        else:
            lines.append(f"    page.goto({_py_literal(url)})")
        return lines

    if action == "hover":
        loc = _locator_expr(fmt, str(step.get("selector", "")))
        if fmt == ExportFormat.TYPESCRIPT:
            lines.append(f"  await {loc}.hover();")
        else:
            lines.append(f"    {loc}.hover()")
        return lines

    if action == "click":
        loc = _locator_expr(fmt, str(step.get("selector", "")))
        if fmt == ExportFormat.TYPESCRIPT:
            lines.append(f"  await {loc}.click();")
        else:
            lines.append(f"    {loc}.click()")
        return lines

    if action == "double_click":
        loc = _locator_expr(fmt, str(step.get("selector", "")))
        if fmt == ExportFormat.TYPESCRIPT:
            lines.append(f"  await {loc}.dblclick();")
        else:
            lines.append(f"    {loc}.dblclick()")
        return lines

    if action == "fill":
        loc = _locator_expr(fmt, str(step.get("selector", "")))
        value = str(step.get("value", ""))
        if fmt == ExportFormat.TYPESCRIPT:
            lines.append(f"  await {loc}.fill({_ts_literal(value)});")
        else:
            lines.append(f"    {loc}.fill({_py_literal(value)})")
        return lines

    if action == "fill_generated":
        generator = str(step.get("generator", ""))
        label = generator_gherkin_phrase(generator)
        env_name = _generator_env_name(generator)
        loc = _locator_expr(fmt, str(step.get("selector", "")))
        placeholder = f"REPLACE_{generator or 'generated'}"
        if fmt == ExportFormat.TYPESCRIPT:
            lines.append(f"  // partial export: generator {generator!r} ({label})")
            lines.append(
                f"  await {loc}.fill(process.env.{env_name} ?? {_ts_literal(placeholder)});"
            )
        else:
            lines.append(f"    # partial export: generator {generator!r} ({label})")
            lines.append(
                f"    {loc}.fill(os.environ.get({_py_literal(env_name)}, {_py_literal(placeholder)}))"
            )
        return lines

    if action == "select":
        loc = _locator_expr(fmt, str(step.get("selector", "")))
        value = str(step.get("value", ""))
        if fmt == ExportFormat.TYPESCRIPT:
            lines.append(f"  await {loc}.selectOption({_ts_literal(value)});")
        else:
            lines.append(f"    {loc}.select_option(value={_py_literal(value)})")
        return lines

    if action == "clear":
        loc = _locator_expr(fmt, str(step.get("selector", "")))
        if fmt == ExportFormat.TYPESCRIPT:
            lines.append(f"  await {loc}.clear();")
        else:
            lines.append(f"    {loc}.clear()")
        return lines

    if action == "check":
        loc = _locator_expr(fmt, str(step.get("selector", "")))
        if fmt == ExportFormat.TYPESCRIPT:
            lines.append(f"  await {loc}.check();")
        else:
            lines.append(f"    {loc}.check()")
        return lines

    if action == "uncheck":
        loc = _locator_expr(fmt, str(step.get("selector", "")))
        if fmt == ExportFormat.TYPESCRIPT:
            lines.append(f"  await {loc}.uncheck();")
        else:
            lines.append(f"    {loc}.uncheck()")
        return lines

    if action == "press":
        key = str(step.get("key", "Enter"))
        selector = str(step.get("selector", "") or "").strip()
        if selector:
            loc = _locator_expr(fmt, selector)
            if fmt == ExportFormat.TYPESCRIPT:
                lines.append(f"  await {loc}.press({_ts_literal(key)});")
            else:
                lines.append(f"    {loc}.press({_py_literal(key)})")
        elif fmt == ExportFormat.TYPESCRIPT:
            lines.append(f"  await page.keyboard.press({_ts_literal(key)});")
        else:
            lines.append(f"    page.keyboard.press({_py_literal(key)})")
        return lines

    if action == "upload":
        loc = _locator_expr(fmt, str(step.get("selector", "")))
        path = str(step.get("path", ""))
        if fmt == ExportFormat.TYPESCRIPT:
            lines.append(f"  await {loc}.setInputFiles({_ts_literal(path)});")
        else:
            lines.append(f"    {loc}.set_input_files({_py_literal(path)})")
        return lines

    if action == "scroll_to":
        loc = _locator_expr(fmt, str(step.get("selector", "")))
        if fmt == ExportFormat.TYPESCRIPT:
            lines.append(f"  await {loc}.scrollIntoViewIfNeeded();")
        else:
            lines.append(f"    {loc}.scroll_into_view_if_needed()")
        return lines

    if action == "draw_signature":
        selector = str(step.get("selector", ""))
        if fmt == ExportFormat.TYPESCRIPT:
            lines.extend(_signature_export_ts(selector))
        else:
            lines.extend(_signature_export_py(selector))
        return lines

    if action == "reload":
        if fmt == ExportFormat.TYPESCRIPT:
            lines.append("  await page.reload();")
        else:
            lines.append("    page.reload()")
        return lines

    if action == "go_back":
        if fmt == ExportFormat.TYPESCRIPT:
            lines.append("  await page.goBack();")
        else:
            lines.append("    page.go_back()")
        return lines

    if action == "close_browser":
        if fmt == ExportFormat.TYPESCRIPT:
            lines.append("  await page.context().browser()?.close();")
        else:
            lines.append("    page.context.browser.close()")
        return lines

    if action == "assert_visible":
        loc = _locator_expr(fmt, str(step.get("selector", "")))
        if fmt == ExportFormat.TYPESCRIPT:
            lines.append(f"  await expect({loc}).toBeVisible();")
        else:
            lines.append(f"    expect({loc}).to_be_visible()")
        return lines

    if action == "assert_hidden":
        loc = _locator_expr(fmt, str(step.get("selector", "")))
        if fmt == ExportFormat.TYPESCRIPT:
            lines.append(f"  await expect({loc}).toBeHidden();")
        else:
            lines.append(f"    expect({loc}).to_be_hidden()")
        return lines

    if action == "assert_text":
        loc = _locator_expr(fmt, str(step.get("selector", "")))
        value = str(step.get("value", ""))
        if fmt == ExportFormat.TYPESCRIPT:
            lines.append(f"  await expect({loc}).toContainText({_ts_literal(value)});")
        else:
            lines.append(f"    expect({loc}).to_contain_text({_py_literal(value)})")
        return lines

    if action == "assert_url":
        url = str(step.get("url", ""))
        if fmt == ExportFormat.TYPESCRIPT:
            lines.append(f"  await expect(page).toHaveURL({_ts_literal(url)});")
        else:
            lines.append(f"    expect(page).to_have_url({_py_literal(url)})")
        return lines

    if action == "wait":
        ms = max(0, int(step.get("ms", 1000)))
        if fmt == ExportFormat.TYPESCRIPT:
            lines.append(f"  await page.waitForTimeout({ms});")
        else:
            lines.append(f"    page.wait_for_timeout({ms})")
        return lines

    if action == "wait_for":
        loc = _locator_expr(fmt, str(step.get("selector", "")))
        if fmt == ExportFormat.TYPESCRIPT:
            lines.append(f"  await {loc}.waitFor({{ state: 'visible' }});")
        else:
            lines.append(f"    {loc}.wait_for(state='visible')")
        return lines

    if action == "wait_for_hidden":
        loc = _locator_expr(fmt, str(step.get("selector", "")))
        if fmt == ExportFormat.TYPESCRIPT:
            lines.append(f"  await {loc}.waitFor({{ state: 'hidden' }});")
        else:
            lines.append(f"    {loc}.wait_for(state='hidden')")
        return lines

    return _unsupported_lines(str(action), fmt)


def _export_notice_lines(analysis: ExportAnalysis, fmt: ExportFormat) -> list[str]:
    if not analysis.has_warnings:
        return []
    if fmt == ExportFormat.TYPESCRIPT:
        prefix = "//"
    else:
        prefix = "#"
    lines = [f"{prefix} Scenaria export notice:"]
    if analysis.partial:
        lines.append(f"{prefix} partial: {', '.join(analysis.partial)}")
    if analysis.unsupported:
        lines.append(f"{prefix} unsupported: {', '.join(analysis.unsupported)}")
    lines.append(prefix)
    return lines


def export_scenario_playwright(
    scenario: dict[str, Any],
    *,
    fmt: ExportFormat = ExportFormat.TYPESCRIPT,
) -> str:
    """Return Playwright test source for a scenario dict."""
    name = str(scenario.get("name", "") or "scenario")
    steps = normalize_steps(list(scenario.get("steps", [])))
    analysis = analyze_export(scenario)
    body_lines: list[str] = []
    for step in steps:
        body_lines.extend(_step_lines(step, fmt))

    notice = _export_notice_lines(analysis, fmt)
    needs_os = any(step.get("action") == "fill_generated" for step in steps)

    if fmt == ExportFormat.TYPESCRIPT:
        test_name = _safe_test_name(name)
        header = [
            "// Generated by Scenaria",
            *notice,
            "import { test, expect } from '@playwright/test';",
            "",
            f"test({_ts_literal(name)}, async ({{ page }}) => {{",
        ]
        footer = ["});", ""]
        if not body_lines:
            body_lines = ["  // no steps"]
        return "\n".join(header + body_lines + footer)

    test_name = _safe_test_name(name)
    header = [
        "# Generated by Scenaria",
        *notice,
    ]
    if needs_os:
        header.append("import os")
    header.extend(
        [
            "from playwright.sync_api import Page, expect",
            "",
            "",
            f"def test_{test_name}(page: Page) -> None:",
        ]
    )
    if not body_lines:
        body_lines = ["    pass"]
    return "\n".join(header + body_lines + ["", ""])
