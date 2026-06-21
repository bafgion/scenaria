"""Build scenaria-vanessa.zip add-on artifact."""

from __future__ import annotations

import json
import shutil
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGE_ROOT = ROOT / "packages" / "scenaria_vanessa"
DIST = ROOT / "dist" / "addons"


def build_addon_zip(version: str | None = None) -> Path:
    manifest_path = PACKAGE_ROOT / "plugin.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if version:
        manifest["version"] = version
    DIST.mkdir(parents=True, exist_ok=True)
    target = DIST / f"scenaria-vanessa-{manifest['version']}.zip"
    if target.exists():
        target.unlink()
    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("plugin.json", json.dumps(manifest, ensure_ascii=False, indent=2))
        package_dir = PACKAGE_ROOT / "scenaria_vanessa"
        for path in package_dir.rglob("*"):
            if path.is_file() and "__pycache__" not in path.parts:
                archive.write(path, Path("scenaria_vanessa") / path.relative_to(package_dir))
    return target


if __name__ == "__main__":
    print(build_addon_zip())
