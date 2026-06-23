"""Tests for VAParamsMerger."""

from __future__ import annotations

import json
from pathlib import Path

from scenaria_vanessa.params_merger import VAParamsMerger, path_for_va_json

from app.plugins.models import RunMode, RunRequest


def test_merge_overlay_writes_va_params(tmp_path: Path, monkeypatch) -> None:
    project = tmp_path / "proj"
    features = project / "features"
    features.mkdir(parents=True)
    feature = features / "smoke.feature"
    feature.write_text(
        'Функционал: UI\n@smoke\nСценарий: A\n\tДопустим открыт "https://example.com"\n',
        encoding="utf-8",
    )
    base = project / ".scenaria" / "va-params.base.json"
    base.parent.mkdir(parents=True)
    base.write_text(json.dumps({"ДанныеКлиентовТестирования": "keep-me"}), encoding="utf-8")

    epf = tmp_path / "vanessa.epf"
    epf.write_text("stub", encoding="utf-8")
    monkeypatch.setattr(
        "scenaria_vanessa.settings.load_vanessa_settings",
        lambda: {
            "epf_path": str(epf),
            "project_base_params": ".scenaria/va-params.base.json",
        },
    )

    request = RunRequest(
        mode=RunMode.FILES,
        paths=[project],
        project_root=project,
        tags=["smoke"],
    )
    va_path, merged, run_dir = VAParamsMerger().merge_for_request(request)
    assert va_path.is_file()
    assert merged["ДанныеКлиентовТестирования"] == "keep-me"
    assert "СписокТеговОтбор" in merged
    assert any("smoke.feature" in item for item in merged.get("СписокФичДляВыполнения", []))
    assert (run_dir / "junit").is_dir()


def test_path_for_va_json_uses_backslashes() -> None:
    assert "\\" in path_for_va_json(Path("C:/demo/feature.feature"))


def test_merge_allure_overlay(tmp_path: Path, monkeypatch) -> None:
    project = tmp_path / "proj"
    project.mkdir()
    feature = project / "a.feature"
    feature.write_text("x", encoding="utf-8")
    monkeypatch.setattr("scenaria_vanessa.settings.load_vanessa_settings", lambda: {"epf_path": ""})
    request = RunRequest(
        mode=RunMode.FILES,
        paths=[feature],
        project_root=project,
        runner_options={"report_junit": True, "report_allure": True},
    )
    _, merged, run_dir = VAParamsMerger().merge_for_request(request)
    assert "КаталогВыгрузкиAllure" in merged
    assert (run_dir / "allure").is_dir()
