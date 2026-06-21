"""Tests for runner plugin models."""

from __future__ import annotations

from pathlib import Path

from app.plugins.models import RunBatchResult, RunCaseResult, RunMode, RunRequest


def test_run_request_tag_property() -> None:
    request = RunRequest(tags=["@smoke"])
    assert request.tag == "smoke"
    assert RunRequest().tag is None


def test_run_case_result_roundtrip() -> None:
    case = RunCaseResult(
        path=Path("demo.feature"),
        name="demo",
        classname="features",
        success=True,
        message="ok",
        executed=3,
        total=3,
        duration_ms=1200,
    )
    restored = RunCaseResult.from_dict(case.to_dict())
    assert restored.path == case.path
    assert restored.success is True
    assert restored.executed == 3


def test_run_batch_result_legacy_cases() -> None:
    batch = RunBatchResult(
        runner="playwright",
        success=True,
        cases=[
            RunCaseResult(
                path=Path("a.feature"),
                name="a",
                classname="features",
                success=True,
                message="ok",
            )
        ],
        duration_ms=500,
    )
    legacy = batch.to_legacy_cases()
    assert len(legacy) == 1
    assert legacy[0]["success"] is True
    assert legacy[0]["path"] == Path("a.feature")


def test_run_mode_values() -> None:
    assert RunMode.FILES.value == "files"
