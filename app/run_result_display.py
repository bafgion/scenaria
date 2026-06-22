"""Human-friendly labels for run history and results panels."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.run_status_store import RunHistoryEntry

RUN_SUCCESS_ICON = "✓"
RUN_FAIL_ICON = "✗"

_RUNNER_LABELS: dict[str, str] = {
    "playwright": "Playwright",
    "vanessa": "Vanessa Automation",
}


def format_runner_label(runner: str | None) -> str:
    key = (runner or "playwright").strip().lower()
    return _RUNNER_LABELS.get(key, (runner or "Playwright").strip() or "Playwright")


def format_run_status_text(success: bool) -> str:
    if success:
        return f"{RUN_SUCCESS_ICON} Успех"
    return f"{RUN_FAIL_ICON} Ошибка"


def format_failed_step_label(failed_step: int | None) -> str:
    if failed_step is None:
        return "—"
    return f"Шаг {failed_step}"


def brief_error_message(message: str, *, limit: int = 240) -> str:
    if not message:
        return "—"
    brief = message.splitlines()[0].strip()
    if len(brief) > limit:
        return brief[: limit - 3] + "..."
    return brief or "—"


def summarize_run_history(entries: list[RunHistoryEntry]) -> str:
    if not entries:
        return "Прогонов пока не было — запустите сценарий, чтобы увидеть историю."
    ok = sum(1 for entry in entries if entry.success)
    fail = len(entries) - ok
    parts = [f"Записей: {len(entries)}"]
    if ok:
        parts.append(f"{RUN_SUCCESS_ICON} {ok}")
    if fail:
        parts.append(f"{RUN_FAIL_ICON} {fail}")
    return " · ".join(parts)


def summarize_suite_cases(cases: list[dict[str, Any]], *, live: bool = False) -> str:
    row_count = len(cases)
    if row_count == 0:
        prefix = "Прогон выполняется" if live else "Итог"
        return f"{prefix}: сценариев пока нет"
    failed = sum(1 for case in cases if not case.get("success"))
    ok = row_count - failed
    prefix = "Прогон выполняется" if live else "Итог"
    status = f"{RUN_SUCCESS_ICON} {ok}" if ok else ""
    if failed:
        status_part = f"{status} · {RUN_FAIL_ICON} {failed}" if status else f"{RUN_FAIL_ICON} {failed}"
    else:
        status_part = status or f"{RUN_SUCCESS_ICON} 0"
    return f"{prefix}: {status_part} — показано {row_count}"


def format_single_run_summary(payload: dict[str, Any]) -> str:
    success = bool(payload.get("success"))
    parts = [format_run_status_text(success)]
    duration_ms = int(payload.get("duration_ms", 0))
    if duration_ms > 0:
        from app.run_display import format_duration

        parts.append(format_duration(duration_ms))
    runner = payload.get("runner")
    if runner and str(runner).lower() != "playwright":
        parts.append(format_runner_label(str(runner)))
    failed_step = payload.get("failed_step")
    if failed_step is not None and not success:
        parts.append(format_failed_step_label(int(failed_step)))
    message = str(payload.get("message", "") or "")
    if message and not success:
        parts.append(brief_error_message(message, limit=120))
    return " · ".join(parts)
