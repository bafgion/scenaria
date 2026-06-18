"""Recording controller edge cases."""

from __future__ import annotations

import app.mvc.controllers.recording_controller as recording_controller
from app.scenario_utils import ScenarioNotFoundError


def test_scenario_not_found_error_is_imported() -> None:
    assert recording_controller.ScenarioNotFoundError is ScenarioNotFoundError
