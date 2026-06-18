"""Stable selectors for clicks on text inside buttons."""

from __future__ import annotations

from playwright.sync_api import sync_playwright
import pytest

from app.paths import configure_playwright_browsers
from app.selector_heuristics import SELECTOR_HEURISTICS_JS
from app.steps import normalize_steps

BUTTON_MENU_HTML = """
<!doctype html>
<html>
  <body>
    <div class="cards">
      <div class="card">
        <button type="button" class="btn"><span>Выбрать</span></button>
      </div>
      <div class="card">
        <div class="btn" role="button">
          <span>Без</span><span>НДС</span>
        </div>
      </div>
      <div class="card">
        <div class="btn option"><div>5%</div></div>
      </div>
    </div>
  </body>
</html>
"""

SELECTOR_PROBE_FN = (
    """
(selector) => {
"""
    + SELECTOR_HEURISTICS_JS
    + """
  const el = document.querySelector(selector);
  if (!el) return null;
  return buildSelector(el);
}
"""
)


def test_normalize_upgrades_fragile_button_click() -> None:
    steps = normalize_steps(
        [
            {
                "action": "click",
                "selector": "div > div > span:nth-of-type(1)",
                "text": "Выбрать",
            }
        ]
    )
    assert steps[0]["selector"] == 'button:has-text("Выбрать")'


def test_normalize_upgrades_fragile_multiline_button_text() -> None:
    steps = normalize_steps(
        [
            {
                "action": "click",
                "selector": "div.card > div > span:nth-of-type(2)",
                "text": "Без НДС",
            }
        ]
    )
    assert steps[0]["selector"] == 'button:has-text("Без НДС")'


def test_selector_probe_span_inside_button() -> None:
    configure_playwright_browsers()
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_context().new_page()
        page.set_content(BUTTON_MENU_HTML)
        assert page.evaluate(SELECTOR_PROBE_FN, "button span") == 'button:has-text("Выбрать")'
        assert (
            page.evaluate(SELECTOR_PROBE_FN, ".card:nth-of-type(2) span:nth-of-type(1)")
            == 'button:has-text("БезНДС")'
        )
        assert page.evaluate(SELECTOR_PROBE_FN, ".option div") == 'div:has-text("5%")'
        browser.close()
