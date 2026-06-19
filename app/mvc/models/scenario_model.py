"""Open scenario model (name, url, steps, dirty state)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from PySide6.QtCore import QObject, Signal

from app.feature_store import clear_draft, load_draft, save_draft
from app.gherkin_ru import GherkinParseError, gherkin_to_steps


class ScenarioModel(QObject):
    """Current scenario being edited in the main panel."""

    changed = Signal()
    loaded = Signal()
    cleared = Signal()
    dirty_changed = Signal(bool)
    status_message = Signal(str, str)  # text, tone

    def __init__(self) -> None:
        super().__init__()
        self._feature_path: Path | None = None
        self._name = ""
        self._start_url = ""
        self._steps: list[dict[str, Any]] = []
        self._source_text: str | None = None
        self._dirty = False
        self._saved_snapshot = ""

    @property
    def feature_path(self) -> Path | None:
        return self._feature_path

    @property
    def name(self) -> str:
        return self._name

    @property
    def start_url(self) -> str:
        return self._start_url

    @property
    def steps(self) -> list[dict[str, Any]]:
        return list(self._steps)

    @property
    def source_text(self) -> str | None:
        return self._source_text

    @property
    def dirty(self) -> bool:
        return self._dirty

    def load_from_path(self, path: Path) -> None:
        try:
            raw = path.read_text(encoding="utf-8")
        except OSError as exc:
            self.status_message.emit(f"Не удалось открыть «{path.name}»: {exc}", "error")
            raise
        try:
            steps = gherkin_to_steps(raw)
        except GherkinParseError as exc:
            self.status_message.emit(f"Ошибка в «{path.name}»: {exc}", "error")
            raise
        self._feature_path = path.resolve()
        self._name = path.stem
        self._start_url = ""
        for step in steps:
            if step.get("action") == "goto":
                url = str(step.get("url", "") or "").strip()
                if url:
                    self._start_url = url
                    break
        self._steps = list(steps)
        self._source_text = raw
        self._saved_snapshot = self._snapshot()
        self._dirty = False
        clear_draft()
        self.loaded.emit()
        self.dirty_changed.emit(False)
        self.changed.emit()
        self.status_message.emit(f"Загружен сценарий «{path.stem}»", "success")

    def new_scenario(self) -> None:
        preserved_start_url = self._start_url
        self._feature_path = None
        self._name = ""
        self._start_url = preserved_start_url
        self._steps = []
        self._source_text = ""
        self._saved_snapshot = self._snapshot()
        self._dirty = False
        clear_draft()
        self.cleared.emit()
        self.dirty_changed.emit(False)
        self.changed.emit()
        self.status_message.emit("Новый сценарий", "info")

    def set_name(self, name: str) -> None:
        if name == self._name:
            return
        self._name = name
        self._mark_dirty()

    def set_start_url(self, url: str) -> None:
        if url == self._start_url:
            return
        self._start_url = url
        self._mark_dirty()

    def set_steps(self, steps: list[dict[str, Any]]) -> None:
        self._steps = list(steps)
        self._source_text = None
        self._mark_dirty()

    def set_source_text(self, text: str) -> None:
        self._source_text = text

    def restore_draft_if_any(self) -> bool:
        draft = load_draft()
        if not draft or not draft.get("steps"):
            return False
        draft_path_raw = str(draft.get("feature_path", "") or "").strip()
        if draft_path_raw:
            draft_path = Path(draft_path_raw)
            if draft_path.is_file():
                try:
                    self.load_from_path(draft_path)
                    return True
                except (OSError, GherkinParseError, ValueError):
                    pass
        self._feature_path = None
        self._name = str(draft.get("name", "") or "")
        self._start_url = str(draft.get("startUrl", "") or "")
        self._steps = list(draft.get("steps", []) or [])
        self._source_text = None
        self._saved_snapshot = self._snapshot()
        self._dirty = True
        self.loaded.emit()
        self.dirty_changed.emit(True)
        self.changed.emit()
        self.status_message.emit("Восстановлен черновик", "warning")
        return True

    def save_draft_if_needed(self, *, enabled: bool, editor_text: str | None = None) -> None:
        if not enabled or self._feature_path is not None:
            return
        steps: list[dict[str, Any]] = []
        if editor_text is not None and editor_text.strip():
            try:
                steps = gherkin_to_steps(editor_text)
            except GherkinParseError:
                return
        elif self._dirty and self._steps:
            steps = list(self._steps)
        if not steps:
            return
        save_draft(
            {
                "name": self._name,
                "startUrl": self._start_url,
                "steps": steps,
            }
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self._name,
            "startUrl": self._start_url,
            "steps": list(self._steps),
        }

    def mark_saved(self, path: Path) -> None:
        self._feature_path = path.resolve()
        self._saved_snapshot = self._snapshot()
        self._dirty = False
        clear_draft()
        self.dirty_changed.emit(False)
        self.changed.emit()

    def bind_feature_path(self, path: Path | None) -> None:
        """Point the model at a file without loading its contents from disk."""
        if path is None:
            self._feature_path = None
            return
        resolved = path.resolve()
        if self._feature_path == resolved:
            return
        self._feature_path = resolved
        self._name = resolved.stem
        self.changed.emit()

    def _snapshot(self) -> str:
        return json.dumps(self.as_dict(), ensure_ascii=False, sort_keys=True)

    def _mark_dirty(self) -> None:
        dirty = self._snapshot() != self._saved_snapshot
        if dirty != self._dirty:
            self._dirty = dirty
            self.dirty_changed.emit(dirty)
        self.changed.emit()
