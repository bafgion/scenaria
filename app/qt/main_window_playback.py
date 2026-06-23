"""Playback, validation, and batch result handlers for MainWindow (T7-1)."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from app.feature_store import get_root
from app.settings import load_settings, save_settings

if TYPE_CHECKING:
    from app.qt.main_window import MainWindow


class MainWindowPlaybackMixin:
    def _on_play_step(self: MainWindow, index: int) -> None:
        self.workspace.clear_play_highlight()
        self.workspace.highlight_play_step(index)

    def _on_focus_failed(self: MainWindow, index: int) -> None:
        self.workspace.mark_failed_step(index)
        display = index + 1
        self._show_error_for_step(index, display_index=display)
        self._show_bottom_panel("error")

    def _show_error_for_step(
        self: MainWindow,
        step_index: int,
        *,
        display_index: int | None = None,
    ) -> None:
        steps = self._controller.scenario.steps
        step = steps[step_index] if 0 <= step_index < len(steps) else {}
        selector = str(step.get("selector") or step.get("url") or "")
        self.bottom_panel.error_panel.show_failure(
            step_index=display_index if display_index is not None else step_index + 1,
            selector=selector,
            message="Шаг не выполнен — см. журнал и результаты",
            screenshot_path=None,
        )

    def _on_validation_results(self: MainWindow, payload: dict) -> None:
        self.bottom_panel.validate_panel.show_results(payload)
        self.workspace.show_editor()
        self._show_bottom_panel("validate")

    def _on_validate_step_focus(self: MainWindow, step_index: int) -> None:
        self.workspace.show_editor()
        payload = self.bottom_panel.validate_panel.results_as_payload()
        status = ""
        for item in payload.get("results", []):
            if int(item.get("step_index", 0)) == step_index:
                status = str(item.get("status", "") or "")
                break
        failed = status not in {"", "ok", "fragile", "skipped"}
        self.workspace.gherkin_panel.highlight_step(step_index, failed=failed)

    def _on_play_results(self: MainWindow, payload: dict, _duration_ms: int) -> None:
        has_failed = self._controller.session.last_failed_step_index is not None
        if not has_failed:
            settings = load_settings()
            if not settings.get("first_run_checklist_done"):
                settings["first_run_checklist_done"] = True
                save_settings(settings)
                self._sync_welcome_checklist()
        self.bottom_panel.results_panel.show_results(payload, has_failed_step=has_failed)
        self.workspace.clear_play_highlight()
        if has_failed:
            idx = int(self._controller.session.last_failed_step_index or -1)
            self.workspace.mark_failed_step(idx)
            steps = self._controller.scenario.steps
            step = steps[idx] if 0 <= idx < len(steps) else {}
            selector = str(step.get("selector") or step.get("url") or "")
            display = int(payload.get("failed_step") or (idx + 1 if idx >= 0 else 0))
            self.bottom_panel.error_panel.show_failure(
                step_index=display,
                selector=selector,
                message=str(payload.get("message", "")),
                screenshot_path=payload.get("screenshot_path"),
                trace_path=payload.get("trace_path"),
            )
            self._show_bottom_panel("error")
        else:
            self.bottom_panel.error_panel.clear()
            self._show_bottom_panel("results")
        self._maybe_open_html_report(payload)

    def _maybe_open_html_report(self: MainWindow, payload: dict) -> None:
        if not load_settings().get("open_html_report_after_run", False):
            return
        from app.report_locator import ReportTarget, find_latest_report

        hints = {
            "html_report_path": payload.get("html_report_path"),
            "suite_html_index": payload.get("suite_html_index"),
            "allure_dir": payload.get("allure_dir"),
        }
        target = find_latest_report(hints=hints, project_root=get_root())
        if target is None:
            report_path = payload.get("html_report_path") or payload.get("suite_html_index")
            if report_path:
                path = Path(str(report_path))
                if path.is_file():
                    target = ReportTarget("html", path)
        if target is not None:
            self._open_report_target(target)

    def _on_batch_results(self: MainWindow, payload: dict, _duration_ms: int) -> None:
        self.bottom_panel.results_panel.show_results(payload, has_failed_step=not payload.get("success"))
        self.bottom_panel.error_panel.clear()
        self._show_bottom_panel("results")
        self._maybe_open_html_report(payload)

    def _on_batch_partial_results(self: MainWindow, payload: dict) -> None:
        if str(payload.get("runner", "") or "") != "vanessa":
            return
        panel = self.bottom_panel.results_panel
        total_hint = int(payload.get("total", 0) or 0)
        if payload.get("bootstrap"):
            panel.begin_live_suite(total_hint=total_hint)
            self._show_bottom_panel("results")
            return
        cases = list(payload.get("cases") or [])
        if not cases:
            return
        panel.update_suite_cases(cases)
        self._show_bottom_panel("results")
