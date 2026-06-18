"""Draw a simple stroke on signature canvas elements (ПЭП widgets)."""

from __future__ import annotations

from playwright.sync_api import Page


def draw_signature_on_canvas(page: Page, selector: str) -> None:
    """Simulate a handwritten stroke inside a canvas (or canvas-like) element."""
    locator = page.locator(selector).first
    locator.wait_for(state="visible", timeout=15_000)
    locator.scroll_into_view_if_needed()
    box = locator.bounding_box()
    if not box:
        raise RuntimeError(f"Не удалось получить область элемента: {selector}")

    x, y, w, h = box["x"], box["y"], box["width"], box["height"]
    if w < 8 or h < 8:
        raise RuntimeError(f"Слишком маленькая область подписи: {selector}")

    start_x = x + w * 0.12
    start_y = y + h * 0.55
    page.mouse.move(start_x, start_y)
    page.mouse.down()

    stroke = (
        (x + w * 0.28, y + h * 0.38),
        (x + w * 0.42, y + h * 0.62),
        (x + w * 0.58, y + h * 0.35),
        (x + w * 0.72, y + h * 0.58),
        (x + w * 0.86, y + h * 0.42),
    )
    for px, py in stroke:
        page.mouse.move(px, py, steps=8)

    page.mouse.up()
    page.wait_for_timeout(180)
