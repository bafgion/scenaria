"""Tests for selector priority settings and post-record hint keys."""

from __future__ import annotations

from app.qt.widgets.post_record_banner import hint_dismiss_key
from app.scenario_hints import ScenarioHint
from app.selector_build import normalize_selector_priority


def test_normalize_selector_priority_drops_unknown_and_appends_missing() -> None:
    assert normalize_selector_priority(["css", "testid", "unknown"]) == [
        "css",
        "testid",
        "id",
        "name_aria",
        "text",
        "chain",
    ]


def test_hint_dismiss_key_includes_step_index() -> None:
    hint = ScenarioHint(
        id="menu_hover",
        title="x",
        step_indices=(4,),
        severity="warning",
        auto_fixable=True,
    )
    assert hint_dismiss_key(hint) == "menu_hover:4"
