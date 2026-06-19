"""Russian labels on standard dialog buttons."""

from __future__ import annotations

import pytest
from PySide6.QtWidgets import QApplication

from app.qt.dialogs import (
    BTN_CANCEL,
    BTN_CLOSE,
    BTN_NO,
    BTN_OK,
    BTN_YES,
    close_button_box,
    ok_cancel_button_box,
)


@pytest.fixture(scope="module")
def _qt_app():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


def test_ok_cancel_button_box_labels(_qt_app) -> None:
    box = ok_cancel_button_box()
    labels = {btn.text() for btn in box.buttons()}
    assert labels == {BTN_OK, BTN_CANCEL}


def test_close_button_box_label(_qt_app) -> None:
    box = close_button_box()
    assert [btn.text() for btn in box.buttons()] == [BTN_CLOSE]


def test_confirm_button_constants() -> None:
    assert BTN_YES == "Да"
    assert BTN_NO == "Нет"
