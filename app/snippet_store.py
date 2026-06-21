"""User-defined Gherkin snippet storage and palette helpers."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from app.feature_store import get_root
from app.gherkin_snippets import GherkinSnippet, HEADER_SNIPPETS, STEP_SNIPPETS
from app.paths import global_snippets_path, project_snippets_path

_PLACEHOLDER_RE = re.compile(r"\{\{(\w+)\}\}")

SnippetSource = Literal["builtin", "project", "global"]
PaletteKind = Literal["builtin", "user"]


@dataclass(frozen=True)
class UserSnippet:
    id: str
    label: str
    description: str
    text: str
    placeholders: tuple[str, ...] = ()
    source: SnippetSource = "global"


@dataclass(frozen=True)
class PaletteSnippet:
    id: str
    label: str
    description: str
    text: str
    placeholders: tuple[str, ...]
    kind: PaletteKind
    builtin: GherkinSnippet | None = None
    source: SnippetSource = "builtin"


def extract_placeholders(text: str) -> tuple[str, ...]:
    seen: list[str] = []
    for match in _PLACEHOLDER_RE.finditer(text):
        name = match.group(1)
        if name not in seen:
            seen.append(name)
    return tuple(seen)


def resolve_placeholders(text: str, values: dict[str, str]) -> str:
    result = text
    for key, value in values.items():
        result = result.replace(f"{{{{{key}}}}}", value)
    return result


def _normalize_snippet(raw: dict[str, Any], *, source: SnippetSource) -> UserSnippet | None:
    snippet_id = str(raw.get("id", "") or "").strip()
    label = str(raw.get("label", "") or "").strip()
    text = str(raw.get("text", "") or "")
    if not snippet_id or not label or not text.strip():
        return None
    description = str(raw.get("description", "") or "").strip()
    declared = raw.get("placeholders")
    if isinstance(declared, list):
        placeholders = tuple(str(item).strip() for item in declared if str(item).strip())
    else:
        placeholders = extract_placeholders(text)
    return UserSnippet(
        id=snippet_id,
        label=label,
        description=description,
        text=text,
        placeholders=placeholders,
        source=source,
    )


def _load_snippets_file(path: Path, *, source: SnippetSource) -> list[UserSnippet]:
    if not path.is_file():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    if not isinstance(data, dict):
        return []
    raw_items = data.get("snippets")
    if not isinstance(raw_items, list):
        return []
    result: list[UserSnippet] = []
    for item in raw_items:
        if isinstance(item, dict):
            snippet = _normalize_snippet(item, source=source)
            if snippet is not None:
                result.append(snippet)
    return result


def load_user_snippets(project_root: Path | None = None) -> list[UserSnippet]:
    """Merged user snippets: project overrides global entries with the same id."""
    root = project_root or get_root()
    by_id: dict[str, UserSnippet] = {}
    for snippet in _load_snippets_file(global_snippets_path(), source="global"):
        by_id[snippet.id] = snippet
    if root is not None:
        for snippet in _load_snippets_file(project_snippets_path(root), source="project"):
            by_id[snippet.id] = snippet
    return sorted(by_id.values(), key=lambda item: item.label.lower())


def slugify_snippet_id(label: str) -> str:
    text = re.sub(r"[^\w\-]+", "-", label.strip().lower(), flags=re.UNICODE)
    text = re.sub(r"-+", "-", text).strip("-")
    return text or "snippet"


def append_user_snippet(
    snippet: UserSnippet,
    *,
    project_root: Path | None = None,
    prefer_project: bool = True,
) -> Path:
    """Append or replace a user snippet by id."""
    root = project_root or get_root()
    use_project = prefer_project and root is not None
    existing = load_user_snippets(root if use_project else None)
    by_id = {item.id: item for item in existing}
    by_id[snippet.id] = snippet
    ordered = sorted(by_id.values(), key=lambda item: item.label.lower())
    return save_user_snippets(ordered, project_root=root, use_project=use_project)


def save_user_snippets(
    snippets: list[UserSnippet],
    *,
    project_root: Path | None = None,
    use_project: bool = False,
) -> Path:
    root = project_root or get_root()
    target = project_snippets_path(root) if use_project and root is not None else global_snippets_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": 1,
        "snippets": [
            {
                "id": item.id,
                "label": item.label,
                "description": item.description,
                "text": item.text,
                "placeholders": list(item.placeholders),
            }
            for item in snippets
        ],
    }
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return target


def _builtin_palette_items() -> list[PaletteSnippet]:
    items: list[PaletteSnippet] = []
    for snippet in (*HEADER_SNIPPETS, *STEP_SNIPPETS):
        items.append(
            PaletteSnippet(
                id=f"builtin:{snippet.label}",
                label=snippet.label,
                description=snippet.description,
                text=snippet.insert,
                placeholders=(),
                kind="builtin",
                builtin=snippet,
                source="builtin",
            )
        )
    return items


def list_palette_snippets(
    project_root: Path | None = None,
    *,
    query: str = "",
) -> list[PaletteSnippet]:
    items = _builtin_palette_items()
    for snippet in load_user_snippets(project_root):
        items.append(
            PaletteSnippet(
                id=snippet.id,
                label=snippet.label,
                description=snippet.description,
                text=snippet.text,
                placeholders=snippet.placeholders,
                kind="user",
                builtin=None,
                source=snippet.source,
            )
        )
    normalized = query.strip().lower()
    if not normalized:
        return items
    filtered: list[PaletteSnippet] = []
    for item in items:
        haystack = " ".join(
            part
            for part in (item.label, item.description, item.text, item.id)
            if part
        ).lower()
        if normalized in haystack:
            filtered.append(item)
    return filtered


def filter_palette_snippets(items: list[PaletteSnippet], query: str) -> list[PaletteSnippet]:
    normalized = query.strip().lower()
    if not normalized:
        return list(items)
    return [
        item
        for item in items
        if normalized
        in " ".join(
            part for part in (item.label, item.description, item.text, item.id) if part
        ).lower()
    ]
