"""Heuristics for scenario quality hints in the UI."""

from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Any, Literal

from app.gherkin_ru import STEP_INDENT
from app.selector_build import SELECTOR_ACTIONS, is_fragile_selector
from app.selector_resolve import hover_selector_from_container

PLAYWRIGHT_CHAIN_SEP = " >> "

ASSERT_ACTIONS = frozenset({"assert_text", "assert_visible", "assert_hidden", "assert_url"})
INTERACTIVE_AFTER_GOTO = frozenset({"click", "fill", "select", "check", "uncheck", "double_click", "upload"})


@dataclass(frozen=True)
class ScenarioHint:
    id: str
    title: str
    step_indices: tuple[int, ...]
    severity: Literal["info", "warning"]
    auto_fixable: bool


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


def apply_duplicate_goto_fix_at_index(steps: list[dict[str, Any]], index: int) -> list[dict[str, Any]] | None:
    """Remove a duplicate consecutive ``goto`` step."""
    if index <= 0 or index >= len(steps):
        return None
    if steps[index].get("action") != "goto" or steps[index - 1].get("action") != "goto":
        return None
    updated = list(steps)
    updated.pop(index)
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

        selector = str(step.get("selector", "") or "")
        if split_playwright_chain_selector(selector):
            suspicious.append(index)
            continue

        # Recorder attached menu context but the hover step is missing from the list.
        if str(step.get("hoverSelector", "") or "").strip():
            suspicious.append(index)

    return suspicious


def find_duplicate_goto_indices(steps: list[dict[str, Any]]) -> list[int]:
    indices: list[int] = []
    for index in range(1, len(steps)):
        if steps[index].get("action") == "goto" and steps[index - 1].get("action") == "goto":
            indices.append(index)
    return indices


def find_goto_no_wait_indices(steps: list[dict[str, Any]]) -> list[int]:
    indices: list[int] = []
    for index, step in enumerate(steps):
        if step.get("action") != "goto":
            continue
        if index + 1 >= len(steps):
            continue
        nxt = steps[index + 1]
        action = nxt.get("action")
        if action not in INTERACTIVE_AFTER_GOTO:
            continue
        if action in {"wait", "wait_for", "wait_for_hidden"}:
            continue
        indices.append(index)
    return indices


def find_fill_no_assert_indices(steps: list[dict[str, Any]]) -> list[int]:
    indices: list[int] = []
    for index, step in enumerate(steps):
        if step.get("action") not in {"fill", "fill_generated"}:
            continue
        window = steps[index + 1 : index + 4]
        if any(item.get("action") in ASSERT_ACTIONS for item in window):
            continue
        indices.append(index)
    return indices


def find_div_click_indices(steps: list[dict[str, Any]]) -> list[int]:
    indices: list[int] = []
    for index, step in enumerate(steps):
        if step.get("action") != "click":
            continue
        selector = str(step.get("selector", "") or "").lower()
        if "div:has-text" not in selector:
            continue
        if "button" in selector or " a:" in selector or selector.startswith("a:"):
            continue
        indices.append(index)
    return indices


def find_long_chain_indices(steps: list[dict[str, Any]]) -> list[int]:
    indices: list[int] = []
    for index, step in enumerate(steps):
        selector = str(step.get("selector", "") or "")
        if selector.count(PLAYWRIGHT_CHAIN_SEP) >= 2:
            indices.append(index)
    return indices


def find_fragile_selector_indices(steps: list[dict[str, Any]]) -> list[int]:
    indices: list[int] = []
    for index, step in enumerate(steps):
        if step.get("action") not in SELECTOR_ACTIONS:
            continue
        if step.get("fragile") is True:
            indices.append(index)
            continue
        selector = str(step.get("selector", "") or "")
        if selector and is_fragile_selector(selector):
            indices.append(index)
    return indices


def collect_all_hints(steps: list[dict[str, Any]]) -> list[ScenarioHint]:
    """Collect post-record quality hints for the scenario."""
    hints: list[ScenarioHint] = []

    for index in find_suspicious_menu_clicks(steps):
        hints.append(
            ScenarioHint(
                id="menu_hover",
                title="Клик по меню без предшествующего «навожу»",
                step_indices=(index,),
                severity="warning",
                auto_fixable=True,
            )
        )

    for index in find_duplicate_goto_indices(steps):
        hints.append(
            ScenarioHint(
                id="duplicate_goto",
                title="Два шага «открыт» подряд",
                step_indices=(index,),
                severity="warning",
                auto_fixable=True,
            )
        )

    for index in find_goto_no_wait_indices(steps):
        hints.append(
            ScenarioHint(
                id="goto_no_wait",
                title="После перехода сразу действие — добавьте «жду» или «жду появления»",
                step_indices=(index, index + 1),
                severity="info",
                auto_fixable=False,
            )
        )

    for index in find_fill_no_assert_indices(steps):
        hints.append(
            ScenarioHint(
                id="fill_no_assert",
                title="Ввод без проверки в следующих шагах",
                step_indices=(index,),
                severity="info",
                auto_fixable=False,
            )
        )

    for index in find_div_click_indices(steps):
        hints.append(
            ScenarioHint(
                id="div_click",
                title="Клик по div:has-text — уточните до button или a",
                step_indices=(index,),
                severity="info",
                auto_fixable=False,
            )
        )

    for index in find_long_chain_indices(steps):
        hints.append(
            ScenarioHint(
                id="long_chain",
                title="Длинная цепочка селекторов (>>) — возможно, стоит разбить",
                step_indices=(index,),
                severity="info",
                auto_fixable=False,
            )
        )

    for index in find_fragile_selector_indices(steps):
        hints.append(
            ScenarioHint(
                id="fragile_selector",
                title="Хрупкий CSS-селектор — добавьте data-testid или id",
                step_indices=(index,),
                severity="warning",
                auto_fixable=False,
            )
        )

    return hints


def apply_hint_fix(steps: list[dict[str, Any]], hint: ScenarioHint) -> list[dict[str, Any]] | None:
    """Apply an auto-fix for a supported hint."""
    if not hint.auto_fixable or not hint.step_indices:
        return None
    index = hint.step_indices[0]
    if hint.id == "menu_hover":
        return apply_menu_hover_fix_at_index(steps, index)
    if hint.id == "duplicate_goto":
        return apply_duplicate_goto_fix_at_index(steps, index)
    return None


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
