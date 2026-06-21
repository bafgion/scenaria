"""Build argv for 1C platform + Vanessa /C string."""

from __future__ import annotations

import shlex
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class PlatformLaunchSpec:
    executable: Path
    mode: str = "TestManager"
    ib_connection_string: str = ""
    user: str = ""
    password: str = ""
    epf_path: Path | None = None
    extra_args: list[str] = field(default_factory=list)
    start_feature_player: bool = True
    quiet_install_vanessa_ext: bool = True
    install_ext_on_fail: bool = False
    va_params_path: Path | None = None

    def build_argv(self) -> list[str]:
        if not self.executable.is_file():
            raise FileNotFoundError(f"Платформа 1С не найдена: {self.executable}")
        argv: list[str] = [str(self.executable)]
        if self.user:
            argv.append(f'/N"{self.user}"')
        if self.password:
            argv.append(f'/P"{self.password}"')
        mode = (self.mode or "TestManager").strip()
        if mode:
            argv.append(mode)
        if self.ib_connection_string.strip():
            argv.append(f'/IBConnectionString "{self.ib_connection_string.strip()}"')
        if self.epf_path is not None and self.epf_path.is_file():
            argv.append(f'/Execute "{self.epf_path}"')
        argv.extend(self.extra_args)
        argv.append(f'/C"{self.build_c_string()}"')
        return argv

    def build_c_string(self) -> str:
        if self.va_params_path is None:
            raise ValueError("Не задан путь к VAParams.json")
        segments: list[str] = []
        if self.start_feature_player:
            segments.append("StartFeaturePlayer")
        if self.quiet_install_vanessa_ext:
            segments.append("QuietInstallVanessaExt")
        if self.install_ext_on_fail:
            segments.append("InstallVanessaExtOnFailOfQuietInstall")
        segments.append(f"VAParams={self.va_params_path.resolve()}")
        return ";".join(segments)

    def format_command_line(self) -> str:
        return " ".join(shlex.quote(part) if " " in part else part for part in self.build_argv())


def launch_spec_from_settings(
    settings: dict[str, Any],
    *,
    va_params_path: Path,
) -> PlatformLaunchSpec:
    epf_raw = str(settings.get("epf_path", "") or "").strip()
    epf = Path(epf_raw).expanduser() if epf_raw else None
    extra = settings.get("platform_extra_args") or []
    if not isinstance(extra, list):
        extra = []
    return PlatformLaunchSpec(
        executable=Path(str(settings.get("platform_executable", "") or "")).expanduser(),
        mode=str(settings.get("platform_mode", "TestManager") or "TestManager"),
        ib_connection_string=str(settings.get("ib_connection_string", "") or ""),
        user=str(settings.get("user", "") or ""),
        password=str(settings.get("password", "") or ""),
        epf_path=epf,
        extra_args=[str(item) for item in extra],
        start_feature_player=bool(settings.get("start_feature_player", True)),
        quiet_install_vanessa_ext=bool(settings.get("quiet_install_vanessa_ext", True)),
        install_ext_on_fail=bool(settings.get("install_ext_on_fail", False)),
        va_params_path=va_params_path,
    )
