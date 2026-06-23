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
from collections.abc import Callable
from pathlib import Path

from app.brand import BRAND_NAME, EXE_NAME
from app.paths import app_root
from app.release_info import github_repo
from app.update.checker import UpdateAsset, UpdateCheckError
from app.update.http_download import download_url_resilient

_STAGING_DIR_NAME = "_update_staging"
_LOG_NAME = "_apply_update.log"
_BAT_NAME = "_apply_update.bat"
_VBS_NAME = "_apply_update.vbs"
UPDATE_LOG_NAME = _LOG_NAME


def _write_script_file(path: Path, content: str) -> None:
    """Write helper scripts without relying on the optional ascii codec in frozen builds."""
    path.write_bytes(content.encode("utf-8"))


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download_asset(
    asset: UpdateAsset,
    destination: Path,
    on_progress=None,
    *,
    should_cancel: Callable[[], bool] | None = None,
) -> Path:
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
                should_cancel=should_cancel,
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


def _extract_zip(zip_path: Path, target_dir: Path, on_phase=None) -> None:
    target_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "r") as archive:
        names = archive.namelist()
        total = len(names) or 1
        for index, name in enumerate(names, start=1):
            archive.extract(name, target_dir)
            if on_phase is not None:
                on_phase("extract", index, total, name)


def _find_payload_root(extracted_dir: Path) -> Path:
    exe = list(extracted_dir.rglob(EXE_NAME))
    if not exe:
        raise UpdateCheckError(f"В архиве обновления не найден {EXE_NAME}")
    return exe[0].parent


def _quote_batch_path(path: Path) -> str:
    return str(path.resolve())


def prepare_update_script(
    staging_dir: Path,
    install_dir: Path,
    *,
    exe_name: str = EXE_NAME,
    parent_pid: int,
    max_wait_sec: int = 120,
) -> Path:
    script_path = install_dir / _BAT_NAME
    log_path = install_dir / _LOG_NAME
    target = _quote_batch_path(install_dir)
    staging = _quote_batch_path(staging_dir)
    log_file = _quote_batch_path(log_path)
    lines = [
        "@echo off",
        "setlocal EnableExtensions EnableDelayedExpansion",
        f'set "TARGET={target}"',
        f'set "STAGING={staging}"',
        f'set "LOG={log_file}"',
        f'set "PID={int(parent_pid)}"',
        f'set "WAIT_SEC=0"',
        f'set "MAX_WAIT={int(max_wait_sec)}"',
        f'echo [%date% %time%] Update started PID=%PID% >"%LOG%"',
        "ping -n 3 127.0.0.1 >nul",
        ":wait_exit",
        'for /f %%C in (\'tasklist /FI "PID eq %PID%" /NH 2^>nul ^| find /C "%PID%"\') do set "FOUND=%%C"',
        'if not defined FOUND set "FOUND=0"',
        'if "!FOUND!"=="0" goto do_copy',
        "set /a WAIT_SEC+=1",
        "if !WAIT_SEC! GEQ !MAX_WAIT! goto force_kill",
        "ping -n 2 127.0.0.1 >nul",
        "goto wait_exit",
        ":force_kill",
        f'echo [%date% %time%] Force kill PID %PID% >>"%LOG%"',
        "taskkill /PID %PID% /T /F >>\"%LOG%\" 2>&1",
        f'taskkill /IM {exe_name} /T /F >>"%LOG%" 2>&1',
        "ping -n 3 127.0.0.1 >nul",
        ":do_copy",
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
    _write_script_file(script_path, "\r\n".join(lines) + "\r\n")
    return script_path


def _write_hidden_launcher(script: Path) -> Path:
    vbs_path = script.with_name(_VBS_NAME)
    bat_quoted = str(script.resolve()).replace('"', '""')
    _write_script_file(
        vbs_path,
        f'CreateObject("WScript.Shell").Run "cmd /c ""{bat_quoted}""", 0, False\r\n',
    )
    return vbs_path


def stage_update_package(zip_path: Path, on_phase=None) -> Path:
    temp_root = Path(tempfile.mkdtemp(prefix="scenaria-update-"))
    extracted = temp_root / "extracted"
    _extract_zip(zip_path, extracted, on_phase=on_phase)
    return _find_payload_root(extracted)


def _copy_to_local_staging(source: Path, install_dir: Path, on_phase=None) -> Path:
    local_staging = install_dir / _STAGING_DIR_NAME
    if local_staging.exists():
        shutil.rmtree(local_staging, ignore_errors=True)
    files = [path for path in source.rglob("*") if path.is_file()]
    total = len(files) or 1
    local_staging.mkdir(parents=True, exist_ok=True)
    for index, src_file in enumerate(files, start=1):
        rel = src_file.relative_to(source)
        dest = local_staging / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src_file, dest)
        if on_phase is not None:
            on_phase("stage", index, total, str(rel))
    return local_staging


def _launch_update_script(script: Path, install_dir: Path) -> None:
    if os.name != "nt":
        raise UpdateCheckError("Обновление поддерживается только в Windows")

    launcher = _write_hidden_launcher(script)
    create_no_window = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
    create_flags = (
        subprocess.DETACHED_PROCESS
        | subprocess.CREATE_NEW_PROCESS_GROUP
        | create_no_window
    )
    breakaway = getattr(subprocess, "CREATE_BREAKAWAY_FROM_JOB", 0x01000000)
    create_flags |= breakaway

    startupinfo = None
    if hasattr(subprocess, "STARTUPINFO"):
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= getattr(subprocess, "STARTF_USESHOWWINDOW", 1)
        startupinfo.wShowWindow = 0

    subprocess.Popen(
        ["wscript.exe", "//Nologo", str(launcher)],
        cwd=str(install_dir),
        creationflags=create_flags,
        startupinfo=startupinfo,
        close_fds=True,
    )
    time.sleep(0.5)


def apply_update(
    asset: UpdateAsset,
    on_progress=None,
    on_phase=None,
    *,
    on_exit_requested=None,
    should_cancel: Callable[[], bool] | None = None,
) -> None:
    if not getattr(sys, "frozen", False):
        raise UpdateCheckError("Обновление доступно только в portable EXE")

    def emit_phase(phase: str, current: int, total: int, detail: str = "") -> None:
        if on_phase is not None:
            on_phase(phase, current, total, detail)

    def download_progress(done: int, total: int) -> None:
        if on_progress is not None:
            on_progress(done, total)
        emit_phase("download", done, total, asset.name)

    install_dir = app_root()
    download_temp = Path(tempfile.mkdtemp(prefix="scenaria-download-"))
    zip_path = download_temp / asset.name
    remote_staging_parent: Path | None = None
    try:
        download_asset(asset, zip_path, on_progress=download_progress, should_cancel=should_cancel)
        emit_phase("verify", 1, 1, "")
        remote_staging = stage_update_package(zip_path, on_phase=emit_phase)
        remote_staging_parent = remote_staging.parent.parent
        local_staging = _copy_to_local_staging(remote_staging, install_dir, on_phase=emit_phase)
        script = prepare_update_script(local_staging, install_dir, parent_pid=os.getpid())
    except Exception:
        shutil.rmtree(download_temp, ignore_errors=True)
        if remote_staging_parent is not None:
            shutil.rmtree(remote_staging_parent, ignore_errors=True)
        raise
    finally:
        shutil.rmtree(download_temp, ignore_errors=True)
        if remote_staging_parent is not None:
            shutil.rmtree(remote_staging_parent, ignore_errors=True)

    emit_phase("launch", 1, 1, "")
    _launch_update_script(script, install_dir)
    if on_exit_requested is not None:
        on_exit_requested()
    else:
        os._exit(0)
