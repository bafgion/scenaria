"""Tests for step normalization."""

from __future__ import annotations

from app.steps import apply_coalesced_step, normalize_steps, urls_match


def test_urls_match_trailing_slash() -> None:
    assert urls_match("https://shop.com/page", "https://shop.com/page/")
    assert not urls_match("https://shop.com/page", "https://shop.com/other")


def test_apply_coalesced_step_fill_replaces() -> None:
    steps = [{"action": "fill", "selector": "#q", "value": "a"}]
    updated, emitted = apply_coalesced_step(steps, {"action": "fill", "selector": "#q", "value": "b"})
    assert len(updated) == 1
    assert updated[0]["value"] == "b"
    assert emitted is not None


def test_apply_coalesced_step_skips_duplicate_hover() -> None:
    steps = [{"action": "hover", "selector": "nav"}]
    updated, emitted = apply_coalesced_step(steps, {"action": "hover", "selector": "nav"})
    assert updated == steps
    assert emitted is None


def test_collapse_duplicate_fills() -> None:
    steps = [
        {"action": "goto", "url": "https://a.com"},
        {"action": "fill", "selector": "#email", "value": "a"},
        {"action": "fill", "selector": "#email", "value": "b"},
    ]
    out = normalize_steps(steps)
    assert len(out) == 2
    assert out[1]["value"] == "b"


def test_collapse_duplicate_hovers_and_clicks() -> None:
    steps = [
        {"action": "hover", "selector": "nav"},
        {"action": "hover", "selector": "nav"},
        {"action": "click", "selector": "btn"},
        {"action": "click", "selector": "btn"},
    ]
    out = normalize_steps(steps)
    assert out == [
        {"action": "hover", "selector": "nav"},
        {"action": "click", "selector": "btn"},
    ]


def test_drop_spurious_midform_goto() -> None:
    steps = [
        {"action": "fill", "selector": "#q", "value": "dress"},
        {"action": "goto", "url": "https://shop.com/search"},
        {"action": "click", "selector": "button.search"},
    ]
    out = normalize_steps(steps)
    assert [s["action"] for s in out] == ["fill", "click"]


def test_drop_duplicate_gotos() -> None:
    steps = [
        {"action": "goto", "url": "https://a.com"},
        {"action": "click", "selector": "a"},
        {"action": "goto", "url": "https://a.com"},
    ]
    out = normalize_steps(steps)
    assert len(out) == 2
    assert out[-1]["action"] == "click"
