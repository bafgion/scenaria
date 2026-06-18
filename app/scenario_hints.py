"""Heuristics for scenario quality hints in the UI."""

from __future__ import annotations

from typing import Any

from app.gherkin_ru import STEP_INDENT


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
