"""Export recorder scenarios to Playwright test scripts."""

from __future__ import annotations

import json
import re
from enum import Enum
from typing import Any

from app.steps import normalize_steps


class ExportFormat(str, Enum):
    TYPESCRIPT = "typescript"
    PYTHON = "python"


def _ts_literal(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def _py_literal(value: str) -> str:
    return repr(value)


def _safe_test_name(name: str) -> str:
    cleaned = re.sub(r"[^\w\-]+", "_", name.strip(), flags=re.UNICODE).strip("_")
    return cleaned or "scenario"


def _locator_expr(fmt: ExportFormat, selector: str) -> str:
    if fmt == ExportFormat.TYPESCRIPT:
        return f"page.locator({_ts_literal(selector)}).first()"
    return f"page.locator({_py_literal(selector)}).first()"


def _signature_export_ts(selector: str) -> list[str]:
    loc = _locator_expr(ExportFormat.TYPESCRIPT, selector)
    return [
        f"  {{",
        f"    const box = await {loc}.boundingBox();",
        f"    if (!box) throw new Error('Canvas not found');",
        f"    const {{ x, y, width: w, height: h }} = box;",
        f"    await page.mouse.move(x + w * 0.12, y + h * 0.55);",
        f"    await page.mouse.down();",
        f"    for (const [px, py] of [[0.28, 0.38], [0.42, 0.62], [0.58, 0.35], [0.72, 0.58], [0.86, 0.42]]) {{",
        f"      await page.mouse.move(x + w * px, y + h * py, {{ steps: 8 }});",
        f"    }}",
        f"    await page.mouse.up();",
        f"  }}",
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


def _step_lines(step: dict[str, Any], fmt: ExportFormat) -> list[str]:
    action = step.get("action")
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
        from app.run_variables import generator_gherkin_phrase

        loc = _locator_expr(fmt, str(step.get("selector", "")))
        generator = str(step.get("generator", ""))
        label = generator_gherkin_phrase(generator)
        if fmt == ExportFormat.TYPESCRIPT:
            lines.append(f"  // TODO: generate {label}")
            lines.append(f"  await {loc}.fill('generated-{generator}');")
        else:
            lines.append(f"    # TODO: generate {label}")
            lines.append(f"    {loc}.fill('generated-{generator}')")
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

    if fmt == ExportFormat.TYPESCRIPT:
        lines.append(f"  // unsupported action: {action}")
    else:
        lines.append(f"    # unsupported action: {action}")
    return lines


def export_scenario_playwright(
    scenario: dict[str, Any],
    *,
    fmt: ExportFormat = ExportFormat.TYPESCRIPT,
) -> str:
    """Return Playwright test source for a scenario dict."""
    name = str(scenario.get("name", "") or "scenario")
    steps = normalize_steps(list(scenario.get("steps", [])))
    body_lines: list[str] = []
    for step in steps:
        body_lines.extend(_step_lines(step, fmt))

    if fmt == ExportFormat.TYPESCRIPT:
        test_name = _safe_test_name(name)
        header = [
            "// Generated by Scenaria",
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
        "from playwright.sync_api import Page, expect",
        "",
        "",
        f"def test_{test_name}(page: Page) -> None:",
    ]
    if not body_lines:
        body_lines = ["    pass"]
    return "\n".join(header + body_lines + ["", ""])
