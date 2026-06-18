"""Application version."""

from __future__ import annotations

import sys
from functools import lru_cache
from importlib import metadata
from pathlib import Path

from app.brand import PACKAGE_NAME
from app.paths import app_root


def _read_bundled_version() -> str | None:
    if not getattr(sys, "frozen", False):
        return None
    version_file = app_root() / "version.txt"
    if not version_file.is_file():
        return None
    value = version_file.read_text(encoding="utf-8").strip()
    return value or None


def _read_pyproject_version() -> str | None:
    pyproject = Path(__file__).resolve().parent.parent / "pyproject.toml"
    if not pyproject.is_file():
        return None
    for line in pyproject.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith("version = "):
            return stripped.split("=", 1)[1].strip().strip('"').strip("'")
    return None


@lru_cache(maxsize=1)
def app_version() -> str:
    bundled = _read_bundled_version()
    if bundled:
        return bundled
    try:
        return metadata.version(PACKAGE_NAME)
    except metadata.PackageNotFoundError:
        pass
    from_pyproject = _read_pyproject_version()
    if from_pyproject:
        return from_pyproject
    return "0.0.0"


def version_tuple(version: str | None = None) -> tuple[int, ...]:
    raw = (version or app_version()).strip().lstrip("v")
    parts: list[int] = []
    for piece in raw.split("."):
        digits = "".join(ch for ch in piece if ch.isdigit())
        if digits:
            parts.append(int(digits))
    return tuple(parts) if parts else (0,)


def is_newer_version(remote: str, local: str | None = None) -> bool:
    return version_tuple(remote) > version_tuple(local or app_version())
