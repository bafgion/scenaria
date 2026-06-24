"""Qt application entry."""

from __future__ import annotations

import atexit
import sys

from PySide6.QtWidgets import QApplication

from app.qt.startup import finish_startup, load_application, show_startup_splash


def run_qt_app() -> None:
    app = QApplication(sys.argv)
    splash = show_startup_splash(app)

    controller, window = load_application(app, splash)
    atexit.register(controller.shutdown)

    window.show()
    finish_startup(app, splash)

    sys.exit(app.exec())
