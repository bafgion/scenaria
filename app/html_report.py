"""HTML run reports for single scenarios and batch suites."""

from __future__ import annotations

import base64
import html
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.step_display import format_step_table_cells
from app.qt.theme import (
    COLOR_BG,
    COLOR_BORDER,
    COLOR_ERROR,
    COLOR_MUTED,
    COLOR_SUCCESS,
    COLOR_TEXT,
)


@dataclass
class StepRunResult:
    index: int
    action: str
    success: bool
    message: str
    duration_ms: int
    selector: str = ""
    screenshot_path: str | None = None


@dataclass
class RunReport:
    scenario_name: str
    feature_path: str | None
    started_at: str
    duration_ms: int
    success: bool
    message: str
    steps: list[StepRunResult] = field(default_factory=list)
    trace_path: str | None = None
    screenshot_path: str | None = None
    log_lines: list[str] = field(default_factory=list)


def _step_selector_summary(step: dict[str, Any]) -> str:
    action = str(step.get("action", "") or "")
    if action == "goto":
        return str(step.get("url", "") or "")
    if action == "assert_url":
        return str(step.get("url", "") or "")
    return str(step.get("selector", "") or step.get("value", "") or "")


def run_report_from_play(
    scenario: dict[str, Any],
    result: dict[str, Any],
    *,
    started_at: datetime | None = None,
    feature_path: str | Path | None = None,
    duration_ms: int | None = None,
) -> RunReport:
    started = started_at or datetime.now(timezone.utc)
    raw_steps = list(result.get("step_results") or [])
    steps: list[StepRunResult] = []
    if raw_steps:
        for item in raw_steps:
            if not isinstance(item, dict):
                continue
            steps.append(
                StepRunResult(
                    index=int(item.get("index", item.get("step_index", 0))),
                    action=str(item.get("action", "") or ""),
                    success=bool(item.get("success", False)),
                    message=str(item.get("message", "") or ""),
                    duration_ms=int(item.get("duration_ms", 0)),
                    selector=str(item.get("selector", "") or ""),
                    screenshot_path=item.get("screenshot_path"),
                )
            )
    else:
        playable = list(scenario.get("steps") or [])
        executed = int(result.get("executed_count", 0))
        failed_index = result.get("failed_step_index")
        for index, step in enumerate(playable):
            action = str(step.get("action", "") or "")
            success = failed_index is None or index < int(failed_index)
            message = ""
            if not success and index == int(failed_index):
                message = str(result.get("message", "") or "")
            steps.append(
                StepRunResult(
                    index=index,
                    action=action,
                    success=success,
                    message=message,
                    duration_ms=0,
                    selector=_step_selector_summary(step),
                    screenshot_path=result.get("screenshot_path") if not success else None,
                )
            )
        if executed < len(steps) and failed_index is None:
            for step in steps[executed:]:
                step.success = False
                step.message = "не выполнен"

    path_str = str(feature_path) if feature_path else None
    return RunReport(
        scenario_name=str(scenario.get("name", "") or "Сценарий"),
        feature_path=path_str,
        started_at=started.astimezone().isoformat(timespec="seconds"),
        duration_ms=int(duration_ms if duration_ms is not None else 0),
        success=bool(result.get("success")),
        message=str(result.get("message", "") or ""),
        steps=steps,
        trace_path=result.get("trace_path"),
        screenshot_path=result.get("screenshot_path"),
        log_lines=list(result.get("log_lines") or []),
    )


def _encode_image(path: str | None) -> str | None:
    if not path:
        return None
    file_path = Path(path)
    if not file_path.is_file():
        return None
    try:
        data = base64.b64encode(file_path.read_bytes()).decode("ascii")
    except OSError:
        return None
    suffix = file_path.suffix.lower()
    mime = "image/png" if suffix == ".png" else "image/jpeg"
    return f"data:{mime};base64,{data}"


def render_run_report_html(report: RunReport) -> str:
    status = "Успех" if report.success else "Ошибка"
    status_color = COLOR_SUCCESS if report.success else COLOR_ERROR
    title = html.escape(report.scenario_name)
    feature = html.escape(report.feature_path or "—")
    started = html.escape(report.started_at)
    duration = html.escape(f"{report.duration_ms} мс")
    message = html.escape(report.message)

    rows: list[str] = []
    for step in report.steps:
        step_dict: dict[str, Any] = {"action": step.action}
        if step.action in {"goto", "assert_url"}:
            step_dict["url"] = step.selector
        else:
            step_dict["selector"] = step.selector
        label, target, value = format_step_table_cells(step_dict)
        display_target = target or value or step.selector or "—"
        status_icon = "✓" if step.success else "✗"
        row_class = "ok" if step.success else "fail"
        rows.append(
            "<tr class='{cls}'>"
            f"<td>{step.index + 1}</td>"
            f"<td>{html.escape(label)}</td>"
            f"<td class='mono'>{html.escape(display_target)}</td>"
            f"<td>{status_icon}</td>"
            f"<td>{step.duration_ms} мс</td>"
            f"<td>{html.escape(step.message)}</td>"
            "</tr>".format(cls=row_class)
        )

    screenshot_data = _encode_image(report.screenshot_path)
    screenshot_block = ""
    if screenshot_data:
        screenshot_block = (
            f"<h2>Скриншот ошибки</h2>"
            f"<img class='shot' src='{screenshot_data}' alt='screenshot'/>"
        )

    trace_block = ""
    if report.trace_path:
        trace_block = (
            f"<p>Trace: <code>{html.escape(report.trace_path)}</code></p>"
        )

    log_block = ""
    if report.log_lines:
        log_text = html.escape("\n".join(report.log_lines[-60:]))
        log_block = f"<h2>Журнал</h2><pre class='log'>{log_text}</pre>"

    return f"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>{title} — Scenaria</title>
<style>
body {{ margin: 0; font-family: "Segoe UI", sans-serif; background: {COLOR_BG}; color: {COLOR_TEXT}; }}
.wrap {{ max-width: 1100px; margin: 0 auto; padding: 24px; }}
h1 {{ margin: 0 0 8px; font-size: 20pt; }}
.meta {{ color: {COLOR_MUTED}; margin-bottom: 20px; line-height: 1.5; }}
.badge {{ display: inline-block; padding: 4px 10px; border-radius: 4px; background: {status_color}; color: #111; font-weight: 600; }}
table {{ width: 100%; border-collapse: collapse; font-size: 10pt; }}
th, td {{ border: 1px solid {COLOR_BORDER}; padding: 6px 8px; text-align: left; vertical-align: top; }}
th {{ background: #2d2d2d; }}
tr.ok td:nth-child(4) {{ color: {COLOR_SUCCESS}; }}
tr.fail {{ background: #3a2222; }}
tr.fail td:nth-child(4) {{ color: {COLOR_ERROR}; font-weight: 600; }}
.mono {{ font-family: Consolas, monospace; font-size: 9pt; word-break: break-all; }}
.shot {{ max-width: 100%; border: 1px solid {COLOR_BORDER}; border-radius: 4px; }}
.log {{ background: #111; border: 1px solid {COLOR_BORDER}; padding: 12px; overflow: auto; font-size: 9pt; }}
code {{ color: #9cdcfe; }}
</style>
</head>
<body>
<div class="wrap">
<h1>{title}</h1>
<div class="meta">
<span class="badge">{status}</span><br/>
Файл: <code>{feature}</code><br/>
Старт: {started} · Длительность: {duration}<br/>
{message}
</div>
<h2>Шаги</h2>
<table>
<thead><tr><th>#</th><th>Действие</th><th>Цель</th><th></th><th>Время</th><th>Сообщение</th></tr></thead>
<tbody>
{"".join(rows) if rows else "<tr><td colspan='6'>Нет данных по шагам</td></tr>"}
</tbody>
</table>
{screenshot_block}
{trace_block}
{log_block}
</div>
</body>
</html>"""


def write_run_report_html(report: RunReport, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_run_report_html(report), encoding="utf-8")
    return path


def write_suite_index_html(
    entries: list[tuple[RunReport, Path]],
    path: Path,
) -> Path:
    rows: list[str] = []
    ok_count = sum(1 for report, _ in entries if report.success)
    for report, detail_path in entries:
        mark = "OK" if report.success else "FAIL"
        cls = "ok" if report.success else "fail"
        rel = html.escape(detail_path.name)
        rows.append(
            f"<tr class='{cls}'><td>{html.escape(report.scenario_name)}</td>"
            f"<td>{mark}</td>"
            f"<td>{report.duration_ms} мс</td>"
            f"<td><a href='{rel}'>{rel}</a></td></tr>"
        )
    body = f"""<!DOCTYPE html>
<html lang="ru"><head><meta charset="utf-8"/><title>Пакетный прогон</title>
<style>
body {{ background: {COLOR_BG}; color: {COLOR_TEXT}; font-family: "Segoe UI", sans-serif; padding: 24px; }}
table {{ border-collapse: collapse; width: 100%; }}
th, td {{ border: 1px solid {COLOR_BORDER}; padding: 8px; }}
th {{ background: #2d2d2d; }}
tr.fail {{ background: #3a2222; }}
a {{ color: #4fc1ff; }}
</style></head><body>
<h1>Пакетный прогон</h1>
<p>{ok_count}/{len(entries)} успешно</p>
<table><thead><tr><th>Сценарий</th><th>Статус</th><th>Время</th><th>Отчёт</th></tr></thead>
<tbody>{"".join(rows)}</tbody></table>
</body></html>"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    return path


def save_play_html_report(
    scenario: dict[str, Any],
    result: dict[str, Any],
    *,
    feature_path: str | Path | None = None,
    started_at: datetime | None = None,
    duration_ms: int | None = None,
    report_dir: Path | None = None,
) -> Path | None:
    from app.paths import reports_dir

    base = report_dir or reports_dir()
    stamp = (started_at or datetime.now()).strftime("%Y-%m-%d_%H-%M-%S")
    safe_name = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in str(scenario.get("name", "run")))
    folder = base / stamp
    report = run_report_from_play(
        scenario,
        result,
        started_at=started_at,
        feature_path=feature_path,
        duration_ms=duration_ms,
    )
    return write_run_report_html(report, folder / f"{safe_name}.html")


def save_batch_html_reports(
    cases: list[dict[str, Any]],
    *,
    started_at: datetime | None = None,
) -> str | None:
    from app.feature_store import load_feature
    from app.paths import reports_dir
    from app.settings import load_settings

    if not load_settings().get("save_html_reports", True) or not cases:
        return None

    stamp = (started_at or datetime.now()).strftime("%Y-%m-%d_%H-%M-%S")
    folder = reports_dir() / stamp
    entries: list[tuple[RunReport, Path]] = []
    for case in cases:
        path = case.get("path")
        if path is None:
            continue
        feature_path = Path(path)
        try:
            feature = load_feature(feature_path)
        except Exception:
            continue
        scenario = {
            "name": feature.get("name", feature_path.stem),
            "startUrl": feature.get("startUrl", ""),
            "steps": feature.get("steps", []),
        }
        result = {
            "success": bool(case.get("success")),
            "message": str(case.get("message", "") or ""),
            "executed_count": int(case.get("executed", 0)),
            "total_count": int(case.get("total", 0)),
            "step_results": list(case.get("step_results") or []),
            "screenshot_path": case.get("screenshot_path"),
            "trace_path": case.get("trace_path"),
            "log_lines": list(case.get("log_lines") or []),
        }
        report = run_report_from_play(
            scenario,
            result,
            started_at=started_at,
            feature_path=feature_path,
            duration_ms=int(case.get("duration_ms", 0)),
        )
        detail_path = folder / f"{feature_path.stem}.html"
        write_run_report_html(report, detail_path)
        case["html_report_path"] = str(detail_path)
        entries.append((report, detail_path))
    if not entries:
        return None
    index_path = write_suite_index_html(entries, folder / "index.html")
    return str(index_path)
