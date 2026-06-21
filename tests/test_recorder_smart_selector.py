"""Integration: recorder JS sends elementInfo for smart selectors."""

from __future__ import annotations

from playwright.sync_api import sync_playwright
import pytest

from app.paths import configure_playwright_browsers
from app.recorder_script import RECORDER_INIT_SCRIPT
from app.selector_build import apply_smart_selector_to_step

pytestmark = pytest.mark.integration

CHECKOUT_HTML = """
<!doctype html>
<html>
  <body>
    <button data-testid="checkout" type="button">Оформить</button>
  </body>
</html>
"""


def test_recorded_click_prefers_testid_after_smart_selector() -> None:
    configure_playwright_browsers()
    collected: list[dict] = []

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_context().new_page()
        page.expose_function("recordStep", lambda step: collected.append(dict(step)))
        page.set_content(CHECKOUT_HTML)
        page.evaluate(RECORDER_INIT_SCRIPT)
        page.click("button")
        page.wait_for_timeout(200)
        browser.close()

    assert collected
    step = apply_smart_selector_to_step(collected[0])
    assert step["selector"] == '[data-testid="checkout"]'
    assert step["selectorStrategy"] == "testid"
