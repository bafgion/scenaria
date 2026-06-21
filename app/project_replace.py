"""Project-wide text replace for `.feature` files."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.text_replace import find_matches, replace_all


@dataclass(frozen=True)
class FileReplacePreview:
    path: Path
    match_count: int
    skipped: bool = False
    skip_reason: str = ""


def collect_replaceable_paths(
    *,
    current_path: Path | None,
    open_paths: list[Path],
    project_root: Path | None,
) -> list[Path]:
    seen: set[str] = set()
    result: list[Path] = []

    def add(path: Path | None) -> None:
        if path is None:
            return
        resolved = path.resolve()
        if resolved.suffix.lower() != ".feature" or not resolved.is_file():
            return
        key = str(resolved)
        if key in seen:
            return
        seen.add(key)
        result.append(resolved)

    add(current_path)
    for path in open_paths:
        add(path)
    if project_root is not None and project_root.is_dir():
        try:
            for path in sorted(project_root.rglob("*.feature"), key=lambda item: str(item).lower()):
                add(path)
        except OSError:
            pass
    return result


def preview_files_replace(
    paths: list[Path],
    needle: str,
    replacement: str,
    *,
    case_sensitive: bool = False,
    steps_only: bool = False,
    skip_paths: set[Path] | None = None,
) -> list[FileReplacePreview]:
    if not needle:
        return []
    skip = {item.resolve() for item in (skip_paths or set())}
    previews: list[FileReplacePreview] = []
    for path in paths:
        resolved = path.resolve()
        if resolved in skip:
            previews.append(
                FileReplacePreview(
                    resolved,
                    0,
                    skipped=True,
                    skip_reason="несохранённые изменения",
                )
            )
            continue
        if not resolved.is_file() or resolved.suffix.lower() != ".feature":
            continue
        try:
            text = resolved.read_text(encoding="utf-8")
        except OSError as exc:
            previews.append(
                FileReplacePreview(resolved, 0, skipped=True, skip_reason=str(exc))
            )
            continue
        count = len(
            find_matches(
                text,
                needle,
                case_sensitive=case_sensitive,
                steps_only=steps_only,
            )
        )
        if count:
            previews.append(FileReplacePreview(resolved, count))
    return previews


def apply_files_replace(
    paths: list[Path],
    needle: str,
    replacement: str,
    *,
    case_sensitive: bool = False,
    steps_only: bool = False,
    skip_paths: set[Path] | None = None,
) -> dict[Path, tuple[str, int]]:
    if not needle:
        return {}
    skip = {item.resolve() for item in (skip_paths or set())}
    changed: dict[Path, tuple[str, int]] = {}
    for path in paths:
        resolved = path.resolve()
        if resolved in skip or not resolved.is_file():
            continue
        try:
            text = resolved.read_text(encoding="utf-8")
        except OSError:
            continue
        new_text, count = replace_all(
            text,
            needle,
            replacement,
            case_sensitive=case_sensitive,
            steps_only=steps_only,
        )
        if count:
            resolved.write_text(new_text, encoding="utf-8")
            changed[resolved] = (new_text, count)
    return changed
