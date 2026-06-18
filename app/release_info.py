"""Release/update configuration."""

from __future__ import annotations

import json
import os
from pathlib import Path

from app.brand import DEFAULT_GITHUB_REPO, GITHUB_REPO_ENV


def github_repo() -> str:
    env = os.environ.get(GITHUB_REPO_ENV, "").strip()
    if env:
        return env
    config = _config_path()
    if config.is_file():
        try:
            data = json.loads(config.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            data = {}
        repo = str(data.get("github_repo", "")).strip()
        if repo:
            return repo
    return DEFAULT_GITHUB_REPO


def _config_path() -> Path:
    return Path(__file__).resolve().parent.parent / "release.json"
