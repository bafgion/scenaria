"""Shipped beginner examples and paths."""

from __future__ import annotations


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


def test_outline_example_expands() -> None:
    from app.gherkin_outline import outline_example_count, parse_outline
    from app.run_suite import collect_play_scenarios

    path = examples_dir() / "04-tablica-primerov.feature"
    text = path.read_text(encoding="utf-8")
    assert outline_example_count(text) == 2
    outline = parse_outline(text)
    assert outline is not None
    assert outline.rows[0]["url"] == "https://example.com"

    scenarios = collect_play_scenarios(path, text=text)
    assert len(scenarios) == 2
    assert scenarios[0]["steps"][0]["url"] == "https://example.com"
    assert scenarios[1]["steps"][0]["url"] == "https://www.example.org"
    assert "<url>" not in scenarios[0]["steps"][0]["url"]


def test_first_example_is_simple_goto_assert() -> None:
    path = examples_dir() / "01-pervaya-proverka.feature"
    steps = gherkin_to_steps(path.read_text(encoding="utf-8"))
    assert steps[0]["action"] == "goto"
    assert steps[0]["url"] == "https://example.com"


def test_testclient_example_parses_context() -> None:
    from app.gherkin_context import parse_feature_test_client
    from app.run_suite import collect_play_scenarios
    from app.test_clients import test_client_exists

    root = examples_dir()
    path = root / "05-testclient-kontekst.feature"
    text = path.read_text(encoding="utf-8")
    assert parse_feature_test_client(text) == "DemoUser"
    steps = gherkin_to_steps(text)
    assert len(steps) == 4
    assert steps[0]["action"] == "goto"

    scenarios = collect_play_scenarios(path, text=text)
    assert len(scenarios) == 1
    assert scenarios[0]["testClient"] == "DemoUser"
    assert test_client_exists("DemoUser", root)
