"""Download Vanessa Automation .epf into local app data."""

from __future__ import annotations

from pathlib import Path
from typing import Callable

DEFAULT_EPF_DOWNLOAD_URL = (
    "https://github.com/Pr-Mex/vanessa-automation/releases/latest/download/vanessa-automation.epf"
)


def default_epf_path() -> Path:
    from app.paths import data_dir

    return data_dir() / "vanessa" / "vanessa-automation.epf"


def resolve_epf_download_url(settings: dict | None = None) -> str:
    from scenaria_vanessa.settings import load_vanessa_settings

    cfg = settings or load_vanessa_settings()
    custom = str(cfg.get("epf_download_url", "") or "").strip()
    return custom or DEFAULT_EPF_DOWNLOAD_URL


ProgressCallback = Callable[[int, int], None]


def download_vanessa_epf(
    destination: Path | None = None,
    *,
    url: str | None = None,
    settings: dict | None = None,
    on_progress: ProgressCallback | None = None,
) -> Path:
    from app.update.http_download import download_url_resilient

    target = Path(destination or default_epf_path()).expanduser()
    download_url = str(url or resolve_epf_download_url(settings)).strip()
    if not download_url:
        raise ValueError("URL загрузки Vanessa EPF не задан")
    download_url_resilient(download_url, target, on_progress=on_progress)
    if not target.is_file() or target.stat().st_size <= 0:
        raise OSError(f"Файл не загружен: {target}")
    return target
