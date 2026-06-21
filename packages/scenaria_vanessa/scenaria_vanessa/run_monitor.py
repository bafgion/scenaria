"""Poll Vanessa report artifacts while a run is in progress."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from app.plugins.models import RunCaseResult

from scenaria_vanessa.report_parsers import IncrementalJUnitParser, read_current_scenario_label

_SCENARIO_TAIL_BYTES = 24_576


@dataclass
class VanessaRunSnapshot:
    cases: list[RunCaseResult]
    current_scenario: str
    completed_cases: int
    total_planned: int


class VanessaRunMonitor:
    def __init__(
        self,
        *,
        junit_dir: Path | None,
        scenario_log: Path | None,
        process_log: Path | None = None,
        total_planned: int = 1,
    ) -> None:
        self._junit_dir = junit_dir
        self._scenario_log = scenario_log
        self._process_log = process_log
        self._total_planned = max(1, int(total_planned))
        self._junit = IncrementalJUnitParser()

    def poll(self) -> VanessaRunSnapshot:
        cases = self._junit.poll(self._junit_dir) if self._junit_dir is not None else []
        current = read_current_scenario_label(
            self._scenario_log,
            process_log=self._process_log,
            max_bytes=_SCENARIO_TAIL_BYTES,
        )
        if not current and cases:
            current = str(cases[-1].name or "")
        completed = len(cases)
        total = max(self._total_planned, completed, 1)
        return VanessaRunSnapshot(
            cases=cases,
            current_scenario=current,
            completed_cases=completed,
            total_planned=total,
        )
