"""Tests for user snippet storage."""

from __future__ import annotations

import json
from pathlib import Path

from app.snippet_store import (
    UserSnippet,
    extract_placeholders,
    list_palette_snippets,
    load_user_snippets,
    resolve_placeholders,
    save_user_snippets,
)


def test_extract_placeholders() -> None:
    assert extract_placeholders('Допустим открыт "{{url}}"') == ("url",)
    assert extract_placeholders("no vars") == ()


def test_resolve_placeholders() -> None:
    text = 'Допустим открыт "{{url}}"\n\tИ ввожу "{{login}}" в "#email"'
    resolved = resolve_placeholders(text, {"url": "https://a.com", "login": "qa@test.com"})
    assert "https://a.com" in resolved
    assert "qa@test.com" in resolved
    assert "{{" not in resolved


def test_load_and_merge_user_snippets(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("app.snippet_store.global_snippets_path", lambda: tmp_path / "global.json")
    global_path = tmp_path / "global.json"
    global_path.write_text(
        json.dumps(
            {
                "version": 1,
                "snippets": [
                    {
                        "id": "shared",
                        "label": "Shared",
                        "description": "global",
                        "text": "global text",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    (project_dir / ".scenaria").mkdir()
    (project_dir / ".scenaria" / "snippets.json").write_text(
        json.dumps(
            {
                "version": 1,
                "snippets": [
                    {
                        "id": "shared",
                        "label": "Shared project",
                        "text": "project text",
                    },
                    {
                        "id": "local",
                        "label": "Local",
                        "text": "local text",
                    },
                ],
            }
        ),
        encoding="utf-8",
    )
    snippets = load_user_snippets(project_dir)
    by_id = {item.id: item for item in snippets}
    assert by_id["shared"].text == "project text"
    assert by_id["shared"].source == "project"
    assert by_id["local"].label == "Local"


def test_save_user_snippets_writes_json(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("app.snippet_store.global_snippets_path", lambda: tmp_path / "snippets.json")
    path = save_user_snippets(
        [
            UserSnippet(
                id="login",
                label="Login",
                description="demo",
                text='Допустим открыт "{{url}}"',
                placeholders=("url",),
            )
        ]
    )
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["version"] == 1
    assert payload["snippets"][0]["id"] == "login"


def test_list_palette_includes_builtin_and_user(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("app.snippet_store.global_snippets_path", lambda: tmp_path / "snippets.json")
    save_user_snippets(
        [UserSnippet(id="x", label="Custom login", description="", text="И нажимаю \"#x\"")],
    )
    items = list_palette_snippets(tmp_path)
    assert any(item.kind == "builtin" for item in items)
    assert any(item.id == "x" for item in items)


def test_list_palette_filters_by_query(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("app.snippet_store.global_snippets_path", lambda: tmp_path / "snippets.json")
    save_user_snippets(
        [
            UserSnippet(id="a", label="Checkout flow", description="", text="step a"),
            UserSnippet(id="b", label="Login flow", description="", text="step b"),
        ],
    )
    items = list_palette_snippets(tmp_path, query="checkout flow")
    assert len(items) == 1
    assert items[0].id == "a"
