"""Locate the most recent test report on disk or from UI hints."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from app.paths import reports_dir

ReportKind = Literal["html", "allure"]


@dataclass(frozen=True)
class ReportTarget:
    kind: ReportKind
    path: Path


def _path_if_file(raw: str | Path | None) -> Path | None:
    if raw is None:
        return None
    path = Path(str(raw))
    return path if path.is_file() else None


def _path_if_dir(raw: str | Path | None) -> Path | None:
    if raw is None:
        return None
    path = Path(str(raw))
    return path if path.is_dir() else None


def _allure_has_content(path: Path) -> bool:
    try:
        from scenaria_vanessa.allure_helpers import allure_results_ready

        return allure_results_ready(path)
    except ImportError:
        return any(path.rglob("*"))


def _newest_html_in_reports_dir() -> Path | None:
    base = reports_dir()
    if not base.is_dir():
        return None
    best: tuple[float, Path] | None = None
    for path in base.rglob("*.html"):
        if not path.is_file():
            continue
        mtime = path.stat().st_mtime
        if best is None or mtime > best[0]:
            best = (mtime, path)
    return best[1] if best else None


def _newest_vanessa_allure(project_root: Path | None) -> Path | None:
    try:
        from scenaria_vanessa.report_parsers import allure_dir_from_params, load_merged_params
        from scenaria_vanessa.settings import load_vanessa_settings, resolve_runs_dir
    except ImportError:
        return None

    runs_root = resolve_runs_dir(load_vanessa_settings())
    if not runs_root.is_dir():
        return None

    candidates: list[tuple[float, Path]] = []
    for run_dir in runs_root.iterdir():
        if not run_dir.is_dir():
            continue
        allure = run_dir / "allure"
        if (run_dir / "VAParams.json").is_file():
            try:
                merged = load_merged_params(run_dir)
                resolved = allure_dir_from_params(merged)
                if resolved is not None:
                    allure = resolved
            except Exception:  # noqa: BLE001
                pass
        if not _allure_has_content(allure):
            continue
        mtime = max(run_dir.stat().st_mtime, allure.stat().st_mtime)
        candidates.append((mtime, allure))

    if not candidates:
        return None
    candidates.sort(key=lambda item: item[0], reverse=True)
    return candidates[0][1]


def find_latest_report(
    *,
    hints: dict[str, str | None] | None = None,
    project_root: Path | None = None,
) -> ReportTarget | None:
    """Resolve the newest openable report (HTML or Allure directory)."""
    hints = hints or {}

    for key in ("html_report_path", "suite_html_index"):
        path = _path_if_file(hints.get(key))
        if path is not None:
            return ReportTarget("html", path)

    allure_hint = _path_if_dir(hints.get("allure_dir"))
    if allure_hint is not None and _allure_has_content(allure_hint):
        return ReportTarget("allure", allure_hint)

    html = _newest_html_in_reports_dir()
    if html is not None:
        return ReportTarget("html", html)

    allure = _newest_vanessa_allure(project_root)
    if allure is not None:
        return ReportTarget("allure", allure)

    return None
