"""Shipped beginner examples and paths."""

from __future__ import annotations

from pathlib import Path

from app.gherkin_ru import gherkin_to_steps
from app.paths import examples_dir


def test_examples_dir_exists() -> None:
    root = examples_dir()
    assert root.is_dir()
    assert list(root.glob("*.feature"))


def test_example_features_parse() -> None:
    root = examples_dir()
    for path in sorted(root.glob("*.feature")):
        text = path.read_text(encoding="utf-8")
        steps = gherkin_to_steps(text)
        assert steps, f"{path.name} produced no steps"


def test_first_example_is_simple_goto_assert() -> None:
    path = examples_dir() / "01-pervaya-proverka.feature"
    steps = gherkin_to_steps(path.read_text(encoding="utf-8"))
    assert steps[0]["action"] == "goto"
    assert steps[0]["url"] == "https://example.com"
