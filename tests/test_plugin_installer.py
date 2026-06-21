"""Tests for zip plugin installer."""

from __future__ import annotations

import json
import shutil
import zipfile
from pathlib import Path

import pytest

from app.plugins.installer import PluginInstallError, install_from_zip, list_installed_plugins, uninstall_plugin
from app.plugins.registry import get_registry, reset_registry


def _make_zip(tmp_path: Path, plugin_id: str = "demo") -> Path:
    root = tmp_path / "payload"
    pkg = root / "demo_pkg"
    pkg.mkdir(parents=True)
    (pkg / "__init__.py").write_text("", encoding="utf-8")
    (pkg / "plugin_impl.py").write_text(
        "class DemoRunner:\n"
        "    id = 'demo'\n"
        "    label = 'Demo'\n"
        "    def is_available(self): return True, ''\n"
        "    def run(self, request, *, on_log=None, on_progress=None, should_stop=None):\n"
        "        from app.plugins.models import RunBatchResult\n"
        "        return RunBatchResult(runner=self.id, success=True, cases=[])\n"
        "    def parse_results(self, run_dir):\n"
        "        from app.plugins.models import RunResult\n"
        "        return RunResult(runner=self.id, success=True, cases=[], run_dir=run_dir)\n",
        encoding="utf-8",
    )
    manifest = {
        "id": plugin_id,
        "name": "Demo",
        "version": "0.0.1",
        "min_scenaria": "0.1.0",
        "entry": "demo_pkg.plugin_impl:DemoRunner",
    }
    (root / "plugin.json").write_text(json.dumps(manifest), encoding="utf-8")
    zip_path = tmp_path / "addon.zip"
    with zipfile.ZipFile(zip_path, "w") as archive:
        for item in root.rglob("*"):
            if item.is_file():
                archive.write(item, item.relative_to(root))
    return zip_path


def test_install_and_uninstall_roundtrip(tmp_path: Path, monkeypatch) -> None:
    plugins_root = tmp_path / "plugins"
    plugins_root.mkdir()
    monkeypatch.setattr("app.paths.plugins_dir", lambda: plugins_root)
    reset_registry()

    zip_path = _make_zip(tmp_path)
    target = install_from_zip(zip_path)
    assert target.is_dir()
    assert (target / "plugin.json").is_file()
    installed = list_installed_plugins()
    assert any(item["id"] == "demo" for item in installed)

    registry = get_registry()
    registry.reload()
    assert registry.get_runner("demo") is not None

    assert uninstall_plugin("demo") is True
    assert not (plugins_root / "demo").exists()
    reset_registry()
    registry.reload()
    assert registry.get_runner("demo") is None


def test_install_rejects_missing_manifest(tmp_path: Path, monkeypatch) -> None:
    plugins_root = tmp_path / "plugins"
    plugins_root.mkdir()
    monkeypatch.setattr("app.paths.plugins_dir", lambda: plugins_root)
    zip_path = tmp_path / "bad.zip"
    with zipfile.ZipFile(zip_path, "w") as archive:
        archive.writestr("readme.txt", "no manifest")
    with pytest.raises(PluginInstallError):
        install_from_zip(zip_path)
