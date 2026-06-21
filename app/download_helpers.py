"""Playwright download capture and file assertions."""

from __future__ import annotations

import uuid
from pathlib import Path

from app.paths import data_dir


def new_download_run_dir() -> tuple[str, Path]:
    run_id = uuid.uuid4().hex[:12]
    directory = data_dir() / "downloads" / run_id
    directory.mkdir(parents=True, exist_ok=True)
    return run_id, directory


def save_playwright_download(download, directory: Path) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    name = download.suggested_filename or "download.bin"
    destination = directory / name
    download.save_as(destination)
    return destination


def read_text_content(path: Path, *, max_bytes: int = 512_000) -> str:
    raw = path.read_bytes()[:max_bytes]
    for encoding in ("utf-8", "utf-8-sig", "cp1251", "latin-1"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw.decode("latin-1", errors="replace")


def file_contains_substring(path: Path, needle: str) -> bool:
    if not needle:
        return True
    if not path.is_file():
        return False
    try:
        return needle in read_text_content(path)
    except OSError:
        return False
