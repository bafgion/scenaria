"""Resolve chained Playwright selectors to the most specific matching element."""

from __future__ import annotations

import re

from playwright.sync_api import Locator, Page

_HAS_TEXT = re.compile(r':has-text\("((?:[^"\\]|\\.)*)"\)')
_CONTAINER_TAGS = frozenset({"div", "section", "span", "li", "nav", "ul"})


def _first_has_text(selector: str) -> str | None:
    match = _HAS_TEXT.search(selector)
    return match.group(1) if match else None


def _root_tag(selector: str) -> str:
    return selector.split(":")[0].split(".")[0].split("#")[0].strip().lower()


def hover_selector_from_container(container_part: str) -> str:
    """Prefer an interactive child when a menu container is used for hover."""
    text = _first_has_text(container_part)
    root = _root_tag(container_part)
    if root in _CONTAINER_TAGS:
        if text:
            return f'{container_part} >> a:has-text("{text}")'
        return f"{container_part} >> a"
    return container_part


def hover_locator_candidates(selector: str) -> list[str]:
    """Ordered hover targets: link/button inside container, then global matches."""
    selector = selector.strip()
    if not selector:
        return []

    seen: set[str] = set()
    candidates: list[str] = []

    def add(candidate: str) -> None:
        candidate = candidate.strip()
        if candidate and candidate not in seen:
            seen.add(candidate)
            candidates.append(candidate)

    text = _first_has_text(selector)
    root = _root_tag(selector)

    if text:
        add(f'a:has-text("{text}")')
        add(f'button:has-text("{text}")')
        add(f'nav a:has-text("{text}")')
        add(f'nav button:has-text("{text}")')
        add(f'[role="menuitem"]:has-text("{text}")')

    if root in _CONTAINER_TAGS or ":has-text(" in selector:
        if text:
            add(f'{selector} >> a:has-text("{text}")')
            add(f'{selector} >> button:has-text("{text}")')
        add(f"{selector} >> a")
        add(f"{selector} >> button")

    add(selector)
    return candidates


def resolve_hover_locator(page: Page, selector: str) -> Locator:
    """Pick the first visible element suitable for opening hover menus."""
    for candidate in hover_locator_candidates(selector):
        locator = page.locator(candidate).first
        try:
            if locator.count() == 0:
                continue
            locator.wait_for(state="visible", timeout=1500)
            return locator
        except Exception:
            continue
    return page.locator(selector).first


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
