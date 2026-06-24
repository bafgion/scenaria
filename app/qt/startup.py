"""Staged application startup behind the splash screen."""

from __future__ import annotations

import os
import time
from typing import TYPE_CHECKING

from PySide6.QtWidgets import QApplication

from app.qt.splash import ScenariaSplash

if TYPE_CHECKING:
    from app.mvc.controllers.app_controller import AppController
    from app.qt.main_window import MainWindow

MIN_SPLASH_SEC = 1.4
PREWARM_TIMEOUT_SEC = 25.0
_TICK_SEC = 0.02


def splash_enabled() -> bool:
    return os.environ.get("SCENARIA_SKIP_SPLASH", "").strip().lower() not in {
        "1",
        "true",
        "yes",
    }


def _pump(app: QApplication, splash: ScenariaSplash | None, message: str, progress: int) -> None:
    if splash is not None:
        splash.set_stage(message, progress)
    else:
        app.processEvents()


def _wait_until(
    app: QApplication,
    splash: ScenariaSplash | None,
    *,
    predicate,
    message: str,
    progress: int,
    timeout_sec: float,
) -> None:
    deadline = time.monotonic() + timeout_sec
    while time.monotonic() < deadline:
        if predicate():
            return
        _pump(app, splash, message, progress)
        time.sleep(_TICK_SEC)


def _wait_minimum(
    app: QApplication,
    splash: ScenariaSplash | None,
    started_at: float,
) -> None:
    remaining = MIN_SPLASH_SEC - (time.monotonic() - started_at)
    if remaining <= 0:
        return
    deadline = time.monotonic() + remaining
    progress = splash.progress() if splash is not None else 0
    while time.monotonic() < deadline:
        _pump(app, splash, "Запуск…", progress)
        time.sleep(_TICK_SEC)


def load_application(
    app: QApplication,
    splash: ScenariaSplash | None,
) -> tuple[AppController, MainWindow]:
    """Load controller and main window while updating splash progress."""
    from app.mvc.controllers.app_controller import AppController
    from app.paths import configure_playwright_browsers
    from app.qt.branding import apply_app_branding, apply_window_icon
    from app.qt.main_window import MainWindow
    from app.qt.theme import apply_dark_theme

    started_at = time.monotonic()

    _pump(app, splash, "Настройка окружения…", 8)
    configure_playwright_browsers()

    _pump(app, splash, "Оформление интерфейса…", 18)
    apply_app_branding(app)
    apply_dark_theme(app)

    _pump(app, splash, "Загрузка модулей…", 32)
    controller = AppController()

    _pump(app, splash, "Создание рабочего окна…", 55)
    window = MainWindow(controller)
    apply_window_icon(window)

    if os.environ.get("SCENARIA_SKIP_RECORDER_PREWARM") != "1":
        _wait_until(
            app,
            splash,
            predicate=controller.recorder.prewarm_ready,
            message="Подготовка Playwright…",
            progress=82,
            timeout_sec=PREWARM_TIMEOUT_SEC,
        )
    else:
        _pump(app, splash, "Подготовка интерфейса…", 82)

    _pump(app, splash, "Готово", 100)
    _wait_minimum(app, splash, started_at)

    return controller, window


def show_startup_splash(app: QApplication) -> ScenariaSplash | None:
    if not splash_enabled():
        return None
    splash = ScenariaSplash()
    splash.show_centered()
    app.processEvents()
    return splash


def finish_startup(app: QApplication, splash: ScenariaSplash | None) -> None:
    if splash is None:
        app.processEvents()
        return
    splash.dismiss()
