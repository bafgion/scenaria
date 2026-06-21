"""Persist last run result and history per `.feature` file for sidebar badges."""

from __future__ import annotations

import json
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.paths import data_dir

MAX_HISTORY = 20
_STORE_LOCK = threading.Lock()


@dataclass(frozen=True)
class FeatureRunStatus:
    success: bool
    message: str
    at: str


@dataclass(frozen=True)
class RunHistoryEntry:
    success: bool
    message: str
    at: str
    duration_ms: int = 0
    failed_step: int | None = None
    report_path: str | None = None
    runner: str = "playwright"
    run_dir: str | None = None


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
    with _STORE_LOCK:
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _key(path: Path) -> str:
    return str(path.resolve())


def _brief_message(message: str) -> str:
    brief = (message or "").splitlines()[0].strip()
    if len(brief) > 200:
        brief = brief[:197] + "..."
    return brief


def _normalize_bucket(raw: Any) -> dict[str, Any]:
    if isinstance(raw, dict) and "last" in raw:
        return raw
    if isinstance(raw, dict) and "success" in raw:
        return {"last": raw, "history": [raw]}
    return {"last": None, "history": []}


def _entry_from_dict(entry: dict[str, Any]) -> RunHistoryEntry:
    failed = entry.get("failed_step")
    return RunHistoryEntry(
        success=bool(entry.get("success")),
        message=str(entry.get("message", "")),
        at=str(entry.get("at", "")),
        duration_ms=int(entry.get("duration_ms", 0)),
        failed_step=int(failed) if failed is not None else None,
        report_path=str(entry["report_path"]) if entry.get("report_path") else None,
        runner=str(entry.get("runner", "playwright") or "playwright"),
        run_dir=str(entry["run_dir"]) if entry.get("run_dir") else None,
    )


def _entry_to_dict(
    *,
    success: bool,
    message: str,
    duration_ms: int = 0,
    failed_step: int | None = None,
    report_path: str | None = None,
    runner: str = "playwright",
    run_dir: str | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "success": bool(success),
        "message": _brief_message(message),
        "at": datetime.now(timezone.utc).isoformat(),
        "duration_ms": max(0, int(duration_ms)),
        "runner": str(runner or "playwright"),
    }
    if failed_step is not None:
        payload["failed_step"] = int(failed_step)
    if report_path:
        payload["report_path"] = report_path
    if run_dir:
        payload["run_dir"] = run_dir
    return payload


def record_run(
    path: Path,
    *,
    success: bool,
    message: str = "",
    duration_ms: int = 0,
    failed_step: int | None = None,
    report_path: str | None = None,
    runner: str = "playwright",
    run_dir: str | None = None,
) -> None:
    data = _load_raw()
    key = _key(path)
    bucket = _normalize_bucket(data.get(key))
    entry = _entry_to_dict(
        success=success,
        message=message,
        duration_ms=duration_ms,
        failed_step=failed_step,
        report_path=report_path,
        runner=runner,
        run_dir=run_dir,
    )
    history = [entry]
    for item in bucket.get("history") or []:
        if isinstance(item, dict):
            history.append(item)
    bucket["last"] = entry
    bucket["history"] = history[:MAX_HISTORY]
    data[key] = bucket
    _save_raw(data)


def get_run_status(path: Path) -> FeatureRunStatus | None:
    bucket = _normalize_bucket(_load_raw().get(_key(path)))
    last = bucket.get("last")
    if not isinstance(last, dict):
        return None
    return FeatureRunStatus(
        success=bool(last.get("success")),
        message=str(last.get("message", "")),
        at=str(last.get("at", "")),
    )


def get_run_history(path: Path) -> list[RunHistoryEntry]:
    bucket = _normalize_bucket(_load_raw().get(_key(path)))
    result: list[RunHistoryEntry] = []
    for item in bucket.get("history") or []:
        if isinstance(item, dict):
            result.append(_entry_from_dict(item))
    return result


def domain_from_url(url: str) -> str:
    if not url:
        return ""
    try:
        from urllib.parse import urlparse

        netloc = urlparse(url).netloc
        return netloc[4:] if netloc.startswith("www.") else netloc
    except Exception:
        return ""
