"""Tests for drag-and-drop path classification."""

from __future__ import annotations

from pathlib import Path

from app.qt.drag_drop import classify_drop_paths, paths_from_drop_urls


def test_paths_from_drop_urls_skips_missing(tmp_path: Path) -> None:
    existing = tmp_path / "a.feature"
    existing.write_text("Feature: A", encoding="utf-8")
    urls = [str(existing), str(tmp_path / "missing.feature")]
    assert paths_from_drop_urls(urls) == [existing.resolve()]


def test_classify_drop_paths(tmp_path: Path) -> None:
    feature = tmp_path / "login.feature"
    feature.write_text("Feature: Login", encoding="utf-8")
    other = tmp_path / "readme.txt"
    other.write_text("x", encoding="utf-8")
    sub = tmp_path / "scenarios"
    sub.mkdir()

    features, directories = classify_drop_paths([feature, other, sub])
    assert features == [feature.resolve()]
    assert directories == [sub.resolve()]
