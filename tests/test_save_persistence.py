"""Saving edited `.feature` files must persist to disk across restarts."""

from __future__ import annotations

from pathlib import Path

from app.feature_store import load_feature
from app.gherkin_ru import gherkin_to_steps, steps_to_gherkin
from app.mvc.controllers.scenario_controller import ScenarioController
from app.mvc.models.catalog_model import CatalogModel
from app.mvc.models.scenario_model import ScenarioModel


def test_save_preserves_comments_and_blank_lines(tmp_path: Path) -> None:
    from app.gherkin_ru import STEP_INDENT

    feature = tmp_path / "annotated.feature"
    tab = STEP_INDENT
    editor_text = (
        "Функционал: UI\n"
        "Сценарий: Demo\n"
        "\n"
        "# Подготовка пользователя\n"
        f"{tab}Допустим открыт \"https://example.com\"\n"
        "\n"
        f"{tab}# TODO: добавить логин\n"
        f"{tab}И нажимаю \"button\"\n"
    )
    feature.write_text(
        f"Функционал: UI\nСценарий: Demo\n{tab}Допустим открыт \"https://example.com\"\n",
        encoding="utf-8",
    )

    model = ScenarioModel()
    controller = ScenarioController(model, CatalogModel())
    model.load_from_path(feature)

    ok, saved = controller.save_current_scenario(editor_text=editor_text, target_path=feature)
    assert ok
    assert saved == editor_text

    disk = feature.read_text(encoding="utf-8")
    assert "# Подготовка пользователя" in disk
    assert "# TODO: добавить логин" in disk
    assert disk.strip().endswith('И нажимаю "button"')
    assert [step["action"] for step in gherkin_to_steps(disk)] == ["goto", "click"]


def test_save_current_scenario_writes_removed_step_to_disk(tmp_path: Path) -> None:
    feature = tmp_path / "signature_demo.feature"
    steps = [
        {"action": "goto", "url": "https://example.com"},
        {"action": "click", "selector": "button"},
        {"action": "close_browser"},
    ]
    feature.write_text(steps_to_gherkin(steps, scenario_name=feature.stem) + "\n", encoding="utf-8")

    model = ScenarioModel()
    controller = ScenarioController(model, CatalogModel())
    model.load_from_path(feature)

    editor_text = steps_to_gherkin(
        [step for step in steps if step["action"] != "close_browser"],
        scenario_name=feature.stem,
    )
    ok, saved = controller.save_current_scenario(editor_text=editor_text)
    assert ok
    assert saved is not None

    reloaded = feature.read_text(encoding="utf-8")
    assert "закрываю браузер" not in reloaded
    assert [step["action"] for step in gherkin_to_steps(reloaded)] == ["goto", "click"]


def test_flush_editor_to_disk_on_close(tmp_path: Path) -> None:
    feature = tmp_path / "demo.feature"
    steps = [
        {"action": "goto", "url": "https://example.com"},
        {"action": "close_browser"},
    ]
    feature.write_text(steps_to_gherkin(steps, scenario_name=feature.stem) + "\n", encoding="utf-8")

    model = ScenarioModel()
    controller = ScenarioController(model, CatalogModel())
    model.load_from_path(feature)

    editor_text = steps_to_gherkin(
        [{"action": "goto", "url": "https://example.com"}],
        scenario_name=feature.stem,
    )
    assert controller.flush_editor_to_disk(editor_text)

    reloaded = load_feature(feature)["steps"]
    assert [step["action"] for step in reloaded] == ["goto"]


def test_flush_editor_to_disk_with_explicit_path(tmp_path: Path) -> None:
    feature = tmp_path / "other.feature"
    steps = [{"action": "goto", "url": "https://example.com"}]
    feature.write_text(steps_to_gherkin(steps, scenario_name=feature.stem) + "\n", encoding="utf-8")

    model = ScenarioModel()
    controller = ScenarioController(model, CatalogModel())
    model.new_scenario()

    updated = steps_to_gherkin(
        [{"action": "goto", "url": "https://example.com"}, {"action": "reload"}],
        scenario_name=feature.stem,
    )
    assert controller.flush_editor_to_disk(updated, path=feature)
    assert [step["action"] for step in gherkin_to_steps(feature.read_text(encoding="utf-8"))] == [
        "goto",
        "reload",
    ]


def test_flush_editor_preserves_comments(tmp_path: Path) -> None:
    from app.gherkin_ru import STEP_INDENT

    feature = tmp_path / "demo.feature"
    tab = STEP_INDENT
    feature.write_text(
        f"Функционал: UI\nСценарий: Demo\n{tab}Допустим открыт \"https://example.com\"\n",
        encoding="utf-8",
    )

    model = ScenarioModel()
    controller = ScenarioController(model, CatalogModel())
    model.load_from_path(feature)

    editor_text = (
        "Функционал: UI\n"
        "Сценарий: Demo\n"
        "\n"
        "# обновлено\n"
        f"{tab}Допустим открыт \"https://example.com\"\n"
        f"{tab}И нажимаю \"go\"\n"
    )
    assert controller.flush_editor_to_disk(editor_text)

    disk = feature.read_text(encoding="utf-8")
    assert "# обновлено" in disk
    assert [step["action"] for step in gherkin_to_steps(disk)] == ["goto", "click"]


def test_draft_autosave_uses_editor_text() -> None:
    from app.feature_store import clear_draft, load_draft

    clear_draft()
    model = ScenarioModel()
    model.new_scenario()
    text = steps_to_gherkin(
        [{"action": "goto", "url": "https://example.com"}],
        scenario_name="draft",
    )
    model.save_draft_if_needed(enabled=True, editor_text=text)
    draft = load_draft()
    assert draft is not None
    assert [step["action"] for step in draft["steps"]] == ["goto"]
    clear_draft()
