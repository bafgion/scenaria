"""Headless validation of `.feature` selector presence."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from playwright.sync_api import sync_playwright

from app.browser_config import browser_context_options, launch_browser
from app.feature_store import load_feature
from app.paths import configure_playwright_browsers
from app.selector_validate import (
    validate_results_to_issues,
    validate_results_to_payload,
    validate_scenario_selectors,
)

ProgressCallback = Callable[[str], None]


def validate_feature_file(
    path: Path,
    *,
    headless: bool = True,
    on_log: ProgressCallback | None = None,
    browser_engine: str | None = None,
) -> dict[str, Any]:
    feature = load_feature(path)
    scenario = {
        "name": feature.get("name", path.stem),
        "startUrl": feature.get("startUrl", ""),
        "steps": feature.get("steps", []),
    }
    if feature.get("testClient"):
        scenario["testClient"] = feature["testClient"]
    start_url = str(scenario.get("startUrl", "") or "")
    steps = scenario.get("steps") or []
    if not start_url and steps and steps[0].get("action") == "goto":
        start_url = str(steps[0].get("url", "") or "")

    from app.feature_store import resolve_project_root
    from app.scenario_test_client import ensure_scenario_test_client

    project_root = resolve_project_root()
    test_client = ensure_scenario_test_client(scenario, project_root)

    configure_playwright_browsers()
    results = []
    with sync_playwright() as playwright:
        browser = launch_browser(
            playwright,
            engine=browser_engine,
            headless=headless,
            on_status=on_log,
        )
        try:
            context = browser.new_context(
                **browser_context_options(
                    start_url,
                    headless=headless,
                    project_root=project_root,
                    test_client=test_client,
                )
            )
            page = context.new_page()
            results = validate_scenario_selectors(page, scenario, on_log=on_log)
        finally:
            browser.close()

    issues = validate_results_to_issues(results)
    return {
        "path": path,
        "name": path.stem,
        "success": len(issues) == 0,
        "issues": issues,
        "results": validate_results_to_payload(results),
    }


def validate_feature_paths(
    paths: list[Path],
    *,
    headless: bool = True,
    on_log: ProgressCallback | None = None,
    browser_engine: str | None = None,
) -> list[dict[str, Any]]:
    from app.run_suite import collect_feature_files

    files = collect_feature_files(paths)
    cases: list[dict[str, Any]] = []
    for path in files:
        if on_log:
            on_log(f"\n=== {path.name} ===")
        cases.append(
            validate_feature_file(
                path,
                headless=headless,
                on_log=on_log,
                browser_engine=browser_engine,
            )
        )
    return cases
