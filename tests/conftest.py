"""Pytest configuration."""

from __future__ import annotations

import sys
import threading
from pathlib import Path

import pytest

from integration_subprocess import integration_subprocess_active, run_integration_tests

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

_BROWSER_LOCK = threading.Lock()
_QT_MODULE_MARKERS = ("PySide6", "QApplication")


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--integration-in-process",
        action="store_true",
        default=False,
        help="Run integration tests in this process (used by integration subprocess runner)",
    )


@pytest.fixture(autouse=True)
def skip_recorder_prewarm_outside_integration(request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch) -> None:
    """AppController creates ScenarioRecorder which prewarms Playwright — unsafe with Qt."""
    if request.node.get_closest_marker("integration"):
        yield
        return
    monkeypatch.setenv("SCENARIA_SKIP_RECORDER_PREWARM", "1")
    yield


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


def _markexpr(config: pytest.Config) -> str:
    return str(config.getoption("-m", default="") or "")


def _should_isolate_integration(config: pytest.Config, items: list[pytest.Item]) -> bool:
    if config.getoption("--integration-in-process"):
        return False
    if integration_subprocess_active():
        return False
    integration = [item for item in items if _is_integration_test(item)]
    if not integration:
        return False
    non_integration = [item for item in items if not _is_integration_test(item)]
    if not non_integration:
        return False
    markexpr = _markexpr(config)
    if markexpr == "integration":
        return False
    if "not integration" in markexpr:
        return False
    return True


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Run real-browser tests before Qt when both run in the same process."""
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


def pytest_collection_finish(session: pytest.Session) -> None:
    config = session.config
    if not _should_isolate_integration(config, session.items):
        return

    exit_code = run_integration_tests()
    config._integration_subprocess_exit = exit_code  # type: ignore[attr-defined]
    session.items[:] = [item for item in session.items if not _is_integration_test(item)]


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    sub_exit = getattr(session.config, "_integration_subprocess_exit", None)
    if sub_exit is None:
        return
    session.exitstatus = sub_exit or exitstatus


@pytest.fixture(autouse=True)
def serialize_integration_tests(request: pytest.FixtureRequest) -> None:
    """Only one Playwright session at a time — prevents flaky restarts under load."""
    if request.node.get_closest_marker("integration"):
        with _BROWSER_LOCK:
            yield
    else:
        yield
