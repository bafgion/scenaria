"""Built-in Playwright runner (wraps ``run_suite``)."""

from __future__ import annotations

import time
from pathlib import Path

from app.plugins.models import RunBatchResult, RunCaseResult, RunMode, RunRequest, RunResult
from app.progress_state import ProgressState
from app.run_suite import infer_project_root, resolve_feature_files, run_feature_paths


class PlaywrightRunner:
    id = "playwright"
    label = "Playwright"

    def is_available(self) -> tuple[bool, str]:
        return True, ""

    def run(
        self,
        request: RunRequest,
        *,
        on_log=None,
        on_progress=None,
        on_partial_cases=None,
        should_stop=None,
    ) -> RunBatchResult:
        started = time.perf_counter()
        tag = request.tag
        paths = list(request.paths)
        root = request.project_root or infer_project_root(paths)
        cases: list[RunCaseResult] = []
        stopped = False
        error: str | None = None
        success = False

        def _on_case_start(path: Path) -> None:
            if not on_progress:
                return
            files = resolve_feature_files(paths, tag=tag)
            try:
                current = sum(1 for case in cases) + 1
            except Exception:
                current = 1
            on_progress(
                ProgressState(
                    task_id="batch-run",
                    label=str(path.name),
                    current=min(current, len(files)),
                    total=max(1, len(files)),
                    cancellable=True,
                )
            )

        try:
            batch = run_feature_paths(
                paths,
                headless=request.headless,
                slow_mo_ms=request.slow_mo_ms,
                on_log=on_log,
                on_case_start=_on_case_start,
                should_stop=should_stop,
                tag=tag,
                project_root=root,
                browser_engine=request.browser_engine,
                variables=request.variables or None,
                runner=self.id,
            )
            cases = [RunCaseResult.from_dict(item) for item in batch]
            stopped = bool(should_stop and should_stop())
            success = bool(cases) and all(case.success for case in cases) and not stopped
        except Exception as exc:  # noqa: BLE001
            error = str(exc)
            success = False

        duration_ms = int((time.perf_counter() - started) * 1000)
        exit_code = 0 if success else 1
        return RunBatchResult(
            runner=self.id,
            success=success,
            cases=cases,
            duration_ms=duration_ms,
            exit_code=exit_code,
            stopped=stopped,
            error=error,
        )

    def parse_results(self, run_dir: Path) -> RunResult:
        return RunResult(runner=self.id, success=False, cases=[], run_dir=run_dir, exit_code=1)

    def contribute_menus(self, host) -> None:
        return None

    def contribute_cli(self, subparsers) -> None:
        return None
