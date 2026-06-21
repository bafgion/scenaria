"""UI session flags (browser, recording, playback)."""

from __future__ import annotations

from PySide6.QtCore import QObject, Signal


class SessionModel(QObject):
    changed = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.pending = False
        self.browser_open = False
        self.player_browser = False
        self.recording = False
        self.paused = False
        self.playing = False
        self.vanessa_running = False
        self.headless = False
        self.filter_recording = False
        self.nav_only_recording = False
        self.hover_recording = False
        self.last_failed_step_index: int | None = None

    def touch(self) -> None:
        self.changed.emit()

    def browser_session_active(self) -> bool:
        return self.browser_open or self.player_browser
