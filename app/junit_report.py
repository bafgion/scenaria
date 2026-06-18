"""JUnit XML report builder for CLI runs."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any


def write_junit_report(
    path: Path,
    *,
    cases: list[dict[str, Any]],
    suite_name: str = "scenaria",
) -> None:
    failures = sum(1 for case in cases if not case.get("success"))
    tests = len(cases)
    suite = ET.Element(
        "testsuite",
        name=suite_name,
        tests=str(tests),
        failures=str(failures),
        errors="0",
        skipped="0",
    )
    for case in cases:
        classname = str(case.get("classname", "scenario"))
        name = str(case.get("name", "run"))
        testcase = ET.SubElement(suite, "testcase", classname=classname, name=name)
        if not case.get("success"):
            failure = ET.SubElement(testcase, "failure", message=str(case.get("message", "failed")))
            failure.text = str(case.get("details", case.get("message", "")))
    tree = ET.ElementTree(suite)
    path.parent.mkdir(parents=True, exist_ok=True)
    tree.write(path, encoding="utf-8", xml_declaration=True)
