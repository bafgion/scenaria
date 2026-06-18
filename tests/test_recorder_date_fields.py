"""Date fields with identical placeholders should get distinct selectors."""

from __future__ import annotations

from playwright.sync_api import sync_playwright

from app.paths import configure_playwright_browsers
from app.recorder_script import RECORDER_INIT_SCRIPT
from app.steps import normalize_steps

PASSPORT_FORM_HTML = """
<!doctype html>
<html>
  <body>
    <div>
      <div>
        <div>Дата рождения *</div>
        <input type="text" placeholder="ДД.ММ.ГГГГ">
      </div>
      <div>
        <div>Дата выдачи паспорта *</div>
        <input type="text" placeholder="ДД.ММ.ГГГГ">
      </div>
    </div>
  </body>
</html>
"""


def _record_fills() -> list[dict]:
    configure_playwright_browsers()
    collected: list[dict] = []

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_context().new_page()
        page.expose_function("recordStep", lambda step: collected.append(dict(step)))
        page.set_content(PASSPORT_FORM_HTML)
        page.evaluate(RECORDER_INIT_SCRIPT)
        page.locator("input").nth(0).fill("01.12.2000")
        page.locator("input").nth(1).fill("15.06.2020")
        page.wait_for_timeout(500)
        browser.close()

    return collected


def test_duplicate_date_placeholders_record_distinct_label_selectors() -> None:
    steps = normalize_steps(_record_fills())
    fills = [step for step in steps if step["action"] == "fill"]
    assert len(fills) == 2
    selectors = {step["selector"] for step in fills}
    assert len(selectors) == 2
    joined = " ".join(selectors).lower()
    assert "рожд" in joined
    assert "выдач" in joined


def test_normalize_upgrades_generic_placeholder_using_field_text() -> None:
    steps = normalize_steps(
        [
            {
                "action": "fill",
                "selector": 'input[placeholder="ДД.ММ.ГГГГ"]',
                "value": "01.12.2000",
                "text": "Дата рождения",
            },
            {
                "action": "fill",
                "selector": 'input[placeholder="ДД.ММ.ГГГГ"]',
                "value": "15.06.2020",
                "text": "Дата выдачи паспорта",
            },
        ]
    )
    assert len(steps) == 2
    assert steps[0]["selector"].startswith('label:has-text("Дата рожд')
    assert steps[1]["selector"].startswith('label:has-text("Дата выдач')
