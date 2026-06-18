"""Multi-tab editor: model binding and save target."""

from __future__ import annotations

from pathlib import Path

from app.gherkin_ru import gherkin_to_steps, steps_to_gherkin
from app.mvc.controllers.scenario_controller import ScenarioController
from app.mvc.models.catalog_model import CatalogModel
from app.mvc.models.scenario_model import ScenarioModel


def _write_feature(path: Path, *, url: str = "https://example.com", extra_step: str | None = None) -> None:
    steps = [{"action": "goto", "url": url}]
    if extra_step:
        steps.append({"action": extra_step})
    path.write_text(steps_to_gherkin(steps, scenario_name=path.stem) + "\n", encoding="utf-8")


def test_bind_feature_path_does_not_load_disk_contents(tmp_path: Path) -> None:
    feature = tmp_path / "demo.feature"
    _write_feature(feature, extra_step="reload")

    model = ScenarioModel()
    model.load_from_path(feature)
    assert [step["action"] for step in model.steps] == ["goto", "reload"]

    other = tmp_path / "other.feature"
    _write_feature(other, url="https://other.test")

    model.bind_feature_path(other)
    assert model.feature_path == other.resolve()
    assert [step["action"] for step in model.steps] == ["goto", "reload"]


def test_new_scenario_clears_feature_path(tmp_path: Path) -> None:
    feature = tmp_path / "demo.feature"
    _write_feature(feature)

    model = ScenarioModel()
    model.load_from_path(feature)
    model.new_scenario()

    assert model.feature_path is None
    assert model.steps == []


def test_feature_texts_equivalent_ignores_trailing_newline() -> None:
    from app.feature_store import feature_texts_equivalent

    body = "Функционал: UI\nСценарий: test\n\tДопустим открыт \"https://example.com\""
    assert feature_texts_equivalent(body, body + "\n")
    assert feature_texts_equivalent(body + "\n", body)
    assert not feature_texts_equivalent(body, body + "\n\tИ нажимаю \"btn\"")


def test_save_current_scenario_does_not_select_in_catalog(tmp_path: Path) -> None:
    feature = tmp_path / "new.feature"
    steps = [{"action": "goto", "url": "https://example.com"}]
    text = steps_to_gherkin(steps, scenario_name=feature.stem)

    model = ScenarioModel()
    catalog = CatalogModel()
    selected: list[Path] = []
    catalog.feature_selected.connect(selected.append)
    controller = ScenarioController(model, catalog)
    model.new_scenario()

    ok, _ = controller.save_current_scenario(editor_text=text, target_path=feature)
    assert ok
    assert feature.is_file()
    assert selected == []


def test_save_current_scenario_uses_explicit_tab_path(tmp_path: Path) -> None:
    feature_a = tmp_path / "a.feature"
    feature_b = tmp_path / "b.feature"
    _write_feature(feature_a)
    _write_feature(feature_b, url="https://b.test")

    model = ScenarioModel()
    controller = ScenarioController(model, CatalogModel())
    model.load_from_path(feature_a)

    editor_text = steps_to_gherkin(
        [{"action": "goto", "url": "https://edited.test"}],
        scenario_name=feature_b.stem,
    )
    ok, _canonical = controller.save_current_scenario(
        editor_text=editor_text,
        target_path=feature_b,
    )
    assert ok

    assert [step["url"] for step in gherkin_to_steps(feature_b.read_text(encoding="utf-8"))] == [
        "https://edited.test"
    ]
    assert [step["url"] for step in gherkin_to_steps(feature_a.read_text(encoding="utf-8"))] == [
        "https://example.com"
    ]
