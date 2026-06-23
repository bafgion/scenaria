"""Run one or many `.feature` files (shared by CLI and GUI)."""



from __future__ import annotations



import threading

import time

from concurrent.futures import ThreadPoolExecutor, as_completed

from dataclasses import dataclass

from pathlib import Path

from typing import Any, Callable



from app.feature_store import load_feature

from app.gherkin_context import parse_feature_test_client
from app.gherkin_ru import gherkin_to_steps
from app.gherkin_outline import expand_outline_steps, parse_outline

from app.mvc.models.catalog_model import collect_feature_paths_with_tag, feature_has_tag

from app.player import ScenarioPlayer

from app.run_status_store import record_run

from app.settings import load_settings



ProgressCallback = Callable[[str], None]





@dataclass(frozen=True)

class FeatureRunCase:

    path: Path

    label: str

    steps: list[dict[str, Any]]

    start_url: str

    test_client: str | None = None

    example_index: int | None = None

    variables: dict[str, str] | None = None

    params_index: int | None = None





def _merge_case_variables(
    case: FeatureRunCase,
    variables: dict[str, str] | None,
) -> dict[str, str] | None:

    merged = dict(variables or {})

    if case.variables:

        merged.update(case.variables)

    return merged or None





def _case_log_title(case: FeatureRunCase) -> str:

    if case.example_index or case.params_index:

        return case.label

    return case.path.name





def collect_feature_files(paths: list[Path]) -> list[Path]:

    files: list[Path] = []

    for path in paths:

        resolved = path.resolve()

        if resolved.is_dir():

            files.extend(sorted(resolved.rglob("*.feature")))

        elif resolved.is_file() and resolved.suffix.lower() == ".feature":

            files.append(resolved)

    return files





def infer_project_root(paths: list[Path]) -> Path | None:

    resolved = [Path(p).resolve() for p in paths]

    dirs = [p for p in resolved if p.is_dir()]

    if len(resolved) == 1 and dirs:

        return dirs[0]

    if len(dirs) == 1:

        return dirs[0]

    files = [p for p in resolved if p.is_file()]

    if files:

        parents = {p.parent for p in files}

        if len(parents) == 1:

            return next(iter(parents))

    return dirs[0] if dirs else None





def resolve_feature_files(paths: list[Path], *, tag: str | None = None) -> list[Path]:

    tag_norm = (tag or "").strip().lstrip("@")

    if not tag_norm:

        return collect_feature_files(paths)



    result: list[Path] = []

    seen: set[str] = set()

    for path in paths:

        resolved = path.resolve()

        if resolved.is_dir():

            for item in collect_feature_paths_with_tag(resolved, tag_norm):

                key = str(item)

                if key not in seen:

                    seen.add(key)

                    result.append(item)

        elif resolved.is_file() and resolved.suffix.lower() == ".feature":

            if feature_has_tag(resolved, tag_norm):

                key = str(resolved)

                if key not in seen:

                    seen.add(key)

                    result.append(resolved)

    return sorted(result, key=lambda p: str(p).lower())





def _expand_cases_with_params(cases: list[FeatureRunCase], path: Path) -> list[FeatureRunCase]:

    from app.scenario_params import load_param_cases

    param_cases = load_param_cases(path)

    if not param_cases:

        return cases

    expanded: list[FeatureRunCase] = []

    for base in cases:

        for pindex, param in enumerate(param_cases, start=1):

            label = f"{base.label} — {param.label}" if param.label else base.label

            expanded.append(

                FeatureRunCase(

                    path=base.path,

                    label=label,

                    steps=base.steps,

                    start_url=base.start_url,

                    test_client=base.test_client,

                    example_index=base.example_index,

                    variables=dict(param.variables),

                    params_index=pindex,

                )

            )

    return expanded





def _start_url_from_steps(steps: list[dict[str, Any]]) -> str:
    for step in steps:
        if step.get("action") == "goto":
            url = str(step.get("url", "") or "").strip()
            if url:
                return url
    return ""


def expand_feature_cases_from_text(text: str, path: Path) -> list[FeatureRunCase]:
    test_client = parse_feature_test_client(text)
    outline = parse_outline(text)
    if outline is None:
        steps = gherkin_to_steps(text)
        return _expand_cases_with_params(
            [
                FeatureRunCase(
                    path=path,
                    label=path.stem,
                    steps=list(steps),
                    start_url=_start_url_from_steps(steps),
                    test_client=test_client,
                )
            ],
            path,
        )

    cases: list[FeatureRunCase] = []
    for index, row in enumerate(outline.rows, start=1):
        steps = expand_outline_steps(outline.template_steps, row)
        start_url = _start_url_from_steps(steps)
        sample = next((value for value in row.values() if str(value).strip()), "")
        label = f"{path.stem} ({index})"
        if sample:
            label = f"{path.stem} — {sample}"
        cases.append(
            FeatureRunCase(
                path=path,
                label=label,
                steps=steps,
                start_url=start_url,
                test_client=test_client,
                example_index=index,
            )
        )
    return _expand_cases_with_params(cases, path)


def feature_case_to_scenario(case: FeatureRunCase) -> dict[str, Any]:
    scenario: dict[str, Any] = {
        "name": case.label,
        "startUrl": case.start_url,
        "steps": list(case.steps),
    }
    if case.test_client:
        scenario["testClient"] = case.test_client
    if case.variables:
        scenario["variables"] = dict(case.variables)
    return scenario


def collect_play_scenarios(
    path: Path | None,
    *,
    text: str | None = None,
) -> list[dict[str, Any]]:
    """Expand outline/examples and .params.json into runnable scenario dicts."""
    if text is None:
        if path is None or not path.is_file():
            raise FileNotFoundError("Нет файла сценария для прогона")
        text = path.read_text(encoding="utf-8")
    resolved_path = path if path is not None else Path("scenario.feature")
    return [feature_case_to_scenario(case) for case in expand_feature_cases_from_text(text, resolved_path)]


def expand_feature_cases(path: Path) -> list[FeatureRunCase]:
    text = path.read_text(encoding="utf-8")
    return expand_feature_cases_from_text(text, path)





def collect_run_cases(paths: list[Path], *, tag: str | None = None) -> list[FeatureRunCase]:

    cases: list[FeatureRunCase] = []

    for path in resolve_feature_files(paths, tag=tag):

        cases.extend(expand_feature_cases(path))

    return cases





def run_feature_file(

    path: Path,

    *,

    headless: bool = True,

    slow_mo_ms: int = 0,

    on_log: ProgressCallback | None = None,

    project_root: Path | None = None,

    browser_engine: str | None = None,

    variables: dict[str, str] | None = None,

    runner: str = "playwright",

    steps: list[dict[str, Any]] | None = None,

    case_label: str | None = None,

    example_index: int | None = None,

) -> dict[str, Any]:

    if steps is None:

        feature = load_feature(path)

        resolved_steps = list(feature.get("steps", []) or [])

        start_url = str(feature.get("startUrl", "") or "")

        name = case_label or str(feature.get("name", path.stem))

    else:

        resolved_steps = list(steps)

        start_url = ""

        for step in resolved_steps:

            if step.get("action") == "goto":

                start_url = str(step.get("url", "") or "").strip()

                if start_url:

                    break

        name = case_label or path.stem



    scenario = {

        "name": name,

        "startUrl": start_url,

        "steps": resolved_steps,

    }

    if browser_engine:

        scenario["browserEngine"] = browser_engine

    if variables:

        scenario["variables"] = dict(variables)

    logs: list[str] = []

    result_holder: dict[str, Any] = {}

    started = time.perf_counter()



    def _log(message: str) -> None:

        logs.append(message)

        if on_log:

            on_log(message)



    def on_done(result: dict[str, Any]) -> None:

        result_holder.update(result)



    player = ScenarioPlayer()

    player.play(

        scenario,

        _log,

        on_done,

        headless=headless,

        slow_mo_ms=slow_mo_ms,

        project_root=project_root,

    )

    thread = player._thread

    if thread is not None:

        thread.join(timeout=600)



    duration_ms = int((time.perf_counter() - started) * 1000)

    success = bool(result_holder.get("success"))

    message = str(result_holder.get("message", ""))

    failed_step = result_holder.get("failed_step")

    record_run(

        path,

        success=success,

        message=message,

        duration_ms=duration_ms,

        failed_step=int(failed_step) if failed_step is not None else None,

        runner=runner,

    )

    return {

        "path": path,

        "name": name,

        "classname": str(path.parent.name or "features"),

        "success": success,

        "message": message if not success else "ok",

        "details": "\n".join(logs[-20:]),

        "executed": int(result_holder.get("executed_count", 0)),

        "total": int(result_holder.get("total_count", 0)),

        "trace_path": result_holder.get("trace_path"),

        "screenshot_path": result_holder.get("screenshot_path"),

        "log_lines": list(logs),

        "step_results": list(result_holder.get("step_results") or []),

        "duration_ms": duration_ms,

        "failed_step": failed_step,

        "example_index": example_index,

    }





def _parallel_workers() -> int:

    raw = load_settings().get("parallel_workers", 1)

    try:

        workers = int(raw)

    except (TypeError, ValueError):

        workers = 1

    return max(1, min(workers, 8))





def run_feature_paths(

    paths: list[Path],

    *,

    headless: bool = True,

    slow_mo_ms: int = 0,

    on_log: ProgressCallback | None = None,

    on_case_start: Callable[[Path], None] | None = None,

    should_stop: Callable[[], bool] | None = None,

    tag: str | None = None,

    project_root: Path | None = None,

    browser_engine: str | None = None,

    variables: dict[str, str] | None = None,

    runner: str = "playwright",

) -> list[dict[str, Any]]:

    root = project_root or infer_project_root(paths)

    run_cases = collect_run_cases(paths, tag=tag)

    workers = _parallel_workers()

    cases: list[dict[str, Any]] = []

    log_lock = threading.Lock()



    def _thread_log(message: str) -> None:

        if not on_log:

            return

        with log_lock:

            on_log(message)



    if workers <= 1 or len(run_cases) <= 1:

        for case in run_cases:

            if should_stop and should_stop():

                if on_log:

                    on_log("\n=== Пакет остановлен пользователем ===")

                break

            if on_case_start:

                on_case_start(case.path)

            if on_log:

                title = _case_log_title(case)

                on_log(f"\n=== {title} ===")

            cases.append(

                run_feature_file(

                    case.path,

                    headless=headless,

                    slow_mo_ms=slow_mo_ms,

                    on_log=on_log,

                    project_root=root,

                    browser_engine=browser_engine,

                    variables=_merge_case_variables(case, variables),

                    runner=runner,

                    steps=case.steps,

                    case_label=case.label,

                    example_index=case.example_index,

                )

            )

        return cases



    completed = 0

    total = len(run_cases)

    stop_event = threading.Event()



    def _run_case(case: FeatureRunCase) -> dict[str, Any]:

        if stop_event.is_set() or (should_stop and should_stop()):

            stop_event.set()

            return {

                "path": case.path,

                "name": case.label,

                "classname": str(case.path.parent.name or "features"),

                "success": False,

                "message": "Остановлено пользователем",

                "details": "",

                "executed": 0,

                "total": 0,

                "trace_path": None,

                "screenshot_path": None,

                "log_lines": [],

                "step_results": [],

                "duration_ms": 0,

                "failed_step": None,

                "example_index": case.example_index,

            }

        _thread_log(f"\n=== [worker] {case.label} ===")

        return run_feature_file(

            case.path,

            headless=headless,

            slow_mo_ms=slow_mo_ms,

            on_log=_thread_log,

            project_root=root,

            browser_engine=browser_engine,

            variables=_merge_case_variables(case, variables),

            runner=runner,

            steps=case.steps,

            case_label=case.label,

            example_index=case.example_index,

        )



    with ThreadPoolExecutor(max_workers=workers) as pool:

        futures = {pool.submit(_run_case, case): case for case in run_cases}

        result_by_label: dict[str, dict[str, Any]] = {}

        for future in as_completed(futures):

            case = futures[future]

            if on_case_start:

                on_case_start(case.path)

            result = future.result()

            result_by_label[case.label] = result

            completed += 1

            if on_log:

                with log_lock:

                    on_log(f"\n--- Прогресс: {completed}/{total} ({case.label}) ---")

            if should_stop and should_stop():

                stop_event.set()

                if on_log:

                    with log_lock:

                        on_log("\n=== Пакет остановлен пользователем ===")

                break



    for case in run_cases:

        item = result_by_label.get(case.label)

        if item is not None:

            cases.append(item)

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

        label = case.get("name") if case.get("example_index") else None

        if not label:

            label = path.name if isinstance(path, Path) else str(case.get("name", "?"))

        if case.get("success"):

            lines.append(f"  [{mark}] {label} ({case.get('executed', 0)}/{case.get('total', 0)})")

        else:

            brief = str(case.get("message", "")).splitlines()[0][:100]

            lines.append(f"  [{mark}] {label}: {brief}")

    return "\n".join(lines)

