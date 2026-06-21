"""Radio button recording."""

from __future__ import annotations

from playwright.sync_api import sync_playwright
import pytest

from app.paths import configure_playwright_browsers
from app.recorder_script import RECORDER_INIT_SCRIPT

pytestmark = pytest.mark.integration


RADIO_HTML = """
<!doctype html>
<html>
  <body>
    <fieldset>
      <legend>Способ доставки</legend>
      <label>
        <input type="radio" name="delivery" value="pickup">
        Самовывоз
      </label>
      <label>
        <input type="radio" name="delivery" value="courier">
        Курьер
      </label>
    </fieldset>
  </body>
</html>
"""


def _record_radio_click(selector: str) -> list[dict]:
    configure_playwright_browsers()
    collected: list[dict] = []

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_context().new_page()
        page.expose_function("recordStep", lambda step: collected.append(dict(step)))
        page.set_content(RADIO_HTML)
        page.evaluate(RECORDER_INIT_SCRIPT)
        page.click(selector)
        page.wait_for_timeout(300)
        browser.close()

    return collected


def test_radio_click_records_check_step() -> None:
    steps = _record_radio_click('input[value="courier"]')
    assert len(steps) == 1
    assert steps[0]["action"] == "check"
    assert "courier" in steps[0]["selector"] or "Курьер" in steps[0].get("text", "")
