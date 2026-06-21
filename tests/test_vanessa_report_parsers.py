"""Tests for JUnit report parsing."""

from __future__ import annotations

from pathlib import Path

from scenaria_vanessa.report_parsers import parse_junit_file


def test_parse_junit_file_success_and_failure(tmp_path: Path) -> None:
    xml = tmp_path / "results.xml"
    xml.write_text(
        """<?xml version="1.0" encoding="UTF-8"?>
        <testsuite name="features">
          <testcase classname="features" name="ok.feature"/>
          <testcase classname="features" name="bad.feature">
            <failure message="assert failed"/>
          </testcase>
        </testsuite>
        """,
        encoding="utf-8",
    )
    cases = parse_junit_file(xml)
    assert len(cases) == 2
    assert cases[0].success is True
    assert cases[1].success is False
