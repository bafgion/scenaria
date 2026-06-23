"""Resolve TestClient for scenario playback."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from app.test_clients import TestClientNotFoundError, require_test_client


def scenario_test_client_name(scenario: dict[str, Any]) -> str | None:
    if "testClient" not in scenario:
        return None
    value = scenario.get("testClient")
    if value is None:
        return None
    name = str(value).strip()
    return name or None


def ensure_scenario_test_client(
    scenario: dict[str, Any],
    project_root: Path | None = None,
) -> str | None:
    """Return client name to load, or ``None`` for a clean session. Raises if client is missing."""
    name = scenario_test_client_name(scenario)
    if name is None:
        return None
    require_test_client(name, project_root)
    return name
