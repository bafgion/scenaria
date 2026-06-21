"""Runner request/result models shared by core and add-ons."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


class RunMode(str, Enum):
    FILES = "files"
    DIRECTORY = "directory"
    TAG = "tag"
    PROJECT_ROOT = "project_root"


@dataclass
class RunRequest:
    mode: RunMode = RunMode.FILES
    paths: list[Path] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    exclude_tags: list[str] = field(default_factory=list)
    scenario_names: list[str] = field(default_factory=list)
    runner_options: dict[str, Any] = field(default_factory=dict)
    project_root: Path | None = None
    headless: bool = True
    slow_mo_ms: int = 0
    browser_engine: str | None = None
    variables: dict[str, str] = field(default_factory=dict)

    @property
    def tag(self) -> str | None:
        if not self.tags:
            return None
        return self.tags[0].strip().lstrip("@") or None


@dataclass
class RunCaseResult:
    path: Path
    name: str
    classname: str
    success: bool
    message: str
    details: str = ""
    executed: int = 0
    total: int = 0
    trace_path: Any = None
    screenshot_path: Any = None
    log_lines: list[str] = field(default_factory=list)
    step_results: list[Any] = field(default_factory=list)
    duration_ms: int = 0
    failed_step: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "name": self.name,
            "classname": self.classname,
            "success": self.success,
            "message": self.message,
            "details": self.details,
            "executed": self.executed,
            "total": self.total,
            "trace_path": self.trace_path,
            "screenshot_path": self.screenshot_path,
            "log_lines": list(self.log_lines),
            "step_results": list(self.step_results),
            "duration_ms": self.duration_ms,
            "failed_step": self.failed_step,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RunCaseResult:
        path = data.get("path")
        if not isinstance(path, Path):
            path = Path(str(path or ""))
        failed = data.get("failed_step")
        return cls(
            path=path,
            name=str(data.get("name", path.stem)),
            classname=str(data.get("classname", "")),
            success=bool(data.get("success")),
            message=str(data.get("message", "")),
            details=str(data.get("details", "")),
            executed=int(data.get("executed", 0)),
            total=int(data.get("total", 0)),
            trace_path=data.get("trace_path"),
            screenshot_path=data.get("screenshot_path"),
            log_lines=list(data.get("log_lines") or []),
            step_results=list(data.get("step_results") or []),
            duration_ms=int(data.get("duration_ms", 0)),
            failed_step=int(failed) if failed is not None else None,
        )


@dataclass
class RunBatchResult:
    runner: str
    success: bool
    cases: list[RunCaseResult]
    duration_ms: int = 0
    run_dir: Path | None = None
    exit_code: int = 0
    stopped: bool = False
    error: str | None = None

    def to_legacy_cases(self) -> list[dict[str, Any]]:
        return [case.to_dict() for case in self.cases]


@dataclass
class RunResult:
    runner: str
    success: bool
    cases: list[RunCaseResult]
    duration_ms: int = 0
    run_dir: Path | None = None
    exit_code: int = 0

    @classmethod
    def from_batch(cls, batch: RunBatchResult) -> RunResult:
        return cls(
            runner=batch.runner,
            success=batch.success,
            cases=list(batch.cases),
            duration_ms=batch.duration_ms,
            run_dir=batch.run_dir,
            exit_code=batch.exit_code,
        )
