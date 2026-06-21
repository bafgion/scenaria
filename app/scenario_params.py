"""External parameter sets for `.feature` files (A5-2)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ParamCase:
    label: str
    variables: dict[str, str]


def params_file_path(feature_path: Path) -> Path:
    return feature_path.with_suffix(".params.json")


def _normalize_case(raw: Any, *, index: int) -> ParamCase | None:
    if not isinstance(raw, dict):
        return None
    variables = raw.get("variables")
    if not isinstance(variables, dict):
        if all(isinstance(key, str) for key in raw.keys()):
            variables = {str(key): str(value) for key, value in raw.items()}
        else:
            return None
    else:
        variables = {str(key): str(value) for key, value in variables.items()}
    label = str(raw.get("label", "") or raw.get("name", "") or f"набор {index}").strip()
    if not variables:
        return None
    return ParamCase(label=label or f"набор {index}", variables=variables)


def load_param_cases(feature_path: Path) -> list[ParamCase]:
    path = params_file_path(feature_path)
    if not path.is_file():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []

    cases: list[ParamCase] = []
    if isinstance(data, dict) and isinstance(data.get("cases"), list):
        for index, item in enumerate(data["cases"], start=1):
            case = _normalize_case(item, index=index)
            if case is not None:
                cases.append(case)
        return cases
    if isinstance(data, list):
        for index, item in enumerate(data, start=1):
            case = _normalize_case(item, index=index)
            if case is not None:
                cases.append(case)
        return cases
    if isinstance(data, dict):
        case = _normalize_case(data, index=1)
        if case is not None:
            cases.append(case)
    return cases


def param_case_count(feature_path: Path) -> int:
    return len(load_param_cases(feature_path))
