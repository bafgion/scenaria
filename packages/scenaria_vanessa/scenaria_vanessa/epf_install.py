"""Download Vanessa Automation .epf into local app data."""

from __future__ import annotations

import json
import tempfile
import urllib.error
import urllib.request
import zipfile
from pathlib import Path
from typing import Callable

from app.brand import BRAND_NAME
from app.version import app_version

VANESSA_GITHUB_REPO = "Pr-Mex/vanessa-automation"
SINGLE_ZIP_PREFIX = "vanessa-automation-single."

ProgressCallback = Callable[[int, int], None]
PhaseCallback = Callable[[str], None]


def default_epf_path() -> Path:
    from app.paths import data_dir

    return data_dir() / "vanessa" / "vanessa-automation.epf"


def _vanessa_api_url(path: str) -> str:
    return f"https://api.github.com/repos/{VANESSA_GITHUB_REPO}{path}"


def _request_release_json(url: str, *, timeout: float = 20.0) -> dict:
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": f"{BRAND_NAME}/{app_version()}",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        payload = json.loads(response.read().decode("utf-8"))
    if not isinstance(payload, dict):
        raise OSError("Некорректный ответ GitHub API")
    return payload


def _pick_single_zip_asset(release: dict) -> str:
    assets = release.get("assets", [])
    if not isinstance(assets, list):
        assets = []
    for entry in assets:
        if not isinstance(entry, dict):
            continue
        name = str(entry.get("name", ""))
        if name.startswith(SINGLE_ZIP_PREFIX) and name.endswith(".zip"):
            url = str(entry.get("browser_download_url", "")).strip()
            if url:
                return url
    tag = str(release.get("tag_name", "")).strip()
    if tag:
        for entry in assets:
            if not isinstance(entry, dict):
                continue
            name = str(entry.get("name", ""))
            if "single" in name.lower() and name.endswith(".zip"):
                return (
                    f"https://github.com/{VANESSA_GITHUB_REPO}/releases/download/{tag}/{name}"
                )
    raise OSError(
        "В последнем релизе Vanessa Automation нет архива vanessa-automation-single*.zip"
    )


def resolve_latest_single_zip_url(*, timeout: float = 20.0) -> str:
    release = _request_release_json(_vanessa_api_url("/releases/latest"), timeout=timeout)
    return _pick_single_zip_asset(release)


def resolve_epf_download_url(settings: dict | None = None) -> str:
    from scenaria_vanessa.settings import load_vanessa_settings

    cfg = settings or load_vanessa_settings()
    custom = str(cfg.get("epf_download_url", "") or "").strip()
    if custom:
        return custom
    try:
        return resolve_latest_single_zip_url()
    except (urllib.error.URLError, urllib.error.HTTPError, OSError, TimeoutError) as exc:
        raise OSError(
            "Не удалось определить URL загрузки Vanessa EPF. "
            "Укажите ссылку вручную в настройках Vanessa."
        ) from exc


def _extract_epf_from_zip(zip_path: Path, destination: Path) -> Path:
    with zipfile.ZipFile(zip_path) as archive:
        epf_names = [name for name in archive.namelist() if name.lower().endswith(".epf")]
        if not epf_names:
            raise OSError(f"В архиве нет .epf: {zip_path.name}")
        chosen = next(
            (name for name in epf_names if "single" in Path(name).name.lower()),
            epf_names[0],
        )
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(archive.read(chosen))
    return destination


def download_vanessa_epf(
    destination: Path | None = None,
    *,
    url: str | None = None,
    settings: dict | None = None,
    on_progress: ProgressCallback | None = None,
    on_phase: PhaseCallback | None = None,
) -> Path:
    from app.update.http_download import download_url_resilient

    target = Path(destination or default_epf_path()).expanduser()
    download_url = str(url or resolve_epf_download_url(settings)).strip()
    if not download_url:
        raise ValueError("URL загрузки Vanessa EPF не задан")

    if on_phase is not None:
        on_phase("download")

    if download_url.lower().endswith(".zip"):
        with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as handle:
            temp_zip = Path(handle.name)
        try:
            download_url_resilient(download_url, temp_zip, on_progress=on_progress)
            if on_phase is not None:
                on_phase("extract")
            _extract_epf_from_zip(temp_zip, target)
        finally:
            temp_zip.unlink(missing_ok=True)
    else:
        download_url_resilient(download_url, target, on_progress=on_progress)

    if not target.is_file() or target.stat().st_size <= 0:
        raise OSError(f"Файл не загружен: {target}")
    return target
