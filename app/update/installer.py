"""Download and apply portable application updates on Windows."""

from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile
from pathlib import Path

from app.brand import BRAND_NAME, EXE_NAME
from app.paths import app_root
from app.release_info import github_repo
from app.update.checker import UpdateAsset, UpdateCheckError
from app.update.http_download import download_url_resilient

_STAGING_DIR_NAME = "_update_staging"
_LOG_NAME = "_apply_update.log"
_BAT_NAME = "_apply_update.bat"


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download_asset(asset: UpdateAsset, destination: Path, on_progress=None) -> Path:
    urls = asset.all_urls
    if not urls:
        raise UpdateCheckError(f"Нет ссылки на файл {asset.name}")

    destination.parent.mkdir(parents=True, exist_ok=True)
    last_error: UpdateCheckError | None = None
    for index, url in enumerate(urls):
        if index > 0:
            destination.unlink(missing_ok=True)
        try:
            download_url_resilient(
                url,
                destination,
                total_hint=asset.size,
                on_progress=on_progress,
            )
            break
        except UpdateCheckError as exc:
            last_error = exc
    else:
        manual = f"https://github.com/{github_repo()}/releases/latest"
        detail = str(last_error) if last_error else asset.name
        raise UpdateCheckError(
            f"Не удалось скачать {asset.name}: {detail}. "
            f"Попробуйте VPN или скачайте вручную: {manual}"
        ) from last_error

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


def _quote_batch_path(path: Path) -> str:
    return str(path.resolve())


def prepare_update_script(staging_dir: Path, install_dir: Path, exe_name: str = EXE_NAME) -> Path:
    script_path = install_dir / _BAT_NAME
    log_path = install_dir / _LOG_NAME
    target = _quote_batch_path(install_dir)
    staging = _quote_batch_path(staging_dir)
    log_file = _quote_batch_path(log_path)
    lines = [
        "@echo off",
        "setlocal EnableExtensions",
        f'set "TARGET={target}"',
        f'set "STAGING={staging}"',
        f'set "LOG={log_file}"',
        f'echo [%date% %time%] Update started >"%LOG%"',
        ":wait_exit",
        f'tasklist /FI "IMAGENAME eq {exe_name}" 2>nul | find /I "{exe_name}" >nul',
        "if %ERRORLEVEL%==0 (",
        "  timeout /t 1 /nobreak >nul",
        "  goto wait_exit",
        ")",
        f'echo [%date% %time%] Copying update files >>"%LOG%"',
        (
            f'robocopy "%STAGING%" "%TARGET%" /E /XD data browsers /R:5 /W:2 '
            f'/NFL /NDL /NJH /NJS /NC /NS /NP >>"%LOG%" 2>&1'
        ),
        "set RC=%ERRORLEVEL%",
        f'echo [%date% %time%] robocopy exit %RC% >>"%LOG%"',
        "if %RC% GEQ 8 (",
        f'  echo Update failed, robocopy code %RC% >>"%LOG%"',
        "  exit /b %RC%",
        ")",
        f'if exist "%STAGING%" rmdir /S /Q "%STAGING%"',
        f'echo [%date% %time%] Restarting {BRAND_NAME} >>"%LOG%"',
        f'start "" "%TARGET%\\{exe_name}"',
        "endlocal",
        "del \"%~f0\" >nul 2>&1",
        "exit /b 0",
    ]
    script_path.write_text("\r\n".join(lines) + "\r\n", encoding="ascii", errors="strict")
    return script_path


def stage_update_package(zip_path: Path) -> Path:
    temp_root = Path(tempfile.mkdtemp(prefix="scenaria-update-"))
    extracted = temp_root / "extracted"
    _extract_zip(zip_path, extracted)
    return _find_payload_root(extracted)


def _copy_to_local_staging(source: Path, install_dir: Path) -> Path:
    local_staging = install_dir / _STAGING_DIR_NAME
    if local_staging.exists():
        shutil.rmtree(local_staging, ignore_errors=True)
    shutil.copytree(source, local_staging)
    return local_staging


def _launch_update_script(script: Path, install_dir: Path) -> None:
    if os.name != "nt":
        raise UpdateCheckError("Обновление поддерживается только в Windows")

    create_no_window = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
    create_flags = (
        subprocess.DETACHED_PROCESS
        | subprocess.CREATE_NEW_PROCESS_GROUP
        | create_no_window
    )
    breakaway = getattr(subprocess, "CREATE_BREAKAWAY_FROM_JOB", 0x01000000)
    create_flags |= breakaway

    subprocess.Popen(
        ["cmd.exe", "/c", str(script)],
        cwd=str(install_dir),
        creationflags=create_flags,
        close_fds=True,
    )
    time.sleep(0.3)


def apply_update(asset: UpdateAsset, on_progress=None) -> None:
    if not getattr(sys, "frozen", False):
        raise UpdateCheckError("Обновление доступно только в portable EXE")

    install_dir = app_root()
    download_temp = Path(tempfile.mkdtemp(prefix="scenaria-download-"))
    zip_path = download_temp / asset.name
    remote_staging_parent: Path | None = None
    try:
        download_asset(asset, zip_path, on_progress=on_progress)
        remote_staging = stage_update_package(zip_path)
        remote_staging_parent = remote_staging.parent.parent
        local_staging = _copy_to_local_staging(remote_staging, install_dir)
        script = prepare_update_script(local_staging, install_dir)
    except Exception:
        shutil.rmtree(download_temp, ignore_errors=True)
        if remote_staging_parent is not None:
            shutil.rmtree(remote_staging_parent, ignore_errors=True)
        raise
    finally:
        shutil.rmtree(download_temp, ignore_errors=True)
        if remote_staging_parent is not None:
            shutil.rmtree(remote_staging_parent, ignore_errors=True)

    _launch_update_script(script, install_dir)
    os._exit(0)
