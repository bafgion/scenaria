"""Normalize recorded scenario steps for reliable playback."""

from __future__ import annotations

import re
from urllib.parse import urlparse

# Playwright navigation: align recorder and player on the same readiness signal.
NAV_WAIT_UNTIL = "domcontentloaded"
NAV_TIMEOUT_MS = 30_000


def urls_match(current: str, target: str) -> bool:
    if not current or not target:
        return False
    if current.rstrip("/") == target.rstrip("/"):
        return True
    cur = urlparse(current)
    tgt = urlparse(target)
    return cur.scheme == tgt.scheme and cur.netloc == tgt.netloc and cur.path.rstrip("/") == tgt.path.rstrip("/")


def normalize_steps(steps: list[dict]) -> list[dict]:
    if not steps:
        return []

    prepared = [_upgrade_fill_selector(step) if step.get("action") == "fill" else step for step in steps]
    merged = _collapse_fills(prepared)
    merged = _collapse_click_before_fill(merged)
    merged = _collapse_checkbox_noise(merged)
    merged = [_upgrade_checkbox_selector(step) for step in merged]
    merged = [_upgrade_canvas_step(step) for step in merged]
    merged = [_upgrade_click_selector(step) for step in merged]
    merged = [_disambiguate_click_selector(step) for step in merged]
    merged = _collapse_duplicate_hovers(merged)
    merged = _collapse_duplicate_clicks(merged)
    merged = _drop_spurious_midform_gotos(merged)
    return _drop_duplicate_gotos(merged)


def apply_coalesced_step(steps: list[dict], step: dict) -> tuple[list[dict], dict | None]:
    """
    Merge *step* into *steps* using live-recording coalescing rules.

    Returns (updated_steps, emitted_step). *emitted_step* is None when the
    incoming step is skipped as a duplicate hover/click.
    """
    if step.get("action") == "fill":
        step = _upgrade_fill_selector(step)

    if not steps:
        return steps + [step], step

    action = step.get("action")
    last = steps[-1]

    if action == "fill" and last.get("action") == "fill" and last.get("selector") == step.get("selector"):
        return steps[:-1] + [step], step

    if action == "fill" and last.get("action") == "click" and last.get("selector") == step.get("selector"):
        upgraded = _upgrade_fill_selector(step)
        return steps[:-1] + [upgraded], upgraded

    if action == "fill" and step.get("inputType") == "checkbox":
        checked = str(step.get("value", "")).lower() in {"on", "true", "1", "yes"}
        return apply_coalesced_step(
            steps,
            {"action": "check" if checked else "uncheck", "selector": step.get("selector", "")},
        )

    if action in ("check", "uncheck"):
        step = _upgrade_checkbox_selector(step)
        if last.get("action") == "click":
            return steps[:-1] + [step], step
        if last.get("action") == action and last.get("selector") == step.get("selector"):
            return steps, None
        if last.get("action") in ("check", "uncheck") and last.get("selector") == step.get("selector"):
            return steps[:-1] + [step], step

    if (
        action == "hover"
        and last.get("action") == "hover"
        and last.get("selector") == step.get("selector")
    ):
        return steps, None

    if (
        action == "click"
        and last.get("action") == "click"
        and last.get("selector") == step.get("selector")
    ):
        return steps, None

    return steps + [step], step


def _collapse_fills(steps: list[dict]) -> list[dict]:
    result: list[dict] = []
    fill_index_by_selector: dict[str, int] = {}

    for step in steps:
        if step.get("action") != "fill":
            result.append(step)
            if step.get("action") in {"click", "select", "goto"}:
                fill_index_by_selector.clear()
            continue

        selector = step.get("selector", "")
        if not selector:
            result.append(step)
            continue

        if selector in fill_index_by_selector:
            result[fill_index_by_selector[selector]] = step
        else:
            fill_index_by_selector[selector] = len(result)
            result.append(step)

    return result


def _collapse_checkbox_noise(steps: list[dict]) -> list[dict]:
    """Turn legacy click+fill(on) checkbox recordings into a single check/uncheck."""
    result: list[dict] = []
    for step in steps:
        if step.get("action") == "fill" and (
            step.get("inputType") == "checkbox"
            or str(step.get("value", "")).lower() in {"on", "off"}
        ):
            checked = str(step.get("value", "")).lower() in {"on", "true", "1", "yes"}
            while result and result[-1].get("action") == "click":
                result.pop()
            normalized = {
                "action": "check" if checked else "uncheck",
                "selector": step.get("selector", ""),
            }
            if step.get("text"):
                normalized["text"] = step.get("text")
            normalized = _upgrade_checkbox_selector(normalized)
            if (
                result
                and result[-1].get("action") == normalized["action"]
                and result[-1].get("selector") == normalized["selector"]
            ):
                continue
            result.append(normalized)
            continue

        if step.get("action") in ("check", "uncheck"):
            while result and result[-1].get("action") == "click":
                result.pop()
            upgraded = _upgrade_checkbox_selector(step)
            if (
                result
                and result[-1].get("action") == upgraded.get("action")
                and result[-1].get("selector") == upgraded.get("selector")
            ):
                continue
            result.append(upgraded)
            continue

        result.append(step)
    return result


def _collapse_click_before_fill(steps: list[dict]) -> list[dict]:
    result: list[dict] = []
    for step in steps:
        if (
            result
            and step.get("action") == "fill"
            and result[-1].get("action") == "click"
        ):
            click_selector = str(result[-1].get("selector", ""))
            fill_selector = str(step.get("selector", ""))
            if click_selector == fill_selector or _selector_is_fragile(click_selector):
                result.pop()
        result.append(step)
    return result


def _selector_is_fragile(selector: str) -> bool:
    lowered = selector.lower()
    if "nth-of-type" in lowered:
        return True
    if re.search(r">\s*input\s*$", lowered):
        return True
    return False


def _contextual_button_selector(context: str, label: str) -> str:
    context_snippet = context[:60] if len(context) > 80 else context
    label_snippet = label[:40] if len(label) > 60 else label
    escaped_ctx = context_snippet.replace("\\", "\\\\").replace('"', '\\"')
    escaped_label = label_snippet.replace("\\", "\\\\").replace('"', '\\"')
    return f'div:has-text("{escaped_ctx}") >> button:has-text("{escaped_label}")'


def _upgrade_click_selector(step: dict) -> dict:
    if step.get("action") != "click":
        return step
    selector = str(step.get("selector", ""))
    if "canvas" in selector.lower():
        return step
    context = str(step.get("contextText", "")).strip()
    text = str(step.get("text", "")).strip().replace("\n", " ")
    text = re.sub(r"\s+", " ", text)
    label = text
    if len(label) >= 2 and len(context) >= 6:
        return {**step, "selector": _contextual_button_selector(context, label)}
    if not _selector_is_fragile(selector):
        return step
    if len(text) < 2:
        return step
    snippet = text[:40] if len(text) > 60 else text
    if len(snippet) < 2:
        return step
    escaped = snippet.replace("\\", "\\\\").replace('"', '\\"')
    return {**step, "selector": f'button:has-text("{escaped}")'}


def _disambiguate_click_selector(step: dict) -> dict:
    if step.get("action") != "click":
        return step
    selector = str(step.get("selector", ""))
    if " >> " in selector:
        return step
    match = re.match(r'^button:has-text\("((?:[^"\\]|\\.)*)"\)$', selector)
    if not match:
        return step
    context = str(step.get("contextText", "")).strip()
    if len(context) < 6:
        return step
    label = match.group(1).replace('\\"', '"')
    return {**step, "selector": _contextual_button_selector(context, label)}


def _upgrade_checkbox_selector(step: dict) -> dict:
    action = step.get("action")
    if action not in ("check", "uncheck"):
        return step
    selector = str(step.get("selector", ""))
    if not _selector_is_fragile(selector):
        return step
    text = str(step.get("text", "")).strip()
    if len(text) < 4:
        return step
    snippet = text[:40] if len(text) > 60 else text
    if len(snippet) < 4:
        return step
    escaped = snippet.replace("\\", "\\\\").replace('"', '\\"')
    return {**step, "selector": f'label:has-text("{escaped}")'}


def _is_generic_placeholder_selector(selector: str) -> bool:
    match = re.search(r'placeholder="([^"]+)"', selector, flags=re.IGNORECASE)
    if not match:
        return False
    placeholder = match.group(1).replace('\\"', '"').strip().lower().replace(" ", "")
    generic = {
        "дд.мм.гггг",
        "дд/мм/гггг",
        "dd.mm.yyyy",
        "mm/dd/yyyy",
        "__.__.____",
        "--.--.----",
    }
    if placeholder in generic:
        return True
    return bool(re.fullmatch(r"[дd_.\-/]{4,}", placeholder, flags=re.IGNORECASE))


def _upgrade_fill_selector(step: dict) -> dict:
    if step.get("action") != "fill":
        return step
    selector = str(step.get("selector", ""))
    fragile = _selector_is_fragile(selector)
    generic_placeholder = _is_generic_placeholder_selector(selector)
    if not fragile and not generic_placeholder:
        return step
    text = str(step.get("text", "")).strip().rstrip("*").strip()
    if len(text) < 2:
        return step
    snippet = text[:40] if len(text) > 60 else text
    if len(snippet) < 2:
        return step
    escaped = snippet.replace("\\", "\\\\").replace('"', '\\"')
    return {**step, "selector": f'label:has-text("{escaped}")'}


def _upgrade_canvas_step(step: dict) -> dict:
    action = step.get("action")
    selector = str(step.get("selector", ""))
    if "canvas" not in selector.lower():
        return step
    if action == "click" and _selector_is_fragile(selector):
        upgraded = {"action": "draw_signature", "selector": _best_canvas_selector(step)}
        if step.get("text"):
            upgraded["text"] = step.get("text")
        return upgraded
    if action == "draw_signature" and _selector_is_fragile(selector):
        return {**step, "selector": _best_canvas_selector(step)}
    return step


def _best_canvas_selector(step: dict) -> str:
    text = str(step.get("text", "")).strip()
    if text and len(text) >= 4:
        snippet = text[:30] if len(text) > 40 else text
        escaped = snippet.replace("\\", "\\\\").replace('"', '\\"')
        return f'div:has-text("{escaped}") canvas'
    return "canvas"


def _collapse_duplicate_hovers(steps: list[dict]) -> list[dict]:
    result: list[dict] = []
    for step in steps:
        if (
            result
            and step.get("action") == "hover"
            and result[-1].get("action") == "hover"
            and step.get("selector") == result[-1].get("selector")
        ):
            continue
        result.append(step)
    return result


def _collapse_duplicate_clicks(steps: list[dict]) -> list[dict]:
    result: list[dict] = []
    for step in steps:
        if (
            result
            and step.get("action") == "click"
            and result[-1].get("action") == "click"
            and step.get("selector") == result[-1].get("selector")
        ):
            continue
        result.append(step)
    return result


def _drop_spurious_midform_gotos(steps: list[dict]) -> list[dict]:
    """Drop redirect gotos between form fills and submit click."""
    result: list[dict] = []
    had_fill = False

    for index, step in enumerate(steps):
        action = step.get("action")
        if action == "fill":
            had_fill = True
            result.append(step)
            continue

        if (
            action == "goto"
            and had_fill
            and index + 1 < len(steps)
            and steps[index + 1].get("action") == "click"
        ):
            continue

        result.append(step)
        if action == "goto":
            had_fill = False

    return result


def _drop_duplicate_gotos(steps: list[dict]) -> list[dict]:
    result: list[dict] = []
    last_goto = ""

    for step in steps:
        if step.get("action") != "goto":
            result.append(step)
            continue

        url = step.get("url", "")
        if url and url == last_goto:
            continue
        last_goto = url
        result.append(step)

    return result
