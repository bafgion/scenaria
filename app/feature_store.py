"""File-based storage for Russian Gherkin `.feature` scenarios."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.gherkin_ru import GherkinParseError, gherkin_to_steps, steps_to_gherkin
from app.paths import data_dir
from app.settings import load_settings, save_settings


FEATURES_ROOT_KEY = "features_root"
MAX_FEATURES_IN_TREE = 5000


@dataclass(frozen=True)
class FeatureItem:
    path: Path
    stem: str
    relative_dir: str
    start_url: str
    step_count: int


def get_root() -> Path | None:
    settings = load_settings()
    raw = str(settings.get(FEATURES_ROOT_KEY, "") or "").strip()
    if not raw:
        return None
    path = Path(raw).expanduser()
    if not path.is_dir():
        return None
    if is_ephemeral_project_path(path):
        clear_root()
        return None
    return path.resolve()


def clear_root() -> None:
    settings = load_settings()
    settings[FEATURES_ROOT_KEY] = ""
    save_settings(settings)


def is_ephemeral_project_path(path: Path) -> bool:
    """Detect pytest temp folders that must not be used as a real project root."""
    lowered = str(path).lower()
    if "pytest-of-" not in lowered:
        return False
    return path.name.startswith("test_")


def resolve_project_root() -> Path | None:
    """Return a persisted project folder, recovering from recents if needed."""
    root = get_root()
    if root is not None:
        return root

    from app.recent import recent_features, recent_projects

    for project in recent_projects():
        if project.is_dir() and not is_ephemeral_project_path(project):
            set_root(project)
            return project.resolve()

    for feature in recent_features():
        parent = feature.parent.resolve()
        if parent.is_dir() and not is_ephemeral_project_path(parent):
            set_root(parent)
            return parent

    settings = load_settings()
    open_tabs = settings.get("open_tabs")
    if isinstance(open_tabs, list):
        for item in open_tabs:
            if not isinstance(item, dict):
                continue
            raw = str(item.get("path", "") or "").strip()
            if not raw:
                continue
            parent = Path(raw).parent.resolve()
            if parent.is_dir() and not is_ephemeral_project_path(parent):
                set_root(parent)
                return parent

    return None


def set_root(path: Path) -> None:
    settings = load_settings()
    settings[FEATURES_ROOT_KEY] = str(path)
    save_settings(settings)


def _compute_start_url(steps: list[dict[str, Any]]) -> str:
    for step in steps:
        if step.get("action") == "goto":
            url = str(step.get("url", "") or "").strip()
            if url:
                return url
    return ""


def load_feature(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    steps = gherkin_to_steps(text)
    return {
        "name": path.stem,
        "startUrl": _compute_start_url(steps),
        "steps": steps,
    }


def save_feature(path: Path, steps: list[dict[str, Any]], *, scenario_name: str | None = None) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    scenario = scenario_name or path.stem
    text = steps_to_gherkin(list(steps), scenario_name=scenario)
    path.write_text(text + "\n", encoding="utf-8")
    return path


def save_feature_text(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = text if text.endswith("\n") or not text else text + "\n"
    path.write_text(payload, encoding="utf-8")
    return path


def normalize_feature_text(text: str) -> str:
    return text.replace("\r\n", "\n").rstrip("\n")


def feature_texts_equivalent(left: str, right: str) -> bool:
    return normalize_feature_text(left) == normalize_feature_text(right)


def delete_feature(path: Path) -> None:
    try:
        path.unlink(missing_ok=True)  # type: ignore[call-arg]
    except TypeError:  # Python <3.8 compat (shouldn't happen)
        if path.exists():
            path.unlink()


def duplicate_feature(src_path: Path, dst_path: Path, *, steps: list[dict[str, Any]] | None = None) -> Path:
    if steps is None:
        loaded = load_feature(src_path)
        steps = loaded["steps"]
    return save_feature(dst_path, steps, scenario_name=dst_path.stem)


def list_features(root: Path) -> list[FeatureItem]:
    items: list[FeatureItem] = []
    if not root.exists():
        return items
    # Limit to avoid accidentally freezing the UI if the user points at a huge dir.
    for i, path in enumerate(sorted(root.rglob("*.feature"), key=lambda p: str(p).lower())):
        if i >= MAX_FEATURES_IN_TREE:
            break
        try:
            loaded = load_feature(path)
        except (OSError, GherkinParseError, ValueError):
            # Skip unreadable/broken files; UI will still show them if needed later.
            continue
        rel_parent = path.parent.relative_to(root) if path.parent != root else Path()
        items.append(
            FeatureItem(
                path=path,
                stem=path.stem,
                relative_dir=str(rel_parent).replace("\\", "/"),
                start_url=str(loaded.get("startUrl", "") or ""),
                step_count=len(loaded.get("steps", []) or []),
            )
        )
    return items


def feature_name_from_path(path: Path) -> str:
    # Requirement: UI name is file stem.
    return path.stem


def _draft_path() -> Path:
    return data_dir() / "draft.json"


def save_draft(draft: dict[str, Any]) -> None:
    payload = dict(draft)
    _draft_path().write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def load_draft() -> dict[str, Any] | None:
    path = _draft_path()
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def clear_draft() -> None:
    try:
        _draft_path().unlink(missing_ok=True)  # type: ignore[call-arg]
    except TypeError:
        if _draft_path().exists():
            _draft_path().unlink()

