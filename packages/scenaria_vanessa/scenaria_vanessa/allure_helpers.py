"""Open Allure report directories and optional CLI serve."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path


def allure_results_ready(allure_dir: Path) -> bool:
    if not allure_dir.is_dir():
        return False
    return any(allure_dir.rglob("*"))


def open_allure_directory(allure_dir: Path) -> bool:
    if not allure_dir.is_dir():
        return False
    target = str(allure_dir.resolve())
    if sys.platform == "win32":
        import os

        os.startfile(target)  # noqa: S606
        return True
    opener = shutil.which("xdg-open") or shutil.which("open")
    if opener:
        subprocess.run([opener, target], check=False)  # noqa: S603
        return True
    return False


def run_allure_serve(allure_dir: Path, allure_cli: str) -> subprocess.Popen | None:
    if not allure_dir.is_dir():
        return None
    executable = shutil.which(allure_cli) or allure_cli
    if not Path(executable).exists() and shutil.which(executable) is None:
        return None
    return subprocess.Popen(  # noqa: S603
        [executable, "serve", str(allure_dir.resolve())],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
