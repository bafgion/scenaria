"""Toolbar labels must not block sidebar splitter resizing."""

from __future__ import annotations

import pytest
from PySide6.QtWidgets import QApplication, QHBoxLayout, QWidget

from app.mvc.controllers.app_controller import AppController
from app.mvc.controllers.catalog_controller import CatalogController
from app.mvc.models.catalog_model import CatalogModel
from app.qt.widgets.editor_action_bar import EditorActionBar
from app.qt.widgets.editor_workspace import EditorWorkspace
from app.qt.widgets.ide_splitter import IdeSplitter
from app.qt.widgets.sidebar import Sidebar
from PySide6.QtCore import Qt


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_toolbar_switches_to_compact_when_action_bar_is_narrow(qapp) -> None:
    bar = EditorActionBar()
    bar.show()
    bar.resize(1400, bar.sizeHint().height())
    qapp.processEvents()
    wide_toolbar_hint = bar.toolbar.sizeHint().width()

    bar.resize(820, bar.sizeHint().height())
    qapp.processEvents()

    assert bar.toolbar._compact
    assert bar.toolbar.sizeHint().width() < wide_toolbar_hint


def test_toolbar_reserves_space_for_scenario_labels(qapp) -> None:
    bar = EditorActionBar()
    bar.show()
    qapp.processEvents()

    assert bar._file_hint.width() > 0
    assert bar._next_step.width() > 0
    assert bar.minimumSizeHint().width() > bar.toolbar.compact_layout_min_width()


def _wide_enough_for_full_toolbar(bar: EditorActionBar) -> int:
    return bar._fixed_chrome_width() + bar.toolbar.full_layout_min_width() + 48


def test_toolbar_shows_secondary_labels_only_with_room(qapp) -> None:
    bar = EditorActionBar()
    bar.show()
    bar.resize(_wide_enough_for_full_toolbar(bar), bar.sizeHint().height())
    qapp.processEvents()

    assert not bar.toolbar._compact
    assert bar.toolbar._buttons["validate"].text() == "Проверить элементы"


def test_workspace_minimum_width_stays_small_with_labeled_toolbar(qapp) -> None:
    controller = AppController()
    workspace = EditorWorkspace(controller)
    workspace.show()
    bar = workspace.editor_action_bar
    workspace.resize(_wide_enough_for_full_toolbar(bar), 700)
    qapp.processEvents()

    assert not bar.toolbar._compact
    chrome = bar._measured_chrome_width()
    assert workspace.minimumSizeHint().width() > chrome


def test_side_splitter_moves_when_toolbar_shows_labels(qapp) -> None:
    host = QWidget()
    host.setMinimumSize(0, 0)
    layout = QHBoxLayout(host)
    layout.setContentsMargins(0, 0, 0, 0)

    model = CatalogModel()
    catalog_controller = CatalogController(model)
    sidebar = Sidebar(model, catalog_controller, host)
    workspace = EditorWorkspace(AppController(), host)

    splitter = IdeSplitter(Qt.Orientation.Horizontal, host)
    splitter.addWidget(sidebar)
    splitter.addWidget(workspace)
    layout.addWidget(splitter)

    host_width = 2000
    splitter.setSizes([260, host_width - 260])
    host.resize(host_width, 700)
    host.show()
    qapp.processEvents()

    assert not workspace.editor_action_bar.toolbar._compact

    splitter.setSizes([500, host_width - 500])
    qapp.processEvents()
    sizes = splitter.sizes()

    assert sizes[0] > 260
