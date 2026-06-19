"""Playback resolves ambiguous contextual click selectors."""

from __future__ import annotations

from playwright.sync_api import sync_playwright

from app.paths import configure_playwright_browsers
from app.selector_resolve import resolve_chained_locator

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
