"""Smart selector strategy for recorded steps."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

DEFAULT_SELECTOR_PRIORITY = ["testid", "id", "name_aria", "text", "chain", "css"]

SELECTOR_STRATEGY_LABELS: dict[str, str] = {
    "testid": "data-testid",
    "id": "id",
    "name_aria": "name / aria-label",
    "text": "текст (has-text)",
    "chain": "цепочка (>>)",
    "css": "CSS (хрупкий)",
}

ALL_SELECTOR_STRATEGIES = list(DEFAULT_SELECTOR_PRIORITY)

def normalize_selector_priority(raw: object) -> list[str]:
    """Return a valid strategy order (unknown keys dropped, missing defaults appended)."""
    if not isinstance(raw, list):
        return list(DEFAULT_SELECTOR_PRIORITY)
    seen: set[str] = set()
    result: list[str] = []
    for item in raw:
        key = str(item).strip()
        if key in ALL_SELECTOR_STRATEGIES and key not in seen:
            result.append(key)
            seen.add(key)
    for key in ALL_SELECTOR_STRATEGIES:
        if key not in seen:
            result.append(key)
    return result


def strategy_label(strategy: str) -> str:
    return SELECTOR_STRATEGY_LABELS.get(strategy, strategy)


SELECTOR_ACTIONS = frozenset(
    {
        "click",
        "fill",
        "select",
        "check",
        "uncheck",
        "hover",
        "double_click",
        "upload",
        "press",
        "draw_signature",
    }
)

_AUTO_ID_PREFIXES = ("ember", "react", "mui-", "radix-", "headlessui-", "chakra-")
_GENERIC_PLACEHOLDERS = frozenset(
    {
        "дд.мм.гггг",
        "дд/мм/гггг",
        "dd.mm.yyyy",
        "mm/dd/yyyy",
        "__.__.____",
        "--.--.----",
    }
)


@dataclass(frozen=True)
class SelectorChoice:
    selector: str
    strategy: str
    fragile: bool
    candidates: tuple[tuple[str, str], ...] = ()


def _escape_attr(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def _escape_text(value: str) -> str:
    snippet = value.strip().replace("\n", " ")
    snippet = re.sub(r"\s+", " ", snippet)
    if len(snippet) > 80:
        snippet = snippet[:80]
    return _escape_attr(snippet)


def _is_stable_id(element_id: str) -> bool:
    if not element_id or len(element_id) >= 40:
        return False
    lowered = element_id.lower()
    return not any(lowered.startswith(prefix) for prefix in _AUTO_ID_PREFIXES)


def _is_generic_placeholder(placeholder: str) -> bool:
    normalized = placeholder.strip().lower().replace(" ", "")
    if normalized in _GENERIC_PLACEHOLDERS:
        return True
    return bool(re.fullmatch(r"[дd_.\-/]{4,}", normalized, flags=re.IGNORECASE))


def is_fragile_selector(selector: str) -> bool:
    lowered = selector.lower()
    if "nth-of-type" in lowered:
        return True
    if re.search(r">\s*input\s*$", lowered):
        return True
    if " >> " in selector:
        return False
    if ":has-text(" in lowered or "data-testid" in lowered or "[aria-label=" in lowered:
        return False
    if lowered.startswith("#") or "[name=" in lowered:
        return False
    if " > " in selector:
        return True
    return False


def _button_tag(info: dict[str, Any]) -> str:
    tag = str(info.get("tag", "") or "").lower()
    role = str(info.get("role", "") or "").lower()
    if tag == "a" or role == "link":
        return "a"
    if tag in {"button", "a"}:
        return tag
    if role in {"button", "menuitem", "tab", "link"}:
        return "button" if role != "link" else "a"
    return tag or "button"


def _candidate_testid(info: dict[str, Any]) -> str | None:
    test_id = str(info.get("testId", "") or "").strip()
    if not test_id:
        return None
    return f'[data-testid="{_escape_attr(test_id)}"]'


def _candidate_id(info: dict[str, Any]) -> str | None:
    element_id = str(info.get("id", "") or "").strip()
    if not element_id or not _is_stable_id(element_id):
        return None
    return f"#{_escape_attr(element_id)}"


def _candidate_name_aria(info: dict[str, Any]) -> str | None:
    tag = str(info.get("tag", "") or "").lower()
    name = str(info.get("name", "") or "").strip()
    if name and tag in {"input", "select", "textarea"}:
        input_type = str(info.get("inputType", "") or "").strip()
        if input_type and tag == "input":
            return f'input[type="{_escape_attr(input_type)}"][name="{_escape_attr(name)}"]'
        return f'{tag}[name="{_escape_attr(name)}"]'

    aria = str(info.get("ariaLabel", "") or "").strip()
    if aria:
        return f'[aria-label="{_escape_attr(aria)}"]'

    role = str(info.get("role", "") or "").strip()
    text = str(info.get("text", "") or "").strip()
    if role and text and len(text) <= 80:
        return f'role={role}[name="{_escape_text(text)}"]'
    return None


def _candidate_text(info: dict[str, Any]) -> str | None:
    tag = str(info.get("tag", "") or "").lower()
    text = str(info.get("text", "") or "").strip()
    caption = str(info.get("captionText", "") or info.get("labelText", "") or "").strip()
    placeholder = str(info.get("placeholder", "") or "").strip()

    if tag in {"input", "textarea", "select"}:
        if caption and len(caption) >= 2:
            return f'label:has-text("{_escape_text(caption)}")'
        if placeholder and not _is_generic_placeholder(placeholder):
            return f'{tag}[placeholder="{_escape_attr(placeholder)}"]'
        return None

    if text and 2 <= len(text) <= 80 and tag in {"button", "a", "label"}:
        return f'{tag}:has-text("{_escape_text(text)}")'
    if text and 2 <= len(text) <= 80:
        btn_tag = _button_tag(info)
        if btn_tag in {"button", "a"}:
            return f'{btn_tag}:has-text("{_escape_text(text)}")'
    return None


def _candidate_chain(info: dict[str, Any]) -> str | None:
    context = str(info.get("contextText", "") or "").strip()
    text = str(info.get("text", "") or "").strip()
    if len(context) < 6 or len(text) < 2 or len(text) > 40:
        return None
    btn_tag = _button_tag(info)
    if btn_tag not in {"button", "a"}:
        return None
    ctx = context[:60] if len(context) > 80 else context
    label = text[:40] if len(text) > 60 else text
    return (
        f'div:has-text("{_escape_text(ctx)}") >> '
        f'{btn_tag}:has-text("{_escape_text(label)}")'
    )


def _candidate_css(info: dict[str, Any], fallback: str) -> str | None:
    css = str(info.get("fallbackSelector", "") or fallback or "").strip()
    return css or None


def _build_candidates(info: dict[str, Any], fallback: str) -> dict[str, str]:
    builders = {
        "testid": _candidate_testid,
        "id": _candidate_id,
        "name_aria": _candidate_name_aria,
        "text": _candidate_text,
        "chain": _candidate_chain,
        "css": lambda data: _candidate_css(data, fallback),
    }
    candidates: dict[str, str] = {}
    for strategy, builder in builders.items():
        selector = builder(info)
        if selector:
            candidates[strategy] = selector
    return candidates


def build_selector_from_info(
    info: dict[str, Any],
    *,
    priority: list[str] | None = None,
    fallback: str = "",
) -> SelectorChoice:
    order = priority or DEFAULT_SELECTOR_PRIORITY
    candidates = _build_candidates(info, fallback)
    ordered: list[tuple[str, str]] = []
    seen: set[str] = set()
    for strategy in order:
        selector = candidates.get(strategy)
        if selector and selector not in seen:
            ordered.append((strategy, selector))
            seen.add(selector)
    for strategy, selector in candidates.items():
        if selector not in seen:
            ordered.append((strategy, selector))
            seen.add(selector)

    if not ordered:
        selector = fallback.strip()
        return SelectorChoice(
            selector=selector,
            strategy="css",
            fragile=is_fragile_selector(selector),
            candidates=(),
        )

    strategy, selector = ordered[0]
    return SelectorChoice(
        selector=selector,
        strategy=strategy,
        fragile=strategy == "css" or is_fragile_selector(selector),
        candidates=tuple(ordered),
    )


def apply_smart_selector_to_step(
    step: dict[str, Any],
    priority: list[str] | None = None,
) -> dict[str, Any]:
    action = step.get("action")
    if action not in SELECTOR_ACTIONS:
        cleaned = dict(step)
        cleaned.pop("elementInfo", None)
        return cleaned

    info = step.get("elementInfo")
    fallback = str(step.get("selector", "") or "")
    result = dict(step)

    if isinstance(info, dict):
        choice = build_selector_from_info(info, priority=priority, fallback=fallback)
        if choice.selector:
            result["selector"] = choice.selector
        result["selectorStrategy"] = choice.strategy
        result["fragile"] = choice.fragile
        if len(choice.candidates) > 1:
            result["selectorCandidates"] = [
                {"strategy": strategy, "selector": selector}
                for strategy, selector in choice.candidates
            ]
    elif fallback and is_fragile_selector(fallback):
        result["fragile"] = True

    result.pop("elementInfo", None)
    return result
