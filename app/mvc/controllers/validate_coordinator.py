"""Selector validate flow (T3-2)."""

from __future__ import annotations

from typing import Any

from app.mvc.controller_host import RecordingControllerHost
from app.scenario_utils import ScenarioNotFoundError


class ValidateCoordinatorMixin:
    """Selector validate flow (T3-2)."""

    def validate_current(self: RecordingControllerHost) -> None:
        bridge = self._bridge_ref()
        try:
            scenario = self._scenario_controller.current_scenario_dict()
        except ScenarioNotFoundError:
            self.log.emit("Нет сценария для проверки", "error")
            return
        if not self._recorder.browser_open:
            self.log.emit("Откройте браузер для проверки селекторов", "error")
            return
        self._set_pending(True, "Проверка сценария...")
        self._recorder.validate_scenario(
            scenario,
            lambda message: bridge.emit_event("play_log", message),
            on_complete=lambda payload: bridge.emit_event("validation_done", payload),
            on_error=lambda exc: bridge.emit_event("error", str(exc)),
            on_status=self._recorder_status,
        )

    def _on_validation_done(self: RecordingControllerHost, payload: dict[str, Any] | list[str]) -> None:
        if isinstance(payload, list):
            payload = {"issues": payload, "results": []}
        issues = list(payload.get("issues") or [])
        self._set_pending(False)
        if issues:
            self.log.emit(f"Проверка: найдено проблем — {len(issues)}", "error")
            for issue in issues:
                self.log.emit(f"  • {issue}", "error")
            self.status.emit(f"Проблем: {len(issues)}", "error")
        else:
            self.log.emit("Проверка пройдена — селекторы найдены", "success")
            self.status.emit("Сценарий готов к запуску", "success")
        self.validation_results.emit({"issues": issues, "results": list(payload.get("results") or [])})
