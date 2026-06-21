"""Tests for platform command builder."""

from __future__ import annotations

from pathlib import Path

from scenaria_vanessa.platform_command import PlatformLaunchSpec


def test_build_c_string_contains_vaparams(tmp_path: Path) -> None:
    exe = tmp_path / "1cv8c.exe"
    exe.write_text("stub", encoding="utf-8")
    epf = tmp_path / "va.epf"
    epf.write_text("stub", encoding="utf-8")
    params = tmp_path / "VAParams.json"
    params.write_text("{}", encoding="utf-8")
    spec = PlatformLaunchSpec(
        executable=exe,
        mode="TestManager",
        ib_connection_string='File="demo";',
        user="Admin",
        epf_path=epf,
        va_params_path=params,
    )
    c_string = spec.build_c_string()
    assert "StartFeaturePlayer" in c_string
    assert "VAParams=" in c_string
    assert str(params.resolve()) in c_string
    argv = spec.build_argv()
    assert argv[0] == str(exe)
    assert any(part.startswith("/C") for part in argv)
