"""Tests for browser_context_options with TestClient."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.browser_config import browser_context_options
from app.test_clients import save_test_client_from_context


class _FakeContext:
    def storage_state(self) -> dict:
        return {"cookies": [{"name": "sid", "value": "1"}]}


def test_browser_context_options_without_test_client_is_clean(tmp_path: Path) -> None:
    save_test_client_from_context(_FakeContext(), "Legacy", project_root=tmp_path)
    opts = browser_context_options(
        "https://example.com",
        settings={},
        project_root=tmp_path,
        test_client=None,
    )
    assert "storage_state" not in opts


def test_browser_context_options_with_test_client(tmp_path: Path) -> None:
    save_test_client_from_context(_FakeContext(), "UserA", project_root=tmp_path)
    opts = browser_context_options(
        "https://example.com",
        settings={},
        project_root=tmp_path,
        test_client="UserA",
    )
    assert opts["storage_state"]["cookies"][0]["name"] == "sid"


def test_browser_context_options_missing_client_raises(tmp_path: Path) -> None:
    from app.test_clients import TestClientNotFoundError

    with pytest.raises(TestClientNotFoundError):
        browser_context_options(
            "https://example.com",
            settings={},
            project_root=tmp_path,
            test_client="Ghost",
        )
