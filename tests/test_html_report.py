"""HTML report generation tests."""

from __future__ import annotations

from app.html_report import (
    render_run_report_html,
    run_report_from_play,
    write_run_report_html,
    write_suite_index_html,
)
from app.selector_validate import StepValidateResult, validate_results_to_issues


def test_run_report_from_play_with_step_results() -> None:
    scenario = {
        "name": "Login",
        "steps": [
            {"action": "goto", "url": "https://example.com"},
            {"action": "click", "selector": "button"},
        ],
    }
    result = {
        "success": False,
        "message": "timeout",
        "executed_count": 1,
        "total_count": 2,
        "failed_step_index": 1,
        "step_results": [
            {
                "index": 0,
                "action": "goto",
                "selector": "https://example.com",
                "success": True,
                "message": "",
                "duration_ms": 120,
            },
            {
                "index": 1,
                "action": "click",
                "selector": "button",
                "success": False,
                "message": "timeout",
                "duration_ms": 5000,
            },
        ],
        "log_lines": ["1. ok", "2. fail"],
    }
    report = run_report_from_play(scenario, result, duration_ms=5120)
    assert report.scenario_name == "Login"
    assert len(report.steps) == 2
    assert report.steps[1].success is False
    html = render_run_report_html(report)
    assert "Login" in html
    assert "button" in html


def test_write_suite_index_html(tmp_path) -> None:
    report = run_report_from_play(
        {"name": "A", "steps": []},
        {"success": True, "message": "ok", "step_results": []},
        duration_ms=10,
    )
    detail = write_run_report_html(report, tmp_path / "a.html")
    index = write_suite_index_html([(report, detail)], tmp_path / "index.html")
    assert index.is_file()
    assert "a.html" in index.read_text(encoding="utf-8")


def test_validate_results_to_issues_fragile_warning() -> None:
    issues = validate_results_to_issues(
        [
            StepValidateResult(2, "click", "div > button:nth-of-type(1)", "fragile", "хрупкий"),
        ]
    )
    assert any("хрупкий" in issue for issue in issues)
