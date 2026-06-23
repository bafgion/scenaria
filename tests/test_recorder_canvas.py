"""Canvas / signature recording."""

from __future__ import annotations

import pytest
from playwright.sync_api import sync_playwright

from app.paths import configure_playwright_browsers
from app.recorder_script import RECORDER_INIT_SCRIPT
from app.steps import normalize_steps

pytestmark = pytest.mark.integration


SIGNATURE_HTML = """
<!doctype html>
<html>
  <body>
    <div>
      <div>
        <div>
          <div>Поставьте подпись в поле ниже</div>
          <div><canvas aria-label="Поле подписи"></canvas></div>
        </div>
      </div>
    </div>
  </body>
</html>
"""


def _record_canvas_click() -> list[dict]:
    configure_playwright_browsers()
    collected: list[dict] = []

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_context().new_page()
        page.expose_function("recordStep", lambda step: collected.append(dict(step)))
        page.set_content(SIGNATURE_HTML)
        page.evaluate(RECORDER_INIT_SCRIPT)
        page.click("canvas")
        page.wait_for_timeout(300)
        browser.close()

    return collected


def test_canvas_click_records_draw_signature() -> None:
    steps = _record_canvas_click()
    assert len(steps) == 1
    assert steps[0]["action"] == "draw_signature"
    assert "canvas" in steps[0]["selector"]
    assert "nth-of-type" not in steps[0]["selector"]


def test_normalize_fragile_canvas_click() -> None:
    steps = normalize_steps(
        [
            {
                "action": "click",
                "selector": "div:nth-of-type(3) > div > div > div > canvas",
                "text": "Поставьте подпись",
            }
        ]
    )
    assert steps[0]["action"] == "draw_signature"
    assert steps[0]["selector"].endswith("canvas")
    assert "nth-of-type" not in steps[0]["selector"]
    assert steps[0]["text"] == "Поставьте подпись"
