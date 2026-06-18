"""Download and apply portable application updates on Windows."""

from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path

from app.brand import BRAND_NAME, EXE_NAME
from app.paths import app_root
from app.update.checker import UpdateAsset, UpdateCheckError


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download_asset(asset: UpdateAsset, destination: Path, on_progress=None) -> Path:
    if not asset.url:
        raise UpdateCheckError(f"Нет ссылки на файл {asset.name}")

    request = urllib.request.Request(asset.url, headers={"User-Agent": BRAND_NAME})
    destination.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(request, timeout=120) as response:
        total = int(response.headers.get("Content-Length", "0") or 0)
        read = 0
        with destination.open("wb") as handle:
            while True:
                chunk = response.read(1024 * 256)
                if not chunk:
                    break
                handle.write(chunk)
                read += len(chunk)
                if on_progress and total > 0:
                    on_progress(read, total)

    if asset.sha256 and _sha256_file(destination) != asset.sha256.lower():
        destination.unlink(missing_ok=True)
        raise UpdateCheckError("Контрольная сумма загруженного файла не совпадает")
    return destination


def _extract_zip(zip_path: Path, target_dir: Path) -> None:
    target_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "r") as archive:
        archive.extractall(target_dir)


def _find_payload_root(extracted_dir: Path) -> Path:
    exe = list(extracted_dir.rglob(EXE_NAME))
    if not exe:
        raise UpdateCheckError(f"В архиве обновления не найден {EXE_NAME}")
    return exe[0].parent


def prepare_update_script(staging_dir: Path, install_dir: Path, exe_name: str = EXE_NAME) -> Path:
    script_path = install_dir / "_apply_update.bat"
    lines = [
        "@echo off",
        "setlocal",
        f"set TARGET={install_dir}",
        f"set STAGING={staging_dir}",
        f"echo Updating {BRAND_NAME}...",
        "timeout /t 2 /nobreak >nul",
        f'robocopy "%STAGING%" "%TARGET%" /E /XD data browsers /R:2 /W:1 /NFL /NDL /NJH /NJS /NC /NS /NP >nul',
        f'start "" "%TARGET%\\{exe_name}"',
        "endlocal",
        "del \"%~f0\"",
    ]
    script_path.write_text("\r\n".join(lines) + "\r\n", encoding="utf-8")
    return script_path


def stage_update_package(zip_path: Path) -> Path:
    temp_root = Path(tempfile.mkdtemp(prefix="scenaria-update-"))
    extracted = temp_root / "extracted"
    _extract_zip(zip_path, extracted)
    return _find_payload_root(extracted)


def apply_update(asset: UpdateAsset, on_progress=None) -> None:
    if not getattr(sys, "frozen", False):
        raise UpdateCheckError("Обновление доступно только в portable EXE")

    install_dir = app_root()
    temp_root = Path(tempfile.mkdtemp(prefix="scenaria-download-"))
    zip_path = temp_root / asset.name
    try:
        download_asset(asset, zip_path, on_progress=on_progress)
        staging_dir = stage_update_package(zip_path)
        script = prepare_update_script(staging_dir, install_dir)
    except Exception:
        shutil.rmtree(temp_root, ignore_errors=True)
        raise

    subprocess.Popen(
        ["cmd.exe", "/c", str(script)],
        cwd=str(install_dir),
        creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP,
        close_fds=True,
    )
    os._exit(0)
