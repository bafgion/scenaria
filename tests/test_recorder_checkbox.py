"""Checkbox recording and normalization."""

from __future__ import annotations

import pytest
from playwright.sync_api import sync_playwright

from app.paths import configure_playwright_browsers
from app.recorder_script import RECORDER_INIT_SCRIPT
from app.steps import apply_coalesced_step, normalize_steps

pytestmark = pytest.mark.integration


CHECKBOX_HTML = """
<!doctype html>
<html>
  <body>
    <label id="agree-label">
      Согласен с условиями Политики конфиденциальности
      <input type="checkbox" name="privacy">
    </label>
  </body>
</html>
"""


CHECKBOX_SIBLING_HTML = """
<!doctype html>
<html>
  <body>
    <div>
      <div>
        <div>
          <label><input type="checkbox"></label>
          <span>Подтверждаю согласие на обработку персональных данных</span>
        </div>
      </div>
    </div>
  </body>
</html>
"""


def _record_steps_on_html(html: str, selector: str) -> list[dict]:
    configure_playwright_browsers()
    collected: list[dict] = []

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_context().new_page()
        page.expose_function("recordStep", lambda step: collected.append(dict(step)))
        page.set_content(html)
        page.evaluate(RECORDER_INIT_SCRIPT)
        page.click(selector)
        page.wait_for_timeout(500)
        browser.close()

    return collected


def _record_steps_on_click(selector: str) -> list[dict]:
    return _record_steps_on_html(CHECKBOX_HTML, selector)


def test_checkbox_click_on_label_records_single_check() -> None:
    steps = _record_steps_on_click("#agree-label")
    assert len(steps) == 1
    assert steps[0]["action"] == "check"
    assert steps[0]["selector"] in {
        'label:has-text("Согласен с условиями Политики конфиденциальности")',
        'input[type="checkbox"][name="privacy"]',
    }


def test_checkbox_click_on_input_records_single_check() -> None:
    steps = _record_steps_on_click('input[name="privacy"]')
    assert len(steps) == 1
    assert steps[0]["action"] == "check"
    assert "privacy" in steps[0]["selector"] or "Согласен" in steps[0]["selector"]


def test_normalize_legacy_checkbox_noise() -> None:
    steps = [
        {"action": "click", "selector": "div > label:nth-of-type(3)"},
        {"action": "click", "selector": "div > label:nth-of-type(3) > input"},
        {
            "action": "fill",
            "selector": "div > label:nth-of-type(3) > input",
            "value": "on",
            "inputType": "checkbox",
        },
    ]
    out = normalize_steps(steps)
    assert out == [
        {
            "action": "check",
            "selector": "div > label:nth-of-type(3) > input",
        }
    ]


def test_apply_coalesced_step_replaces_click_with_check() -> None:
    steps = [{"action": "click", "selector": "label:has-text(\"Согласен\")"}]
    updated, emitted = apply_coalesced_step(
        steps,
        {"action": "check", "selector": 'label:has-text("Согласен")'},
    )
    assert updated == [{"action": "check", "selector": 'label:has-text("Согласен")'}]
    assert emitted is not None


def test_checkbox_with_sibling_text_uses_label_has_text() -> None:
    steps = _record_steps_on_html(CHECKBOX_SIBLING_HTML, "input[type='checkbox']")
    assert len(steps) == 1
    assert steps[0]["action"] == "check"
    assert steps[0]["selector"].startswith('label:has-text("')
    assert "согласие" in steps[0]["selector"].lower()


def test_normalize_upgrades_fragile_checkbox_selector_from_text() -> None:
    steps = normalize_steps(
        [
            {
                "action": "check",
                "selector": "div:nth-of-type(3) > div > div > label:nth-of-type(3) > input",
                "text": "Подтверждаю согласие на обработку персональных данных",
            }
        ]
    )
    assert steps[0]["selector"].startswith('label:has-text("')
    assert "согласие" in steps[0]["selector"].lower()
