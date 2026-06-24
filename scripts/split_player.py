"""Player module layout reference after T8a/T8b split.

Run from repo root:
    python scripts/split_player.py

Modules:
    player.py              — public facade and re-exports
    player_types.py        — PlayResult, callbacks, PICK_CANCEL
    player_worker.py       — ScenarioPlayer thread, picker queue, browser session
    player_run.py          — run_scenario_on_page, validate_scenario_on_page
    player_trace.py        — failure screenshots and Playwright traces
    player_step_executor.py — execute_step dispatch
    player_step_helpers.py — OTP, locators, click helpers
    player_context.py      — RunContext, conditions, email resolve
    player_highlight.py    — element highlight overlay
    run_variables.py       — backward-compatible re-exports from player_context
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULES = [
    "app/player.py",
    "app/player_types.py",
    "app/player_worker.py",
    "app/player_run.py",
    "app/player_trace.py",
    "app/player_step_executor.py",
    "app/player_step_helpers.py",
    "app/player_context.py",
    "app/player_highlight.py",
]


def main() -> None:
    print("Player package layout (post T8b):")
    total = 0
    for rel in MODULES:
        path = ROOT / rel
        lines = len(path.read_text(encoding="utf-8").splitlines()) if path.is_file() else 0
        total += lines
        print(f"  {rel}: {lines}")
    print(f"  total: {total}")


if __name__ == "__main__":
    main()
