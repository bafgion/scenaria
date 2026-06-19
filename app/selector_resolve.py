"""Resolve chained Playwright selectors to the most specific matching element."""

from __future__ import annotations

from playwright.sync_api import Locator, Page


def resolve_chained_locator(page: Page, selector: str) -> Locator:
    """
    For ``container >> target`` selectors, pick the smallest container that
    contains exactly one matching target (innermost card/panel).
    """
    if " >> " not in selector:
        return page.locator(selector)

    container_sel, target_sel = selector.split(" >> ", 1)
    container_sel = container_sel.strip()
    target_sel = target_sel.strip()
    if not container_sel or not target_sel:
        return page.locator(selector)

    containers = page.locator(container_sel)
    try:
        count = containers.count()
    except Exception:
        return page.locator(selector)

    best_target: Locator | None = None
    best_area: float | None = None

    for index in range(count):
        container = containers.nth(index)
        try:
            targets = container.locator(target_sel)
            if targets.count() != 1:
                continue
            box = container.bounding_box(timeout=2000)
        except Exception:
            continue
        if not box:
            continue
        area = float(box["width"]) * float(box["height"])
        if best_area is None or area < best_area:
            best_area = area
            best_target = targets.first

    if best_target is not None:
        return best_target
    return page.locator(selector)
