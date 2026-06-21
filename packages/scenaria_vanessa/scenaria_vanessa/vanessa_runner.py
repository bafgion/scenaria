"""High-level Vanessa run orchestration."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Callable

from app.plugins.models import RunBatchResult, RunCaseResult, RunRequest, RunResult
from app.progress_state import ProgressState
from app.run_status_store import record_run

from scenaria_vanessa.exit_codes import describe_exit_code, is_run_success
from scenaria_vanessa.params_merger import VAParamsMerger
from scenaria_vanessa.platform_command import launch_spec_from_settings
from scenaria_vanessa.process_runner import VanessaProcessRunner
from scenaria_vanessa.report_parsers import build_cases_from_reports, collect_report_artifacts
from scenaria_vanessa.run_monitor import VanessaRunMonitor
from scenaria_vanessa.settings import load_vanessa_settings, validate_paths

PartialCasesCallback = Callable[[list[RunCaseResult]], None]


class VanessaRunner:
    id = "vanessa"
    label = "Vanessa Automation"

    def is_available(self) -> tuple[bool, str]:
        issues = validate_paths()
        if issues:
            return False, issues[0]
        return True, ""

    def run(
        self,
        request: RunRequest,
        *,
        on_log=None,
        on_progress=None,
        on_partial_cases: PartialCasesCallback | None = None,
        should_stop=None,
    ) -> RunBatchResult:
        started = time.perf_counter()
        settings = load_vanessa_settings()
        merger = VAParamsMerger(settings)
        va_params_path, merged, run_dir = merger.merge_for_request(request)
        feature_files = merger._resolve_feature_files(request)  # noqa: SLF001
        artifacts = collect_report_artifacts(merged, run_dir)
        scenario_log = run_dir / "scenario.log"
        process_log = run_dir / "process.log"
        monitor = VanessaRunMonitor(
            junit_dir=artifacts.junit_dir,
            scenario_log=scenario_log,
            process_log=process_log,
            total_planned=max(1, len(feature_files)),
        )
        last_partial_count = -1

        def _emit_progress(snapshot) -> None:
            if not on_progress:
                return
            label = snapshot.current_scenario or "Vanessa Automation"
            on_progress(
                ProgressState(
                    task_id="vanessa-run",
                    label=label,
                    current=min(snapshot.completed_cases, snapshot.total_planned),
                    total=snapshot.total_planned,
                    cancellable=True,
                )
            )

        def _poll_reports() -> None:
            nonlocal last_partial_count
            snapshot = monitor.poll()
            _emit_progress(snapshot)
            if not on_partial_cases:
                return
            count = len(snapshot.cases)
            if count <= last_partial_count:
                return
            last_partial_count = count
            on_partial_cases(list(snapshot.cases))

        if on_log:
            on_log(f"VAParams: {va_params_path}")
            on_log(f"Каталог прогона: {run_dir}")

        _emit_progress(monitor.poll())

        spec = launch_spec_from_settings(settings, va_params_path=va_params_path)
        runner = VanessaProcessRunner(log_encoding=str(settings.get("log_encoding", "auto")))
        process = runner.run(
            spec,
            run_dir=run_dir,
            on_log=on_log,
            on_poll=_poll_reports,
            should_stop=should_stop,
            timeout_sec=int(settings.get("process_timeout_sec", 3600) or 3600),
            dry_run=bool(settings.get("dry_run_only", False)),
        )
        final_snapshot = monitor.poll()
        cases = (
            list(final_snapshot.cases)
            if final_snapshot.cases
            else build_cases_from_reports(
                merged_params=merged,
                run_dir=run_dir,
                feature_files=feature_files,
                exit_code=process.exit_code,
            )
        )
        if on_partial_cases and cases and len(cases) != last_partial_count:
            on_partial_cases(list(cases))
        run_dir_str = str(run_dir.resolve())

        for case in cases:
            if case.path.suffix.lower() == ".feature" and case.path.is_file():
                record_run(
                    case.path,
                    success=case.success,
                    message=case.message,
                    duration_ms=case.duration_ms or process.duration_ms,
                    runner=self.id,
                    run_dir=run_dir_str,
                )

        duration_ms = int((time.perf_counter() - started) * 1000)
        success = is_run_success(process.exit_code) and all(case.success for case in cases)
        if process.stopped:
            success = False
        return RunBatchResult(
            runner=self.id,
            success=success,
            cases=cases,
            duration_ms=duration_ms,
            run_dir=run_dir,
            exit_code=process.exit_code,
            stopped=process.stopped,
            error=None if success else describe_exit_code(process.exit_code).label,
        )

    def parse_results(self, run_dir: Path) -> RunResult:
        import json

        merged_path = run_dir / "VAParams.json"
        merged: dict = {}
        if merged_path.is_file():
            try:
                loaded = json.loads(merged_path.read_text(encoding="utf-8"))
                merged = loaded if isinstance(loaded, dict) else {}
            except (json.JSONDecodeError, OSError):
                merged = {}
        cases = build_cases_from_reports(
            merged_params=merged,
            run_dir=run_dir,
            feature_files=[],
            exit_code=0,
        )
        return RunResult(runner=self.id, success=True, cases=cases, run_dir=run_dir)
