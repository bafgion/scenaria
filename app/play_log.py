"""Human-readable playback log lines for the journal."""

from __future__ import annotations

import re

from app.run_variables import generator_play_log_label


def step_log_target(step: dict, selector: str = "") -> str:
    text = str(step.get("text", "") or "").strip()
    if text:
        return text.rstrip("*").strip()
    sel = selector or str(step.get("selector", "") or "")
    match = re.search(r':has-text\("((?:[^"\\]|\\.)*)"\)', sel)
    if match:
        return match.group(1).replace('\\"', '"').rstrip("*").strip()
    match = re.search(r':has-text\(\'((?:[^\'\\]|\\.)*)\'\)', sel)
    if match:
        return match.group(1).replace("\\'", "'").rstrip("*").strip()
    return sel


def format_click_log(index: int, step: dict) -> str:
    target = step_log_target(step)
    return f"{index}. Клик «{target}»"


def format_fill_log(index: int, step: dict, value: str) -> str:
    target = step_log_target(step)
    return f"{index}. Ввод в «{target}»: {value}"


def format_fill_generated_log(index: int, step: dict, generator: str, value: str) -> str:
    target = step_log_target(step)
    label = generator_play_log_label(generator, value)
    if target and target.lower() not in label.lower():
        return f"{index}. {label} → «{target}»"
    return f"{index}. {label}"
