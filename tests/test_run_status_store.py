"""Tests for run status persistence."""

from __future__ import annotations

from pathlib import Path

from app.run_status_store import domain_from_url, get_run_status, record_run


def test_record_and_read_status(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("app.run_status_store.data_dir", lambda: tmp_path)
    feature = tmp_path / "demo.feature"
    feature.write_text("x", encoding="utf-8")
    record_run(feature, success=True, message="ok")
    status = get_run_status(feature)
    assert status is not None
    assert status.success is True
    assert status.message == "ok"


def test_domain_from_url_strips_www() -> None:
    assert domain_from_url("https://www.shop.com/path") == "shop.com"
