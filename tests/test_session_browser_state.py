"""Session browser flags for detached test playback."""

from __future__ import annotations

from unittest.mock import MagicMock

from app.mvc.models.session_model import SessionModel
from app.player import ScenarioPlayer


def test_browser_session_active() -> None:
    session = SessionModel()
    assert not session.browser_session_active()
    session.browser_open = True
    assert session.browser_session_active()
    session.browser_open = False
    session.player_browser = True
    assert session.browser_session_active()


def test_scenario_player_browser_open_property() -> None:
    player = ScenarioPlayer()
    assert not player.browser_open
    browser = MagicMock()
    browser.is_connected.return_value = True
    page = MagicMock()
    page.is_closed.return_value = False
    context = MagicMock()
    context.pages = [page]
    player._browser = browser
    player._context = context
    player._page = page
    assert player.browser_open
    page.is_closed.return_value = True
    assert not player.browser_open
