"""Selector picker returns stable selectors for nested label forms."""

from __future__ import annotations

from playwright.sync_api import sync_playwright

from app.paths import configure_playwright_browsers
from app.picker_script import PICKER_INSTALL_SCRIPT

NESTED_LABEL_FORM_HTML = """
<!doctype html>
<html>
  <body>
    <div>
      <div>
        <label>
          <div>ИНН</div>
          <div><input type="text"></div>
        </label>
        <label>
          <div>E-mail</div>
          <div><input type="email"></div>
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


def _pick_at(selector: str) -> str | None:
    configure_playwright_browsers()
    picked: list[str] = []

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_context().new_page()
        page.expose_function("pickSelectorDone", lambda value: picked.append(str(value)))
        page.expose_function("pickSelectorCancel", lambda: picked.append(""))
        page.set_content(NESTED_LABEL_FORM_HTML)
        page.evaluate(PICKER_INSTALL_SCRIPT)
        box = page.locator(selector).bounding_box()
        assert box is not None
        page.mouse.click(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
        page.wait_for_timeout(200)
        browser.close()

    return picked[0] if picked else None


def test_picker_nested_label_input_returns_label_has_text() -> None:
    selector = _pick_at("label:nth-of-type(1) input")
    assert selector is not None
    assert selector.startswith('label:has-text("')
    assert "ИНН" in selector


def test_picker_label_caption_div_returns_input_label_has_text() -> None:
    selector = _pick_at("label:nth-of-type(2) > div:first-child")
    assert selector is not None
    assert selector.startswith('label:has-text("')
    assert "mail" in selector.lower()


def test_picker_short_caption_returns_label_has_text() -> None:
    selector = _pick_at("label:nth-of-type(3) input")
    assert selector is not None
    assert 'label:has-text("Имя")' in selector
