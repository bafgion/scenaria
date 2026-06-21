"""Tests for run status persistence."""

from __future__ import annotations

import json
from pathlib import Path

from app.run_status_store import (
    MAX_HISTORY,
    domain_from_url,
    get_run_history,
    get_run_status,
    record_run,
)


def test_record_and_read_status(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("app.run_status_store.data_dir", lambda: tmp_path)
    feature = tmp_path / "demo.feature"
    feature.write_text("x", encoding="utf-8")
    record_run(feature, success=True, message="ok", duration_ms=1500)
    status = get_run_status(feature)
    assert status is not None
    assert status.success is True
    assert status.message == "ok"


def test_run_history_stores_extended_fields(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("app.run_status_store.data_dir", lambda: tmp_path)
    feature = tmp_path / "demo.feature"
    feature.write_text("x", encoding="utf-8")
    record_run(
        feature,
        success=False,
        message="fail on step 3",
        duration_ms=4200,
        failed_step=3,
        report_path="/tmp/report.html",
        runner="vanessa",
    )
    history = get_run_history(feature)
    assert len(history) == 1
    assert history[0].duration_ms == 4200
    assert history[0].failed_step == 3
    assert history[0].report_path == "/tmp/report.html"
    assert history[0].runner == "vanessa"


def test_run_history_stores_run_dir(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("app.run_status_store.data_dir", lambda: tmp_path)
    feature = tmp_path / "demo.feature"
    feature.write_text("x", encoding="utf-8")
    record_run(feature, success=True, message="ok", runner="vanessa", run_dir="/tmp/run-1")
    history = get_run_history(feature)
    assert history[0].run_dir == "/tmp/run-1"


def test_run_history_keeps_last_twenty_entries(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("app.run_status_store.data_dir", lambda: tmp_path)
    feature = tmp_path / "demo.feature"
    feature.write_text("x", encoding="utf-8")
    for index in range(MAX_HISTORY + 5):
        record_run(feature, success=True, message=f"run-{index}")
    history = get_run_history(feature)
    assert len(history) == MAX_HISTORY
    assert history[0].message == f"run-{MAX_HISTORY + 4}"
    assert history[-1].message == f"run-{5}"


def test_migrates_legacy_format_on_read(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("app.run_status_store.data_dir", lambda: tmp_path)
    feature = tmp_path / "demo.feature"
    feature.write_text("x", encoding="utf-8")
    store = tmp_path / "run_status.json"
    store.write_text(
        json.dumps(
            {
                str(feature.resolve()): {
                    "success": True,
                    "message": "legacy",
                    "at": "2020-01-01T00:00:00+00:00",
                }
            }
        ),
        encoding="utf-8",
    )
    status = get_run_status(feature)
    assert status is not None
    assert status.message == "legacy"
    history = get_run_history(feature)
    assert len(history) == 1
    assert history[0].message == "legacy"


def test_domain_from_url_strips_www() -> None:
    assert domain_from_url("https://www.shop.com/path") == "shop.com"
