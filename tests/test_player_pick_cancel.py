"""Player picker cancel during blocking pick()."""

from __future__ import annotations

from unittest.mock import MagicMock

from app.player import ScenarioPlayer, _PICK_CANCEL


def test_pick_pump_cancel_unblocks_active_pick() -> None:
    player = ScenarioPlayer()
    page = MagicMock()
    page.is_closed.return_value = False
    picker = MagicMock()
    player._picker = picker

    completed: list[str | None] = []

    def pick(page_arg, context, *, pump, timeout=300.0):
        pump()
        return None

    picker.pick.side_effect = pick

    player._pick_requests.put((lambda value: completed.append(value), None))
    player._pick_requests.put(_PICK_CANCEL)

    player._service_pick_requests(page)

    assert completed == [None]
    picker.cancel_active.assert_called()


def test_cancel_pending_picks_drains_queue() -> None:
    player = ScenarioPlayer()
    page = MagicMock()
    picker = MagicMock()
    player._picker = picker

    results: list[str | None] = []
    player._pick_requests.put((lambda value: results.append(value), None))
    player._pick_requests.put((lambda value: results.append(value), None))

    player._cancel_pending_picks(page)

    assert results == [None, None]
    picker.cancel_active.assert_called_once_with(page)
