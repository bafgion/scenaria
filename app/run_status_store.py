"""Persist last run result per `.feature` file for sidebar badges."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.paths import data_dir


@dataclass(frozen=True)
class FeatureRunStatus:
    success: bool
    message: str
    at: str


def _store_path() -> Path:
    return data_dir() / "run_status.json"


def _load_raw() -> dict[str, Any]:
    path = _store_path()
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, OSError):
        return {}


def _save_raw(data: dict[str, Any]) -> None:
    path = _store_path()
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _key(path: Path) -> str:
    return str(path.resolve())


def record_run(path: Path, *, success: bool, message: str = "") -> None:
    data = _load_raw()
    brief = (message or "").splitlines()[0].strip()
    if len(brief) > 200:
        brief = brief[:197] + "..."
    data[_key(path)] = {
        "success": bool(success),
        "message": brief,
        "at": datetime.now(timezone.utc).isoformat(),
    }
    _save_raw(data)


def get_run_status(path: Path) -> FeatureRunStatus | None:
    entry = _load_raw().get(_key(path))
    if not isinstance(entry, dict):
        return None
    return FeatureRunStatus(
        success=bool(entry.get("success")),
        message=str(entry.get("message", "")),
        at=str(entry.get("at", "")),
    )


def domain_from_url(url: str) -> str:
    if not url:
        return ""
    try:
        from urllib.parse import urlparse

        netloc = urlparse(url).netloc
        return netloc[4:] if netloc.startswith("www.") else netloc
    except Exception:
        return ""
