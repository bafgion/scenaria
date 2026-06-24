"""Splash screen smoke tests."""

from __future__ import annotations

import pytest
from PySide6.QtWidgets import QApplication

from app.qt.splash import ScenariaSplash
from app.qt.startup import load_application, show_startup_splash, splash_enabled


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_splash_enabled_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SCENARIA_SKIP_SPLASH", raising=False)
    assert splash_enabled() is True


def test_splash_can_be_skipped(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SCENARIA_SKIP_SPLASH", "1")
    assert splash_enabled() is False


def test_splash_widget_stages(qapp: QApplication) -> None:
    splash = ScenariaSplash()
    splash.set_stage("Тест…", 42)
    assert splash.progress() == 42
    splash.show_centered()
    qapp.processEvents()
    splash.close()


def test_load_application_with_splash_disabled(
    qapp: QApplication,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SCENARIA_SKIP_SPLASH", "1")
    monkeypatch.setenv("SCENARIA_SKIP_RECORDER_PREWARM", "1")
    splash = show_startup_splash(qapp)
    assert splash is None
    controller, window = load_application(qapp, splash)
    try:
        assert controller.recording is not None
        assert window is not None
    finally:
        controller.shutdown()
        window.close()
        qapp.processEvents()
