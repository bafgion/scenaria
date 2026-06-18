"""Qt application entry."""

from __future__ import annotations

import atexit
import sys

from PySide6.QtWidgets import QApplication

from app.mvc.controllers.app_controller import AppController
from app.paths import configure_playwright_browsers
from app.qt.branding import apply_app_branding, apply_window_icon
from app.qt.main_window import MainWindow
from app.qt.theme import apply_dark_theme


def run_qt_app() -> None:
    configure_playwright_browsers()

    app = QApplication(sys.argv)
    apply_app_branding(app)
    apply_dark_theme(app)

    controller = AppController()
    atexit.register(controller.shutdown)
    window = MainWindow(controller)
    apply_window_icon(window)
    window.show()

    sys.exit(app.exec())
