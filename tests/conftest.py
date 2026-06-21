"""Pytest configuration."""

from __future__ import annotations

import sys
import threading
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

_BROWSER_LOCK = threading.Lock()
_QT_MODULE_MARKERS = ("PySide6", "QApplication")


@pytest.fixture(autouse=True)
def isolated_settings(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    """Never write tests into the user's real %APPDATA% settings."""
    settings_file = tmp_path / "settings.json"
    monkeypatch.setattr("app.paths.settings_path", lambda: settings_file)
    monkeypatch.setattr("app.settings.settings_path", lambda: settings_file)
    return settings_file


def _module_source(item: pytest.Item) -> str:
    module_path = getattr(item.module, "__file__", None)
    if not module_path:
        return ""
    try:
        return Path(module_path).read_text(encoding="utf-8")
    except OSError:
        return ""


def _is_integration_test(item: pytest.Item) -> bool:
    return item.get_closest_marker("integration") is not None


def _is_qt_test(item: pytest.Item) -> bool:
    if "qapp" in item.fixturenames or "_qt_app" in item.fixturenames:
        return True
    source = _module_source(item)
    return any(marker in source for marker in _QT_MODULE_MARKERS)


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Run real-browser tests before Qt to avoid native crashes on Windows."""
    integration: list[pytest.Item] = []
    plain: list[pytest.Item] = []
    qt: list[pytest.Item] = []
    for item in items:
        if _is_integration_test(item):
            integration.append(item)
        elif _is_qt_test(item):
            qt.append(item)
        else:
            plain.append(item)
    items[:] = integration + plain + qt


@pytest.fixture(autouse=True)
def serialize_integration_tests(request: pytest.FixtureRequest) -> None:
    """Only one Playwright session at a time — prevents flaky restarts under load."""
    if request.node.get_closest_marker("integration"):
        with _BROWSER_LOCK:
            yield
    else:
        yield
