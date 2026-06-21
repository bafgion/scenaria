"""ScenarioPlayer lifecycle and completion semantics."""

from __future__ import annotations

import threading
import time
from pathlib import Path

import pytest

from app.player import ScenarioPlayer
from app.run_suite import run_feature_file

pytestmark = pytest.mark.integration


def _wait_player_stopped(player: ScenarioPlayer, *, timeout: float = 30.0) -> None:
    deadline = time.monotonic() + timeout
    while player.worker_alive and time.monotonic() < deadline:
        time.sleep(0.05)
    if player.worker_alive:
        player.stop()
        deadline = time.monotonic() + timeout
        while player.worker_alive and time.monotonic() < deadline:
            time.sleep(0.05)
    assert not player.worker_alive, "player worker did not stop"


def test_headless_run_feature_file_completes_without_close_browser(tmp_path: Path) -> None:
    feature = tmp_path / "blank.feature"
    feature.write_text(
        'Функционал: T\nСценарий: blank\n\tДопустим открыт "about:blank"\n',
        encoding="utf-8",
    )

    result = run_feature_file(feature, headless=True)

    assert result["success"] is True
    assert result["executed"] >= 0


def test_player_calls_on_done_while_worker_still_alive_for_visible_browser() -> None:
    player = ScenarioPlayer()
    done = threading.Event()
    results: list[dict] = []

    scenario = {
        "name": "blank",
        "startUrl": "about:blank",
        "steps": [{"action": "goto", "url": "about:blank"}],
    }

    def on_done(payload: dict) -> None:
        results.append(payload)
        done.set()

    player.play(scenario, lambda _msg: None, on_done, headless=False, slow_mo_ms=0)
    assert done.wait(timeout=60), "on_done was not called"
    assert results and results[0]["success"] is True
    assert player.worker_alive
    player.stop()
    assert not player.worker_alive


def test_player_worker_stays_alive_after_failure_until_stopped() -> None:
    player = ScenarioPlayer()
    done = threading.Event()
    results: list[dict] = []

    scenario = {
        "name": "fail",
        "startUrl": "about:blank",
        "steps": [
            {"action": "goto", "url": "about:blank"},
            {"action": "click", "selector": "#missing-element-xyz"},
        ],
    }

    def on_done(payload: dict) -> None:
        results.append(payload)
        done.set()

    player.play(scenario, lambda _msg: None, on_done, headless=False, slow_mo_ms=0)
    assert done.wait(timeout=60), "on_done was not called"
    assert results and not results[0]["success"]
    assert player.worker_alive
    player.stop()
    assert not player.worker_alive


def test_player_can_restart_after_failure() -> None:
    player = ScenarioPlayer()
    fail_done = threading.Event()
    ok_done = threading.Event()
    outcomes: list[bool] = []

    fail_scenario = {
        "name": "fail",
        "startUrl": "about:blank",
        "steps": [
            {"action": "goto", "url": "about:blank"},
            {"action": "click", "selector": "#missing-element-xyz"},
        ],
    }
    ok_scenario = {
        "name": "ok",
        "startUrl": "about:blank",
        "steps": [{"action": "goto", "url": "about:blank"}],
    }

    player.play(
        fail_scenario,
        lambda _msg: None,
        lambda payload: (outcomes.append(bool(payload.get("success"))), fail_done.set()),
        headless=False,
        slow_mo_ms=0,
    )
    assert fail_done.wait(timeout=60)
    assert outcomes[-1] is False
    assert player.worker_alive
    player.stop()
    _wait_player_stopped(player)

    player.play(
        ok_scenario,
        lambda _msg: None,
        lambda payload: (outcomes.append(bool(payload.get("success"))), ok_done.set()),
        headless=False,
        slow_mo_ms=0,
    )
    assert ok_done.wait(timeout=60)
    assert outcomes[-1] is True
    player.stop()
    _wait_player_stopped(player)
