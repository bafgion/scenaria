"""Upload path resolution relative to project ``testdata/`` (A6-1)."""

from __future__ import annotations

from pathlib import Path


def testdata_dir(project_root: Path | None) -> Path | None:
    if project_root is None:
        return None
    path = project_root / "testdata"
    return path


def resolve_upload_path(path: str, project_root: Path | None = None) -> Path:
    """Resolve upload file path; relative paths are looked up under ``testdata/``."""
    raw = str(path or "").strip()
    candidate = Path(raw).expanduser()
    if candidate.is_file():
        return candidate.resolve()
    if project_root is not None:
        from_testdata = (project_root / "testdata" / raw).resolve()
        if from_testdata.is_file():
            return from_testdata
        alt = (project_root / raw).resolve()
        if alt.is_file():
            return alt
    return candidate.resolve()


def validate_upload_path(path: str, project_root: Path | None = None) -> str | None:
    """Return an error message when the upload file is missing."""
    resolved = resolve_upload_path(path, project_root)
    if resolved.is_file():
        return None
    hint = ""
    if project_root is not None:
        hint = f" (ожидался файл в {project_root / 'testdata'})"
    return f"Файл для загрузки не найден: {path}{hint}"
