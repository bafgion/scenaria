"""Qt worker event delivery (replacement for Tk UiBridge)."""

from __future__ import annotations

import queue
from collections.abc import Callable
from typing import Any

from PySide6.QtCore import QObject, QTimer, Signal


class WorkerBridge(QObject):
    """Thread-safe event bus: workers call emit(), GUI thread handles via Qt signals."""

    event = Signal(str, object)

    def __init__(self) -> None:
        super().__init__()
        self._queue: queue.Queue[tuple[str, Any]] = queue.Queue()
        self._handlers: dict[str, Callable[[Any], None]] = {}
        self._timer = QTimer(self)
        self._timer.setInterval(50)
        self._timer.timeout.connect(self._poll)
        self.event.connect(self._dispatch)

    def on(self, event: str, handler: Callable[[Any], None]) -> None:
        self._handlers[event] = handler

    def emit_event(self, event: str, payload: Any = None) -> None:
        self._queue.put((event, payload))

    def start(self) -> None:
        self._timer.start()

    def stop(self) -> None:
        self._timer.stop()

    def _poll(self) -> None:
        while True:
            try:
                event, payload = self._queue.get_nowait()
            except queue.Empty:
                break
            self.event.emit(event, payload)

    def _dispatch(self, event: str, payload: object) -> None:
        handler = self._handlers.get(event)
        if handler:
            handler(payload)
