"""Keyboard and file-upload recording."""

from __future__ import annotations

from pathlib import Path

from playwright.sync_api import sync_playwright
import pytest

from app.paths import configure_playwright_browsers
from app.recorder_script import RECORDER_INIT_SCRIPT
from app.steps import apply_coalesced_step, normalize_steps

pytestmark = pytest.mark.integration

FORM_HTML = """
<!doctype html>
<html>
  <body>
    <label>
      Комментарий
      <textarea id="comment"></textarea>
    </label>
    <label>
      Документ
      <input type="file" id="doc">
    </label>
  </body>
</html>
"""


def _record_steps(action_fn) -> list[dict]:
    configure_playwright_browsers()
    collected: list[dict] = []

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_context().new_page()
        page.expose_function("recordStep", lambda step: collected.append(dict(step)))
        page.set_content(FORM_HTML)
        page.evaluate(RECORDER_INIT_SCRIPT)
        action_fn(page)
        page.wait_for_timeout(500)
        browser.close()

    return collected


def test_records_enter_press_on_textarea() -> None:
    steps = _record_steps(
        lambda page: (
            page.fill("#comment", "hello"),
            page.press("#comment", "Enter"),
        )
    )
    assert any(step.get("action") == "fill" for step in steps)
    press_steps = [step for step in steps if step.get("action") == "press"]
    assert len(press_steps) == 1
    assert press_steps[0]["key"] == "Enter"
    assert press_steps[0]["selector"]


def test_records_file_upload_with_placeholder_path() -> None:
    sample = Path(__file__).with_name("sample_upload.txt")
    sample.write_text("demo", encoding="utf-8")
    try:
        steps = _record_steps(lambda page: page.set_input_files("#doc", str(sample)))
    finally:
        sample.unlink(missing_ok=True)

    upload_steps = [step for step in steps if step.get("action") == "upload"]
    assert len(upload_steps) == 1
    assert upload_steps[0]["selector"]
    assert upload_steps[0]["path"] == "<sample_upload.txt>"


def test_coalesce_skips_tab_after_fill_on_same_field() -> None:
    steps = [{"action": "fill", "selector": "#x", "value": "a"}]
    updated, emitted = apply_coalesced_step(
        steps,
        {"action": "press", "key": "Tab", "selector": "#x"},
    )
    assert emitted is None
    assert updated == steps

    updated, emitted = apply_coalesced_step(
        steps,
        {"action": "press", "key": "Enter", "selector": "#x"},
    )
    assert emitted is not None
    assert emitted["key"] == "Enter"


def test_normalize_keeps_upload_step() -> None:
    steps = normalize_steps(
        [
            {
                "action": "upload",
                "selector": 'input[type="file"]',
                "path": "<report.pdf>",
            }
        ]
    )
    assert len(steps) == 1
    assert steps[0]["action"] == "upload"
