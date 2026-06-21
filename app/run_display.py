"""Format play results for the UI."""

from __future__ import annotations

from typing import Any

from app.step_display import format_step_line


def format_duration(ms: int) -> str:
    if ms < 1000:
        return f"{ms} мс"
    seconds = ms / 1000
    if seconds < 60:
        return f"{seconds:.1f} с"
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{minutes} мин {secs} с"


def format_run_at(iso: str) -> str:
    if not iso:
        return ""
    try:
        from datetime import datetime

        normalized = iso.replace("Z", "+00:00")
        dt = datetime.fromisoformat(normalized)
        if dt.tzinfo is not None:
            dt = dt.astimezone()
        return dt.strftime("%d.%m.%Y %H:%M")
    except ValueError:
        return iso[:16]


def format_last_run_summary(
    *,
    success: bool | None,
    at: str = "",
    duration_ms: int = 0,
    failed_step: int | None = None,
    message: str = "",
    runner: str = "",
) -> str:
    if success is None:
        return "Прогон не выполнялся"
    result = "успех" if success else "ошибка"
    parts = [f"Последний: {result}"]
    if runner and runner != "playwright":
        parts.append(f"runner: {runner}")
    if duration_ms > 0:
        parts.append(format_duration(duration_ms))
    when = format_run_at(at)
    if when:
        parts.append(when)
    if failed_step is not None and not success:
        parts.append(f"шаг {failed_step}")
    if message and not success:
        brief = message.splitlines()[0][:80]
        parts.append(brief)
    return ", ".join(parts)


def format_run_diff(recorded_steps: list[dict[str, Any]], result: dict[str, Any]) -> str:
    recorded = len(recorded_steps)
    executed = int(result.get("executed_count", 0))
    playable = int(result.get("total_count", 0))
    skipped = int(result.get("skipped_count", max(0, recorded - playable)))

    lines: list[str] = []
    if skipped > 0:
        lines.append(f"Шагов в сценарии: {recorded} (пропущено при запуске: {skipped})")
    else:
        lines.append(f"Шагов в сценарии: {recorded}")
    lines.append(f"Выполнено: {executed} из {playable}")

    failed_display = result.get("failed_step")
    failed_index = result.get("failed_step_index")
    if failed_display is not None:
        lines.append(f"Ошибка на шаге: {failed_display}")
        step: dict[str, Any] | None = None
        if failed_index is not None:
            idx = int(failed_index)
            if 0 <= idx < len(recorded_steps):
                step = recorded_steps[idx]
        elif 0 < int(failed_display) <= len(recorded_steps):
            step = recorded_steps[int(failed_display) - 1]
        if step is not None:
            lines.append(f"  → {format_step_line(int(failed_display), step)}")
    if executed < playable and failed_display is None:
        lines.append(f"Остановлено на шаге {executed + 1} из {playable}")
    if result.get("screenshot_path"):
        lines.append(f"Скриншот: {result['screenshot_path']}")
    success = bool(result.get("success"))
    lines.append("Статус: успех" if success else f"Статус: ошибка — {result.get('message', '')}")
    return "\n".join(lines)


def compare_run_with_recording(recorded_steps: list[dict[str, Any]], result: dict[str, Any]) -> str:
    return format_run_diff(recorded_steps, result)
