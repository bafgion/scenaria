"""Parse drag-and-drop file paths for the main window."""

from __future__ import annotations

from pathlib import Path


def paths_from_drop_urls(urls: list[str]) -> list[Path]:
    result: list[Path] = []
    for raw in urls:
        if not raw:
            continue
        path = Path(raw)
        if path.exists():
            result.append(path.resolve())
    return result


def classify_drop_paths(paths: list[Path]) -> tuple[list[Path], list[Path]]:
    features: list[Path] = []
    directories: list[Path] = []
    for path in paths:
        if path.is_file() and path.suffix.lower() == ".feature":
            features.append(path)
        elif path.is_dir():
            directories.append(path)
    return features, directories
