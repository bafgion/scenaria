"""Tests for batch feature runner."""

from __future__ import annotations

from pathlib import Path

from app.run_suite import collect_feature_files, format_suite_summary


def test_collect_feature_files_from_directory(tmp_path: Path) -> None:
    (tmp_path / "a.feature").write_text(
        f'Функционал: UI\nСценарий: A\n\tДопустим открыт "https://a.com"\n',
        encoding="utf-8",
    )
    sub = tmp_path / "nested"
    sub.mkdir()
    (sub / "b.feature").write_text(
        f'Функционал: UI\nСценарий: B\n\tДопустим открыт "https://b.com"\n',
        encoding="utf-8",
    )
    files = collect_feature_files([tmp_path])
    names = {path.name for path in files}
    assert names == {"a.feature", "b.feature"}


def test_format_suite_summary() -> None:
    class FakePath:
        name = "demo.feature"

    text = format_suite_summary(
        [
            {"success": True, "path": FakePath(), "executed": 2, "total": 2},
            {"success": False, "path": FakePath(), "message": "timeout"},
        ]
    )
    assert "1 OK, 1 FAIL" in text
    assert "FAIL" in text
