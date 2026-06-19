"""Recorder session edge cases."""

from __future__ import annotations

from app.mvc.models.scenario_model import ScenarioModel


def test_new_scenario_preserves_start_url() -> None:
    model = ScenarioModel()
    model.set_start_url("https://stage.example.com")
    model.set_steps([{"action": "goto", "url": "https://stage.example.com"}])
    model.set_name("demo")

    model.new_scenario()

    assert model.start_url == "https://stage.example.com"
    assert model.steps == []
    assert model.name == ""
    assert model.feature_path is None
