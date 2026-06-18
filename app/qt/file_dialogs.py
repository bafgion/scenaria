"""Qt file dialogs."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QFileDialog, QWidget

FEATURE_FILTER = "Gherkin Feature (*.feature);;Текст (*.txt)"
ZIP_FILTER = "ZIP (*.zip)"
JSON_FILTER = "JSON (*.json)"
PLAYWRIGHT_TS_FILTER = "Playwright TypeScript (*.spec.ts)"
PLAYWRIGHT_PY_FILTER = "Playwright Python (*.py)"


def pick_save_file(
    parent: QWidget | None,
    *,
    title: str,
    filter_spec: str,
    default_name: str = "",
    initial_dir: str | Path | None = None,
) -> Path | None:
    start = str(initial_dir) if initial_dir else ""
    if default_name and start:
        start = str(Path(start) / default_name)
    elif default_name:
        start = default_name
    path, _ = QFileDialog.getSaveFileName(parent, title, start, filter_spec)
    if not path:
        return None
    return Path(path)


def pick_open_file(
    parent: QWidget | None,
    *,
    title: str,
    filter_spec: str,
    initial_dir: str | Path | None = None,
) -> Path | None:
    start = str(initial_dir) if initial_dir else ""
    path, _ = QFileDialog.getOpenFileName(parent, title, start, filter_spec)
    if not path:
        return None
    return Path(path)
