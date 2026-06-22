"""Tests for backlog tasks A2-3, A4-3, A6-1, B4-2."""

from __future__ import annotations

import json
from pathlib import Path

from app.browser_compat import compatibility_warning, list_engine_warnings
from app.gherkin_refactor import (
    collapse_blank_lines_between_steps,
    normalize_step_indents,
    update_start_urls,
)
from app.gherkin_ru import STEP_INDENT
from app.snippet_store import append_user_snippet, load_user_snippets, slugify_snippet_id, UserSnippet
from app.upload_helpers import resolve_upload_path, validate_upload_path

TAB = STEP_INDENT


def test_update_start_urls_replaces_goto_steps() -> None:
    text = (
        f"{TAB}Допустим открыт \"https://old.com\"\n"
        f"{TAB}И нажимаю \"button\"\n"
        f"{TAB}И открыт \"https://also-old.com\""
    )
    updated, count = update_start_urls(text, "https://new.com")
    assert count == 2
    assert "https://new.com" in updated
    assert "old.com" not in updated


def test_normalize_step_indents_uses_tabs() -> None:
    text = "  Допустим открыт \"https://a.com\""
    normalized = normalize_step_indents(text)
    assert normalized.startswith(f"{TAB}Допустим")


def test_normalize_step_indents_preserves_selectors() -> None:
    text = (
        "Сценарий: T\n"
        f'{TAB}Допустим открыт "https://a.com"\n'
        f'    И нажимаю "button:has-text(\\"Далее\\")"\n'
    )
    normalized = normalize_step_indents(text)
    assert ':has-text(\\"Далее\\")' in normalized
    assert '    И нажимаю' not in normalized


def test_collapse_blank_lines_between_steps() -> None:
    text = f"{TAB}Допустим открыт \"https://a.com\"\n\n{TAB}И нажимаю \"x\""
    collapsed = collapse_blank_lines_between_steps(text)
    assert "\n\n" not in collapsed


def test_append_user_snippet(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("app.snippet_store.get_root", lambda: tmp_path)
    project_snippets = tmp_path / ".scenaria" / "snippets.json"
    snippet = UserSnippet(
        id=slugify_snippet_id("Login block"),
        label="Login block",
        description="demo",
        text=f"{TAB}И нажимаю \"#login\"",
    )
    append_user_snippet(snippet, project_root=tmp_path, prefer_project=True)
    assert project_snippets.is_file()
    loaded = load_user_snippets(tmp_path)
    assert any(item.id == snippet.id for item in loaded)


def test_resolve_upload_path_from_testdata(tmp_path: Path) -> None:
    testdata = tmp_path / "testdata"
    testdata.mkdir()
    sample = testdata / "cv.pdf"
    sample.write_text("pdf", encoding="utf-8")
    resolved = resolve_upload_path("cv.pdf", tmp_path)
    assert resolved == sample.resolve()
    assert validate_upload_path("missing.pdf", tmp_path) is not None


def test_browser_compat_warning_for_firefox_signature() -> None:
    warn = compatibility_warning("draw_signature", "firefox")
    assert warn
    warnings = list_engine_warnings([{"action": "draw_signature"}], "firefox")
    assert warnings
