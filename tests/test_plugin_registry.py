"""Tests for plugin registry and folder discovery."""

from __future__ import annotations

import json
import textwrap
from pathlib import Path

from app.plugins.loader import discover_plugins, load_folder_plugin
from app.plugins.registry import PluginRegistry, reset_registry


def _write_fake_plugin(plugins_root: Path, plugin_id: str = "fake") -> Path:
    plugin_dir = plugins_root / plugin_id
    plugin_dir.mkdir(parents=True)
    module_dir = plugin_dir / "fake_runner_pkg"
    module_dir.mkdir()
    (module_dir / "__init__.py").write_text("", encoding="utf-8")
    (module_dir / "runner.py").write_text(
        textwrap.dedent(
            """
            class FakeRunner:
                id = "fake"
                label = "Fake Runner"

                def is_available(self):
                    return True, ""

                def run(self, request, *, on_log=None, on_progress=None, should_stop=None):
                    from app.plugins.models import RunBatchResult

                    return RunBatchResult(runner=self.id, success=True, cases=[])

                def parse_results(self, run_dir):
                    from app.plugins.models import RunResult

                    return RunResult(runner=self.id, success=True, cases=[], run_dir=run_dir)
            """
        ),
        encoding="utf-8",
    )
    manifest = {
        "id": plugin_id,
        "name": "Fake",
        "version": "0.0.1",
        "min_scenaria": "0.1.0",
        "entry": "fake_runner_pkg.runner:FakeRunner",
    }
    (plugin_dir / "plugin.json").write_text(json.dumps(manifest), encoding="utf-8")
    return plugin_dir


def test_load_folder_plugin_success(tmp_path: Path) -> None:
    plugin_dir = _write_fake_plugin(tmp_path)
    runner, error = load_folder_plugin(plugin_dir)
    assert error is None
    assert runner is not None
    assert runner.id == "fake"
    available, _ = runner.is_available()
    assert available is True


def test_discover_plugins_includes_builtin_and_folder(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("app.paths.plugins_dir", lambda: tmp_path)
    _write_fake_plugin(tmp_path)
    runners, errors = discover_plugins()
    assert "playwright" in runners
    assert "fake" in runners
    assert "fake" not in errors


def test_registry_lists_known_optional_plugin(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("app.paths.plugins_dir", lambda: tmp_path)
    reset_registry()
    registry = PluginRegistry()
    registry.reload()
    ids = {info.id for info in registry.runner_infos()}
    assert "playwright" in ids
    assert "vanessa" in ids
