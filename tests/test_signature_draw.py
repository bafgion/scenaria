"""Tests for signature canvas drawing."""

from __future__ import annotations

from unittest.mock import MagicMock, call

from app.signature_draw import draw_signature_on_canvas


def test_draw_signature_moves_mouse() -> None:
    page = MagicMock()
    locator = page.locator.return_value.first
    locator.bounding_box.return_value = {"x": 100, "y": 200, "width": 300, "height": 150}

    draw_signature_on_canvas(page, "canvas")

    locator.wait_for.assert_called_once()
    page.mouse.down.assert_called_once()
    page.mouse.up.assert_called_once()
    assert page.mouse.move.call_count >= 6
