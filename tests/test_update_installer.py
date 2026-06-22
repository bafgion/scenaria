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


def test_stage_update_package_reports_extract_phases(tmp_path: Path) -> None:
    zip_path = tmp_path / "Scenaria-update.zip"
    _write_update_zip(zip_path, "0.2.2")
    phases: list[tuple[str, int, int]] = []

    stage_update_package(
        zip_path,
        on_phase=lambda phase, current, total, _detail: phases.append((phase, current, total)),
    )

    assert phases
    assert phases[0][0] == "extract"
    assert phases[-1][1] == phases[-1][2]
    assert phases[-1][2] > 0


def test_copy_to_local_staging_reports_stage_phases(tmp_path: Path) -> None:
    from app.update.installer import _copy_to_local_staging

    source = tmp_path / "payload"
    source.mkdir()
    (source / EXE_NAME).write_bytes(b"exe")
    nested = source / "nested"
    nested.mkdir()
    (nested / "app.txt").write_bytes(b"payload")

    install_dir = tmp_path / "install"
    install_dir.mkdir()
    phases: list[tuple[str, int, int]] = []

    staging = _copy_to_local_staging(
        source,
        install_dir,
        on_phase=lambda phase, current, total, _detail: phases.append((phase, current, total)),
    )

    assert staging.name == _STAGING_DIR_NAME
    assert phases
    assert all(phase == "stage" for phase, _, _ in phases)
    assert phases[-1][1] == phases[-1][2]


def test_prepare_update_script_waits_for_exe_and_logs(tmp_path: Path) -> None:
    install_dir = tmp_path / "install"
    staging_dir = tmp_path / "staging"
    install_dir.mkdir()
    staging_dir.mkdir()
    script = prepare_update_script(staging_dir, install_dir, parent_pid=4242)
    text = script.read_text(encoding="utf-8")
    assert 'set "PID=4242"' in text
    assert "EnableDelayedExpansion" in text
    assert 'find /C "%PID%"' in text
    assert "goto force_kill" in text
    assert "taskkill /PID %PID% /T /F" in text
    assert f"taskkill /IM {EXE_NAME} /T /F" in text
    assert "robocopy" in text
    assert "_update_staging" not in text
    assert str(staging_dir.resolve()) in text
    assert "if %RC% GEQ 8" in text
    assert 'start "" "%TARGET%\\Scenaria.exe"' in text
    assert "exit /b 0" in text


def test_write_script_file_avoids_ascii_codec(tmp_path: Path, monkeypatch) -> None:
    from app.update.installer import _write_script_file

    def _reject_ascii(encoding: str, /, *args, **kwargs):
        if encoding == "ascii":
            raise LookupError("unknown encoding: ascii")
        return original_lookup(encoding, *args, **kwargs)

    import codecs

    original_lookup = codecs.lookup
    monkeypatch.setattr(codecs, "lookup", _reject_ascii)
    target = tmp_path / "helper.bat"
    _write_script_file(target, "@echo off\r\ntest\r\n")
    assert target.read_bytes() == b"@echo off\r\ntest\r\n"


def test_write_hidden_launcher(tmp_path: Path) -> None:
    from app.update.installer import _write_hidden_launcher

    script = tmp_path / "_apply_update.bat"
    script.write_text("@echo off\r\n", encoding="utf-8")
    vbs = _write_hidden_launcher(script)
    text = vbs.read_text(encoding="utf-8")
    assert vbs.name == "_apply_update.vbs"
    assert "WScript.Shell" in text
    assert str(script.resolve()) in text
    assert ", 0, False" in text
