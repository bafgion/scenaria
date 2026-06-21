"""Playback resolves ambiguous contextual click selectors."""

from __future__ import annotations

from playwright.sync_api import sync_playwright
import pytest

from app.paths import configure_playwright_browsers
from app.selector_resolve import (
    hover_selector_from_container,
    resolve_chained_locator,
    resolve_hover_locator,
)

pytestmark = pytest.mark.integration

CONTRACT_TYPE_HTML = """
<!doctype html>
<html>
  <body>
    <div class="cards">
      <div class="card" id="card-sz">
        <h3>Договор с самозанятым</h3>
        <button type="button" class="btn">Выбрать</button>
      </div>
      <div class="card" id="card-no-contract">
        <h3>Без договора</h3>
        <p>Сотрудничество за бонусы</p>
        <button type="button" class="btn">Выбрать</button>
      </div>
    </div>
    <script>
      document.querySelectorAll('button').forEach((btn) => {
        btn.addEventListener('click', () => {
          window.lastCard = btn.closest('.card')?.id || '';
        });
      });
    </script>
  </body>
</html>
"""


def test_resolve_chained_locator_clicks_innermost_card() -> None:
    configure_playwright_browsers()
    selector = 'div:has-text("Без договора") >> button:has-text("Выбрать")'

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_context().new_page()
        page.set_content(CONTRACT_TYPE_HTML)

        resolve_chained_locator(page, selector).click()
        assert page.evaluate("() => window.lastCard") == "card-no-contract"

        page.evaluate("() => { window.lastCard = ''; }")
        page.locator(selector).first.click()
        assert page.evaluate("() => window.lastCard") == "card-sz"

        browser.close()


MENU_HOVER_HTML = """
<!doctype html>
<html>
  <body>
    <div class="nav">
      <div class="category">
        <a href="#" class="cat-link">Вязаный трикотаж</a>
        <div class="submenu">
          <button type="button">Толстовки</button>
        </div>
      </div>
    </div>
    <style>
      .category .submenu { display: none; }
      .category > a:hover + .submenu { display: block; }
    </style>
  </body>
</html>
"""


def test_hover_selector_from_container_prefers_link() -> None:
    container = 'div:has-text("Категория")'
    assert hover_selector_from_container(container) == (
        'div:has-text("Категория") >> a:has-text("Категория")'
    )


def test_resolve_hover_locator_opens_submenu_via_link() -> None:
    configure_playwright_browsers()
    selector = 'div:has-text("Вязаный трикотаж")'

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_context().new_page()
        page.set_content(MENU_HOVER_HTML)

        resolve_hover_locator(page, selector).hover()
        page.wait_for_timeout(100)
        assert page.locator('button:has-text("Толстовки")').is_visible()

        browser.close()
