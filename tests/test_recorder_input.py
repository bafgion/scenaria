"""Text input recording selectors."""

from __future__ import annotations

from playwright.sync_api import sync_playwright
import pytest

from app.paths import configure_playwright_browsers
from app.recorder_script import RECORDER_INIT_SCRIPT
from app.steps import normalize_steps

pytestmark = pytest.mark.integration


NESTED_LABEL_FORM_HTML = """
<!doctype html>
<html>
  <body>
    <div>
      <div>
        <label>
          <div>E-mail</div>
          <div><input type="email"></div>
        </label>
        <label>
          <div>Пароль</div>
          <div><input type="password"></div>
        </label>
        <label>
          <div>Имя</div>
          <div><input type="text"></div>
        </label>
      </div>
    </div>
  </body>
</html>
"""


def _record_fill(selector: str, value: str) -> list[dict]:
    configure_playwright_browsers()
    collected: list[dict] = []

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_context().new_page()
        page.expose_function("recordStep", lambda step: collected.append(dict(step)))
        page.set_content(NESTED_LABEL_FORM_HTML)
        page.evaluate(RECORDER_INIT_SCRIPT)
        page.click(selector)
        page.fill(selector, value)
        page.wait_for_timeout(500)
        browser.close()

    return collected


def test_nested_label_email_records_label_has_text_without_click() -> None:
    steps = _record_fill("label:nth-of-type(1) input", "user@test.com")
    assert len(steps) == 1
    assert steps[0]["action"] == "fill"
    assert steps[0]["selector"].startswith('label:has-text("')
    assert "mail" in steps[0]["selector"].lower()


def test_normalize_drops_click_before_fill_and_upgrades_selector() -> None:
    steps = normalize_steps(
        [
            {"action": "click", "selector": "div > label:nth-of-type(1) > div:nth-of-type(2) > input"},
            {
                "action": "fill",
                "selector": "div > label:nth-of-type(1) > div:nth-of-type(2) > input",
                "value": "Иван",
                "text": "Имя",
            },
        ]
    )
    assert len(steps) == 1
    assert steps[0]["action"] == "fill"
    assert steps[0]["selector"].startswith('label:has-text("Имя')
