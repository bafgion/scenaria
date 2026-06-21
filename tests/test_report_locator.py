"""Tests for report_locator."""

from __future__ import annotations

from pathlib import Path

from app.report_locator import ReportTarget, find_latest_report


def test_find_latest_report_prefers_hint_html(tmp_path: Path, monkeypatch) -> None:
    reports = tmp_path / "reports"
    reports.mkdir()
    older = reports / "old" / "index.html"
    older.parent.mkdir()
    older.write_text("<html></html>", encoding="utf-8")

    hint = tmp_path / "new.html"
    hint.write_text("<html>new</html>", encoding="utf-8")

    monkeypatch.setattr("app.report_locator.reports_dir", lambda: reports)

    target = find_latest_report(hints={"html_report_path": str(hint)})
    assert target == ReportTarget("html", hint)


def test_find_latest_report_scans_reports_dir(tmp_path: Path, monkeypatch) -> None:
    reports = tmp_path / "reports"
    stamp = reports / "2026-01-01_12-00-00"
    stamp.mkdir(parents=True)
    index = stamp / "index.html"
    index.write_text("<html>batch</html>", encoding="utf-8")

    monkeypatch.setattr("app.report_locator.reports_dir", lambda: reports)

    target = find_latest_report()
    assert target is not None
    assert target.kind == "html"
    assert target.path == index


def test_find_latest_report_allure_hint(tmp_path: Path) -> None:
    allure = tmp_path / "allure"
    allure.mkdir()
    (allure / "result.json").write_text("{}", encoding="utf-8")

    target = find_latest_report(hints={"allure_dir": str(allure)})
    assert target == ReportTarget("allure", allure)


def test_find_latest_report_none_when_empty(tmp_path: Path, monkeypatch) -> None:
    reports = tmp_path / "reports"
    reports.mkdir()
    monkeypatch.setattr("app.report_locator.reports_dir", lambda: reports)

    assert find_latest_report() is None
