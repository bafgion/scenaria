"""Tests for Vanessa rerun failed helper."""

from __future__ import annotations

from pathlib import Path

from scenaria_vanessa.report_parsers import failed_scenarios_from_junit
from scenaria_vanessa.rerun_failed import build_rerun_request


def test_failed_scenarios_from_junit(tmp_path: Path) -> None:
    junit_dir = tmp_path / "junit"
    junit_dir.mkdir()
    (junit_dir / "out.xml").write_text(
        """<?xml version="1.0" encoding="UTF-8"?>
        <testsuite name="login.feature">
          <testcase classname="login.feature" name="Успешный вход"/>
          <testcase classname="login.feature" name="Неверный пароль">
            <failure message="assert"/>
          </testcase>
        </testsuite>
        """,
        encoding="utf-8",
    )
    failed = failed_scenarios_from_junit(junit_dir)
    assert len(failed) == 1
    assert failed[0].scenario_name == "Неверный пароль"


def test_build_rerun_request(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    junit_dir = run_dir / "junit"
    junit_dir.mkdir(parents=True)
    (junit_dir / "out.xml").write_text(
        """<?xml version="1.0"?>
        <testsuite name="demo.feature">
          <testcase classname="demo.feature" name="Fail case"><failure message="x"/></testcase>
        </testsuite>
        """,
        encoding="utf-8",
    )
    (run_dir / "VAParams.json").write_text('{"КаталогВыгрузкиJUnit": "' + str(junit_dir).replace("\\", "\\\\") + '"}', encoding="utf-8")
    feature = tmp_path / "demo.feature"
    feature.write_text("x", encoding="utf-8")
    request = build_rerun_request(
        project_root=tmp_path,
        paths=[feature],
        run_dir=run_dir,
    )
    assert request is not None
    assert "Fail case" in request.scenario_names
