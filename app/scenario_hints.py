"""Heuristics for scenario quality hints in the UI."""

from __future__ import annotations

import copy
from typing import Any

from app.gherkin_ru import STEP_INDENT
from app.selector_resolve import hover_selector_from_container

PLAYWRIGHT_CHAIN_SEP = " >> "


def split_playwright_chain_selector(selector: str) -> tuple[str, str] | None:
    """Split ``container >> target`` menu selectors into hover and click parts."""
    text = selector.strip()
    if PLAYWRIGHT_CHAIN_SEP not in text:
        return None
    parts = [part.strip() for part in text.split(PLAYWRIGHT_CHAIN_SEP) if part.strip()]
    if len(parts) < 2:
        return None
    return parts[0], parts[-1]


def propose_menu_hover_fix(step: dict[str, Any]) -> tuple[str, str] | None:
    """Return (hover_selector, click_selector) when a click step can be split."""
    if step.get("action") != "click":
        return None
    click_selector = str(step.get("selector", "") or "").strip()
    if not click_selector:
        return None

    hover_selector = str(step.get("hoverSelector", "") or "").strip()
    split = split_playwright_chain_selector(click_selector)
    if split:
        chain_hover, chain_click = split
        resolved_hover = hover_selector or hover_selector_from_container(chain_hover)
        return resolved_hover, chain_click
    if hover_selector:
        return hover_selector, click_selector
    return None


def apply_menu_hover_fix_at_index(steps: list[dict[str, Any]], index: int) -> list[dict[str, Any]] | None:
    """Replace a click step with hover + click when menu selectors are known."""
    if index < 0 or index >= len(steps):
        return None
    step = steps[index]
    proposal = propose_menu_hover_fix(step)
    if proposal is None:
        return None

    hover_selector, click_selector = proposal
    prev = steps[index - 1] if index > 0 else None
    if (
        prev
        and prev.get("action") == "hover"
        and str(prev.get("selector", "") or "").strip() == hover_selector
        and str(step.get("selector", "") or "").strip() == click_selector
    ):
        return None

    hover_step: dict[str, Any] = {"action": "hover", "selector": hover_selector}
    hover_text = str(step.get("hoverText", "") or "").strip()
    if hover_text:
        hover_step["text"] = hover_text

    click_step = copy.deepcopy(step)
    click_step["action"] = "click"
    click_step["selector"] = click_selector
    click_step["hoverSelector"] = hover_selector
    if hover_text:
        click_step["hoverText"] = hover_text

    updated = list(steps)
    updated[index] = hover_step
    updated.insert(index + 1, click_step)
    return updated


def find_suspicious_menu_clicks(steps: list[dict[str, Any]]) -> list[int]:
    """Return 0-based indices of click steps that may need a preceding hover."""
    suspicious: list[int] = []
    for index, step in enumerate(steps):
        if step.get("action") != "click":
            continue
        prev = steps[index - 1] if index > 0 else None
        if prev and prev.get("action") == "hover":
            continue
        if step.get("hoverSelector"):
            continue
        selector = str(step.get("selector", "") or "")
        if split_playwright_chain_selector(selector):
            suspicious.append(index)
            continue
        text = str(step.get("text", "") or "")
        haystack = f"{selector} {text}".lower()
        if any(
            token in haystack
            for token in ("nav", "menu", "has-text", "role=menu", "dropdown", "submenu")
        ):
            suspicious.append(index)
    return suspicious


def gherkin_template_text(*, url: str = "https://site.com", scenario_name: str = "Сценарий") -> str:
    safe_url = url.strip() or "https://site.com"
    return (
        "Функционал: UI сценарий\n"
        f"Сценарий: {scenario_name}\n"
        f"{STEP_INDENT}Допустим открыт \"{safe_url}\"\n"
        f'{STEP_INDENT}И нажимаю "button.submit"'
    )


def hover_menu_gherkin_example() -> str:
    return (
        f'{STEP_INDENT}И навожу "nav a:has-text(\\"Услуги\\")"\n'
        f'{STEP_INDENT}И нажимаю "a:has-text(\\"Консультации\\")"'
    )
