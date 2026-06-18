"""Run one or many `.feature` files (shared by CLI and GUI)."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from app.feature_store import load_feature
from app.player import ScenarioPlayer
from app.run_status_store import record_run

ProgressCallback = Callable[[str], None]


def collect_feature_files(paths: list[Path]) -> list[Path]:
    files: list[Path] = []
    for path in paths:
        resolved = path.resolve()
        if resolved.is_dir():
            files.extend(sorted(resolved.rglob("*.feature")))
        elif resolved.is_file() and resolved.suffix.lower() == ".feature":
            files.append(resolved)
    return files


def run_feature_file(
    path: Path,
    *,
    headless: bool = True,
    slow_mo_ms: int = 0,
    on_log: ProgressCallback | None = None,
) -> dict[str, Any]:
    feature = load_feature(path)
    scenario = {
        "name": feature.get("name", path.stem),
        "startUrl": feature.get("startUrl", ""),
        "steps": feature.get("steps", []),
    }
    logs: list[str] = []
    result_holder: dict[str, Any] = {}

    def _log(message: str) -> None:
        logs.append(message)
        if on_log:
            on_log(message)

    def on_done(result: dict[str, Any]) -> None:
        result_holder.update(result)

    player = ScenarioPlayer()
    player.play(scenario, _log, on_done, headless=headless, slow_mo_ms=slow_mo_ms)
    thread = player._thread
    if thread is not None:
        thread.join(timeout=600)

    success = bool(result_holder.get("success"))
    message = str(result_holder.get("message", ""))
    record_run(path, success=success, message=message)
    return {
        "path": path,
        "name": path.stem,
        "classname": str(path.parent.name or "features"),
        "success": success,
        "message": message if not success else "ok",
        "details": "\n".join(logs[-20:]),
        "executed": int(result_holder.get("executed_count", 0)),
        "total": int(result_holder.get("total_count", 0)),
        "trace_path": result_holder.get("trace_path"),
        "screenshot_path": result_holder.get("screenshot_path"),
        "log_lines": list(logs),
    }


def run_feature_paths(
    paths: list[Path],
    *,
    headless: bool = True,
    slow_mo_ms: int = 0,
    on_log: ProgressCallback | None = None,
    on_case_start: Callable[[Path], None] | None = None,
    should_stop: Callable[[], bool] | None = None,
) -> list[dict[str, Any]]:
    files = collect_feature_files(paths)
    cases: list[dict[str, Any]] = []
    for path in files:
        if should_stop and should_stop():
            if on_log:
                on_log("\n=== Пакет остановлен пользователем ===")
            break
        if on_case_start:
            on_case_start(path)
        if on_log:
            on_log(f"\n=== {path.name} ===")
        cases.append(
            run_feature_file(path, headless=headless, slow_mo_ms=slow_mo_ms, on_log=on_log)
        )
    return cases


def format_suite_summary(cases: list[dict[str, Any]]) -> str:
    if not cases:
        return "Сценарии не найдены"
    failed = sum(1 for case in cases if not case.get("success"))
    ok = len(cases) - failed
    lines = [f"Итого: {ok} OK, {failed} FAIL из {len(cases)}"]
    for case in cases:
        mark = "OK" if case.get("success") else "FAIL"
        path = case.get("path")
        label = path.name if isinstance(path, Path) else str(case.get("name", "?"))
        if case.get("success"):
            lines.append(f"  [{mark}] {label} ({case.get('executed', 0)}/{case.get('total', 0)})")
        else:
            brief = str(case.get("message", "")).splitlines()[0][:100]
            lines.append(f"  [{mark}] {label}: {brief}")
    return "\n".join(lines)
