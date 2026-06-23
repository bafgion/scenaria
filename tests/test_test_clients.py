"""Tests for named TestClient storage."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.test_clients import (
    TestClientNotFoundError,
    list_test_clients,
    remove_test_client,
    require_test_client,
    save_test_client_from_context,
    storage_state_for_test_client,
)


class _FakeContext:
    def __init__(self, state: dict) -> None:
        self._state = state

    def storage_state(self) -> dict:
        return self._state


def test_save_and_load_test_client(tmp_path: Path) -> None:
    state = {"cookies": [{"name": "sid", "value": "abc"}]}
    path = save_test_client_from_context(
        _FakeContext(state),
        "ВолковаА_ГК",
        project_root=tmp_path,
    )
    assert path.is_file()
    loaded = storage_state_for_test_client("ВолковаА_ГК", tmp_path)
    assert loaded == state
    clients = list_test_clients(tmp_path)
    assert len(clients) == 1
    assert clients[0].name == "ВолковаА_ГК"


def test_require_test_client_raises(tmp_path: Path) -> None:
    with pytest.raises(TestClientNotFoundError):
        require_test_client("Missing", tmp_path)


def test_remove_test_client(tmp_path: Path) -> None:
    save_test_client_from_context(_FakeContext({"cookies": []}), "A", project_root=tmp_path)
    assert remove_test_client("A", tmp_path)
    assert storage_state_for_test_client("A", tmp_path) is None
