from __future__ import annotations

import zipfile
from pathlib import Path

from app.brand import EXE_NAME
from app.update.installer import (
    _STAGING_DIR_NAME,
    _find_payload_root,
    prepare_update_script,
    stage_update_package,
)


def _write_update_zip(path: Path, version: str) -> None:
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr(f"Scenaria/{EXE_NAME}", b"exe")
        archive.writestr(f"Scenaria/version.txt", version)
        archive.writestr("Scenaria/_internal/app.txt", b"payload")


def test_stage_update_package_finds_exe_root(tmp_path: Path) -> None:
    zip_path = tmp_path / "Scenaria-update.zip"
    _write_update_zip(zip_path, "0.2.2")
    root = stage_update_package(zip_path)
    assert root.name == "Scenaria"
    assert (root / EXE_NAME).is_file()
    assert (root / "version.txt").read_text(encoding="utf-8") == "0.2.2"


def test_prepare_update_script_waits_for_exe_and_logs(tmp_path: Path) -> None:
    install_dir = tmp_path / "install"
    staging_dir = tmp_path / "staging"
    install_dir.mkdir()
    staging_dir.mkdir()
    script = prepare_update_script(staging_dir, install_dir)
    text = script.read_text(encoding="ascii")
    assert "tasklist" in text
    assert "robocopy" in text
    assert "_update_staging" not in text
    assert str(staging_dir.resolve()) in text
    assert "if %RC% GEQ 8" in text
    assert 'start "" "%TARGET%\\Scenaria.exe"' in text
    assert "exit /b 0" in text
