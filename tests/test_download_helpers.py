"""Tests for download helpers."""

from __future__ import annotations

from pathlib import Path

from app.download_helpers import file_contains_substring, new_download_run_dir, read_text_content


def test_new_download_run_dir(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("app.download_helpers.data_dir", lambda: tmp_path)
    run_id, directory = new_download_run_dir()
    assert run_id
    assert directory.is_dir()
    assert directory.parent.name == "downloads"


def test_file_contains_substring(tmp_path: Path) -> None:
    file_path = tmp_path / "report.txt"
    file_path.write_text("Invoice #12345", encoding="utf-8")
    assert file_contains_substring(file_path, "Invoice")
    assert not file_contains_substring(file_path, "missing")


def test_read_text_content_utf8(tmp_path: Path) -> None:
    file_path = tmp_path / "a.txt"
    file_path.write_text("Привет", encoding="utf-8")
    assert "Привет" in read_text_content(file_path)
