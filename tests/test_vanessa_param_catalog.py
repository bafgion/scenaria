"""Tests for param catalog helpers."""

from __future__ import annotations

from scenaria_vanessa.param_catalog import detect_bool_style, normalize_bool


def test_normalize_bool_ru_string() -> None:
    assert normalize_bool(True) == "Истина"
    assert normalize_bool(False) == "Ложь"


def test_detect_bool_style_from_base() -> None:
    assert detect_bool_style({"junitreport": "true"}) == "en_string"
    assert detect_bool_style({"ДелатьОтчетВФорматеjUnit": "Истина"}) == "ru_string"
