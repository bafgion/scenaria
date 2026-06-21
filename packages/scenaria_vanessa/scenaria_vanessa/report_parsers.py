"""Report artifact paths and parsing helpers."""

from __future__ import annotations

import json
import os
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.plugins.models import RunCaseResult

from scenaria_vanessa.exit_codes import is_run_success

_SCENARIO_START_RE = re.compile(
    r"(?:Начало выполнения сценария|Сценарий|Scenario)\s*[:\-]\s*(.+?)\s*$",
    re.IGNORECASE,
)
_STEP_START_RE = re.compile(
    r"(?:Шаг|Step)\s*[:\-]\s*(.+?)\s*$",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class ReportArtifacts:
    junit_dir: Path | None
    allure_dir: Path | None
    status_path: Path | None


@dataclass(frozen=True)
class FailedScenario:
    scenario_name: str
    feature_path: Path | None = None
    message: str = ""


def junit_dir_from_params(merged_params: dict[str, Any]) -> Path | None:
    for key in ("КаталогВыгрузкиJUnit", "junitpath", "КаталогOutputjUnit"):
        raw = merged_params.get(key)
        if raw:
            return Path(str(raw))
    return None


def allure_dir_from_params(merged_params: dict[str, Any]) -> Path | None:
    for key in ("КаталогВыгрузкиAllure", "allurepath"):
        raw = merged_params.get(key)
        if raw:
            return Path(str(raw))
    return None


def status_path_from_params(merged_params: dict[str, Any]) -> Path | None:
    for key in ("ПутьКФайлуДляВыгрузкиСтатусаВыполненияСценариев", "statuspath"):
        raw = merged_params.get(key)
        if raw:
            return Path(str(raw))
    return None


def collect_report_artifacts(merged_params: dict[str, Any], run_dir: Path) -> ReportArtifacts:
    return ReportArtifacts(
        junit_dir=junit_dir_from_params(merged_params) or (run_dir / "junit"),
        allure_dir=allure_dir_from_params(merged_params) or (run_dir / "allure"),
        status_path=status_path_from_params(merged_params) or (run_dir / "status.log"),
    )


def parse_junit_dir(junit_dir: Path) -> list[RunCaseResult]:
    if not junit_dir.is_dir():
        return []
    parser = IncrementalJUnitParser()
    return parser.poll(junit_dir)


@dataclass
class _JUnitFileCache:
    mtime: float
    cases: list[RunCaseResult] = field(default_factory=list)


class IncrementalJUnitParser:
    """Parse only changed JUnit XML files between polls."""

    def __init__(self) -> None:
        self._files: dict[str, _JUnitFileCache] = {}

    def poll(self, junit_dir: Path | None) -> list[RunCaseResult]:
        if junit_dir is None or not junit_dir.is_dir():
            return []
        present: set[str] = set()
        for xml_path in sorted(junit_dir.rglob("*.xml")):
            key = str(xml_path)
            present.add(key)
            try:
                mtime = float(xml_path.stat().st_mtime)
            except OSError:
                continue
            cached = self._files.get(key)
            if cached is not None and cached.mtime == mtime:
                continue
            self._files[key] = _JUnitFileCache(mtime=mtime, cases=parse_junit_file(xml_path))
        for key in list(self._files):
            if key not in present:
                del self._files[key]
        merged: list[RunCaseResult] = []
        for key in sorted(self._files):
            merged.extend(self._files[key].cases)
        return merged


def _read_log_tail(path: Path | None, *, max_bytes: int) -> str:
    if path is None or not path.is_file():
        return ""
    try:
        size = path.stat().st_size
        with path.open("rb") as handle:
            if size > max_bytes:
                handle.seek(-max_bytes, os.SEEK_END)
            return handle.read().decode("utf-8", errors="replace")
    except OSError:
        return ""


def read_current_scenario_label(
    scenario_log: Path | None,
    *,
    process_log: Path | None = None,
    max_bytes: int = 16_384,
) -> str:
    """Best-effort current scenario name from Vanessa text logs."""
    current = ""
    for source in (scenario_log, process_log):
        text = _read_log_tail(source, max_bytes=max_bytes)
        if not text:
            continue
        for line in text.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            match = _SCENARIO_START_RE.search(stripped)
            if match:
                current = match.group(1).strip().strip('"')
                continue
            step_match = _STEP_START_RE.search(stripped)
            if step_match and not current:
                current = step_match.group(1).strip().strip('"')
        if current:
            break
    return current


def parse_status_log(path: Path | None) -> int | None:
    if path is None or not path.is_file():
        return None
    try:
        raw = path.read_text(encoding="utf-8", errors="replace").strip()
    except OSError:
        return None
    if not raw:
        return None
    first = raw.splitlines()[0].strip()
    if first.isdigit():
        return int(first)
    return None


def parse_junit_file(path: Path) -> list[RunCaseResult]:
    try:
        root = ET.parse(path).getroot()
    except (ET.ParseError, OSError):
        return []

    cases: list[RunCaseResult] = []
    if root.tag == "testsuite":
        suites = [root]
    else:
        suites = list(root.findall("testsuite"))
    for suite in suites:
        classname = suite.attrib.get("name", path.stem)
        for testcase in suite.findall("testcase"):
            name = testcase.attrib.get("name", "case")
            failure = testcase.find("failure")
            error = testcase.find("error")
            skipped = testcase.find("skipped")
            if failure is not None:
                message = failure.attrib.get("message") or (failure.text or "failure")
                success = False
            elif error is not None:
                message = error.attrib.get("message") or (error.text or "error")
                success = False
            elif skipped is not None:
                message = "skipped"
                success = True
            else:
                message = "ok"
                success = True
            feature_path = _guess_feature_path(name, classname)
            cases.append(
                RunCaseResult(
                    path=feature_path,
                    name=name,
                    classname=classname,
                    success=success,
                    message=message.strip(),
                    details=message.strip(),
                    executed=1,
                    total=1,
                )
            )
    return cases


def failed_scenarios_from_junit(junit_dir: Path) -> list[FailedScenario]:
    failed: list[FailedScenario] = []
    for case in parse_junit_dir(junit_dir):
        if case.success:
            continue
        feature = case.path if case.path.suffix.lower() == ".feature" else None
        failed.append(
            FailedScenario(
                scenario_name=case.name,
                feature_path=feature if feature and feature.is_file() else None,
                message=case.message,
            )
        )
    return failed


def _guess_feature_path(name: str, classname: str) -> Path:
    for candidate in (name, classname):
        if candidate.lower().endswith(".feature"):
            return Path(candidate)
    return Path(f"{name}.feature")


def build_cases_from_reports(
    *,
    merged_params: dict[str, Any],
    run_dir: Path,
    feature_files: list[Path],
    exit_code: int,
) -> list[RunCaseResult]:
    artifacts = collect_report_artifacts(merged_params, run_dir)
    junit_dir = artifacts.junit_dir
    parsed = parse_junit_dir(junit_dir) if junit_dir is not None else []
    if parsed:
        return parsed

    success = is_run_success(exit_code)
    message = f"exit code {exit_code}"
    if not feature_files:
        if success:
            return []
        return [
            RunCaseResult(
                path=run_dir / "vanessa-run",
                name="vanessa",
                classname="vanessa",
                success=False,
                message=message,
            )
        ]
    return [
        RunCaseResult(
            path=path,
            name=path.stem,
            classname=str(path.parent.name or "features"),
            success=success,
            message=message,
            executed=0,
            total=0,
        )
        for path in feature_files
    ]


def load_merged_params(run_dir: Path) -> dict[str, Any]:
    path = run_dir / "VAParams.json"
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    return data if isinstance(data, dict) else {}
