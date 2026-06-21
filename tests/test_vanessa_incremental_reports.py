"""Tests for incremental Vanessa report parsing and EPF install helpers."""

from __future__ import annotations

from pathlib import Path

from scenaria_vanessa.epf_install import default_epf_path, resolve_epf_download_url
from scenaria_vanessa.report_parsers import (
    IncrementalJUnitParser,
    parse_status_log,
    read_current_scenario_label,
)
from scenaria_vanessa.run_monitor import VanessaRunMonitor


def _write_junit(path: Path, *, name: str, failed: bool = False) -> None:
    failure = '<failure message="boom"/>' if failed else ""
    path.write_text(
        f"""<?xml version="1.0" encoding="UTF-8"?>
        <testsuite name="features">
          <testcase classname="features" name="{name}">{failure}</testcase>
        </testsuite>
        """,
        encoding="utf-8",
    )


def test_incremental_junit_parser_reuses_unchanged_files(tmp_path: Path) -> None:
    junit_dir = tmp_path / "junit"
    junit_dir.mkdir()
    _write_junit(junit_dir / "a.xml", name="one.feature")
    parser = IncrementalJUnitParser()
    initial = parser.poll(junit_dir)
    assert len(initial) == 1
    assert initial[0].name == "one.feature"

    _write_junit(junit_dir / "b.xml", name="two.feature", failed=True)
    updated = parser.poll(junit_dir)
    assert len(updated) == 2
    assert updated[1].success is False


def test_read_current_scenario_label_from_text_log(tmp_path: Path) -> None:
    log = tmp_path / "scenario.log"
    log.write_text(
        "ignored\nНачало выполнения сценария: Вход в систему\nШаг: нажимаю кнопку\n",
        encoding="utf-8",
    )
    assert read_current_scenario_label(log) == "Вход в систему"


def test_parse_status_log_reads_exit_code(tmp_path: Path) -> None:
    status = tmp_path / "status.log"
    status.write_text("1\n", encoding="utf-8")
    assert parse_status_log(status) == 1


def test_vanessa_run_monitor_polls_cases_and_scenario(tmp_path: Path) -> None:
    junit_dir = tmp_path / "junit"
    junit_dir.mkdir()
    _write_junit(junit_dir / "case.xml", name="checkout.feature")
    scenario_log = tmp_path / "scenario.log"
    scenario_log.write_text("Начало выполнения сценария: Оплата\n", encoding="utf-8")
    monitor = VanessaRunMonitor(
        junit_dir=junit_dir,
        scenario_log=scenario_log,
        total_planned=3,
    )
    snapshot = monitor.poll()
    assert snapshot.completed_cases == 1
    assert snapshot.current_scenario == "Оплата"
    assert snapshot.cases[0].name == "checkout.feature"


def test_resolve_epf_download_url_uses_default() -> None:
    url = resolve_epf_download_url({})
    assert "vanessa-automation" in url


def test_default_epf_path_under_data_dir(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr("app.paths.data_dir", lambda: tmp_path)
    assert default_epf_path() == tmp_path / "vanessa" / "vanessa-automation.epf"


def test_download_vanessa_epf_writes_file(tmp_path: Path, monkeypatch) -> None:
    from scenaria_vanessa import epf_install

    destination = tmp_path / "vanessa-automation.epf"

    def fake_download(url: str, path: Path, *, total_hint=0, on_progress=None) -> None:
        assert url
        path.write_bytes(b"epf")

    monkeypatch.setattr("app.update.http_download.download_url_resilient", fake_download)
    result = epf_install.download_vanessa_epf(destination, url="https://example.com/va.epf")
    assert result == destination
    assert destination.is_file()
