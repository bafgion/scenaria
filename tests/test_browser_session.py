"""Tests for browser session storage."""

from __future__ import annotations

from pathlib import Path

from app.browser_session import (
    list_saved_sessions,
    remove_saved_session,
    save_session_from_context,
    session_origin,
    storage_state_for_url,
)


class _FakeContext:
    def __init__(self, state: dict) -> None:
        self._state = state

    def storage_state(self) -> dict:
        return self._state


def test_session_origin_normalizes_url() -> None:
    assert session_origin("https://Stage.Example.com/path") == "https://stage.example.com"


def test_save_and_load_storage_state(tmp_path: Path) -> None:
    origin = "https://shop.test"
    state = {"cookies": [{"name": "sid", "value": "abc", "domain": "shop.test", "path": "/"}]}
    path = save_session_from_context(_FakeContext(state), origin, label="staging", project_root=tmp_path)
    assert path.is_file()
    loaded = storage_state_for_url("https://shop.test/page", tmp_path)
    assert loaded == state
    sessions = list_saved_sessions(tmp_path)
    assert len(sessions) == 1
    assert sessions[0].origin == origin
    assert sessions[0].label == "staging"


def test_different_origins_do_not_overlap(tmp_path: Path) -> None:
    save_session_from_context(_FakeContext({"cookies": []}), "https://a.test", project_root=tmp_path)
    save_session_from_context(_FakeContext({"cookies": [{"name": "x"}]}), "https://b.test", project_root=tmp_path)
    assert storage_state_for_url("https://a.test", tmp_path) == {"cookies": []}
    assert storage_state_for_url("https://b.test", tmp_path) == {"cookies": [{"name": "x"}]}


def test_remove_saved_session(tmp_path: Path) -> None:
    save_session_from_context(_FakeContext({"cookies": []}), "https://x.test", project_root=tmp_path)
    assert remove_saved_session("https://x.test", tmp_path)
    assert storage_state_for_url("https://x.test", tmp_path) is None
