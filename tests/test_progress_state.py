"""Tests for unified progress state."""

from __future__ import annotations

from app.progress_state import ProgressState


def test_progress_fraction() -> None:
    state = ProgressState(task_id="t", label="login.feature", current=2, total=5)
    assert state.fraction == 0.4
    assert state.step_label() == "login.feature (2/5)"


def test_progress_inactive_when_total_zero() -> None:
    state = ProgressState(task_id="t", label="idle", current=0, total=0)
    assert not state.active
