"""Build rerun requests from failed JUnit results."""

from __future__ import annotations

from pathlib import Path

from app.plugins.models import RunMode, RunRequest

from scenaria_vanessa.report_parsers import (
    failed_scenarios_from_junit,
    junit_dir_from_params,
    load_merged_params,
)


def build_rerun_request(
    *,
    project_root: Path | None,
    paths: list[Path],
    run_dir: Path,
    tags: list[str] | None = None,
    exclude_tags: list[str] | None = None,
    runner_options: dict | None = None,
) -> RunRequest | None:
    merged = load_merged_params(run_dir)
    junit_dir = junit_dir_from_params(merged) or (run_dir / "junit")
    failed = failed_scenarios_from_junit(junit_dir) if junit_dir.is_dir() else []
    if not failed:
        return None

    scenario_names = sorted({item.scenario_name for item in failed if item.scenario_name})
    feature_paths = sorted(
        {item.feature_path.resolve() for item in failed if item.feature_path is not None},
        key=lambda p: str(p).lower(),
    )
    if not feature_paths:
        feature_paths = list(paths)

    return RunRequest(
        mode=RunMode.FILES,
        paths=feature_paths or paths,
        project_root=project_root,
        tags=list(tags or []),
        exclude_tags=list(exclude_tags or []),
        scenario_names=scenario_names,
        runner_options=dict(runner_options or {}),
    )
