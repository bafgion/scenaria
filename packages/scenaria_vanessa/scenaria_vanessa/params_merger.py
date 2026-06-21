"""Merge project base VAParams with per-run overlay."""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

from app.plugins.models import RunMode, RunRequest
from app.project_config import load_project_config
from app.run_suite import collect_feature_files, infer_project_root, resolve_feature_files

from scenaria_vanessa.merge_utils import deep_merge
from scenaria_vanessa.param_catalog import detect_bool_style, normalize_bool
from scenaria_vanessa.settings import load_vanessa_settings, resolve_base_params_path, resolve_runs_dir


def path_for_va_json(path: Path) -> str:
    return str(path.resolve()).replace("/", "\\")


def load_json_file(path: Path | None) -> dict[str, Any]:
    if path is None or not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    return data if isinstance(data, dict) else {}


def create_run_dir(settings: dict[str, Any] | None = None) -> Path:
    root = resolve_runs_dir(settings)
    run_dir = root / str(uuid.uuid4())
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


class VAParamsMerger:
    def __init__(self, settings: dict[str, Any] | None = None) -> None:
        self._settings = settings or load_vanessa_settings()

    def merge_for_request(
        self,
        request: RunRequest,
        *,
        run_dir: Path | None = None,
    ) -> tuple[Path, dict[str, Any], Path]:
        run_directory = run_dir or create_run_dir(self._settings)
        project_root = request.project_root or infer_project_root(request.paths)
        base_path = resolve_base_params_path(project_root, self._settings)
        base = load_json_file(base_path)
        bool_style = detect_bool_style(base)

        overlay = self._build_overlay(request, project_root=project_root, run_dir=run_directory, bool_style=bool_style)
        merged = deep_merge(base, overlay)
        va_params_path = run_directory / "VAParams.json"
        va_params_path.write_text(json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8")
        return va_params_path, merged, run_directory

    def _build_overlay(
        self,
        request: RunRequest,
        *,
        project_root: Path | None,
        run_dir: Path,
        bool_style: str,
    ) -> dict[str, Any]:
        epf = Path(str(self._settings.get("epf_path", "") or "")).expanduser()
        junit_dir = run_dir / "junit"
        junit_dir.mkdir(parents=True, exist_ok=True)
        allure_dir = run_dir / "allure"
        scenario_log = run_dir / "scenario.log"
        status_path = run_dir / "status.log"

        options = dict(request.runner_options or {})
        report_junit = bool(options.get("report_junit", self._settings.get("report_junit", True)))
        report_allure = bool(options.get("report_allure", self._settings.get("report_allure", False)))

        overlay: dict[str, Any] = {
            "ВыгружатьСтатусВыполненияСценариевВФайл": normalize_bool(True, style=bool_style),
            "ПутьКФайлуДляВыгрузкиСтатусаВыполненияСценариев": path_for_va_json(status_path),
            "ДелатьЛогВыполненияСценариевВТекстовыйФайл": normalize_bool(True, style=bool_style),
            "ИмяФайлаЛогВыполненияСценариев": path_for_va_json(scenario_log),
        }
        if report_junit:
            overlay["ДелатьОтчетВФорматеjUnit"] = normalize_bool(True, style=bool_style)
            overlay["КаталогВыгрузкиJUnit"] = path_for_va_json(junit_dir)
        if report_allure:
            allure_dir.mkdir(parents=True, exist_ok=True)
            overlay["ДелатьОтчетВФорматеАллюр"] = normalize_bool(True, style=bool_style)
            overlay["КаталогВыгрузкиAllure"] = path_for_va_json(allure_dir)

        if project_root is not None:
            overlay["КаталогПроекта"] = path_for_va_json(project_root)
            project_cfg = load_project_config(project_root)
            features_root = project_root / str(project_cfg.get("features_root", "features") or "features")
            if features_root.is_dir():
                overlay.setdefault("КаталогФич", path_for_va_json(features_root))

        if epf.is_file():
            overlay["КаталогИнструментов"] = path_for_va_json(epf.parent)

        include_tags = [tag.strip().lstrip("@") for tag in request.tags if str(tag).strip()]
        exclude_tags = [tag.strip().lstrip("@") for tag in request.exclude_tags if str(tag).strip()]
        if include_tags:
            overlay["СписокТеговОтбор"] = [f"@{tag}" if not tag.startswith("@") else tag for tag in include_tags]
        if exclude_tags:
            overlay["СписокТеговИсключение"] = [
                f"@{tag}" if not tag.startswith("@") else tag for tag in exclude_tags
            ]

        files = self._resolve_feature_files(request)
        if request.mode == RunMode.DIRECTORY and request.paths:
            directory = next((path.resolve() for path in request.paths if path.resolve().is_dir()), None)
            if directory is not None:
                overlay["КаталогФич"] = path_for_va_json(directory)
        elif files:
            overlay["СписокФичДляВыполнения"] = [path_for_va_json(path) for path in files]

        scenario_names = [name.strip() for name in request.scenario_names if str(name).strip()]
        if scenario_names:
            overlay["СписокСценариевДляВыполнения"] = scenario_names

        return overlay

    def _resolve_feature_files(self, request: RunRequest) -> list[Path]:
        tag = request.tag
        if tag:
            return resolve_feature_files(request.paths, tag=tag)
        return collect_feature_files(request.paths)
