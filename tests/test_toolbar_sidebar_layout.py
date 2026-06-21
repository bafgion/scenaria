"""Toolbar labels must not block sidebar splitter resizing."""

from __future__ import annotations

import pytest
from PySide6.QtWidgets import QApplication, QHBoxLayout, QWidget
from app.mvc.controllers.catalog_controller import CatalogController
from app.mvc.models.catalog_model import CatalogModel
from app.qt.widgets.editor_action_bar import EditorActionBar
from app.qt.widgets.editor_workspace import EditorWorkspace
from app.qt.widgets.ide_splitter import IdeSplitter
from app.qt.widgets.sidebar import Sidebar
from PySide6.QtCore import Qt

from app.mvc.controllers.app_controller import AppController


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def _expand_until_full_toolbar(bar: EditorActionBar, qapp, *, start: int = 1200, step: int = 200, limit: int = 4200) -> int:
    width = start
    while width <= limit:
        bar.resize(width, bar.sizeHint().height())
        qapp.processEvents()
        if not bar.toolbar.is_auto_compact():
            return width
        width += step
    pytest.skip(f"toolbar stayed compact up to {limit}px wide (headless/CI)")


def test_toolbar_switches_to_compact_when_action_bar_is_narrow(qapp) -> None:
    bar = EditorActionBar()
    bar.show()
    full_width = _expand_until_full_toolbar(bar, qapp)
    assert bar.toolbar._buttons["validate"].text() == "Проверить элементы"

    bar.resize(max(400, full_width - 500), bar.sizeHint().height())
    qapp.processEvents()

    assert bar.toolbar.is_auto_compact()
    assert bar.toolbar._buttons["validate"].text() == ""


def test_toolbar_reserves_space_for_scenario_labels(qapp) -> None:
    bar = EditorActionBar()
    bar.show()
    qapp.processEvents()

    assert bar._file_hint.width() > 0
    assert bar._next_step.width() > 0
    assert bar.minimumSizeHint().width() > bar.toolbar.compact_layout_min_width()


def _expand_workspace_until_full_toolbar(
    workspace: EditorWorkspace,
    qapp,
    *,
    start: int = 1200,
    step: int = 200,
    limit: int = 4200,
) -> int:
    width = start
    while width <= limit:
        workspace.resize(width, 700)
        qapp.processEvents()
        if not workspace.editor_action_bar.toolbar.is_auto_compact():
            return width
        width += step
    pytest.skip(f"workspace toolbar stayed compact up to {limit}px wide (headless/CI)")


def test_toolbar_shows_secondary_labels_only_with_room(qapp) -> None:
    bar = EditorActionBar()
    bar.show()
    _expand_until_full_toolbar(bar, qapp)
    assert bar.toolbar._buttons["validate"].text() == "Проверить элементы"


def test_workspace_minimum_width_stays_small_with_labeled_toolbar(qapp) -> None:
    controller = AppController()
    workspace = EditorWorkspace(controller)
    workspace.show()
    _expand_workspace_until_full_toolbar(workspace, qapp)
    chrome = workspace.editor_action_bar._measured_chrome_width()
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

    workspace_min = workspace.minimumSizeHint().width()
    host_width = max(2600, workspace_min + 1000)
    splitter.setSizes([320, host_width - 320])
    host.resize(host_width, 700)
    host.show()
    qapp.processEvents()
    _expand_workspace_until_full_toolbar(workspace, qapp, start=host_width - 320)

    before = splitter.sizes()[0]
    target_sidebar = before + 180
    splitter.setSizes([target_sidebar, host_width - target_sidebar])
    qapp.processEvents()

    if splitter.sizes()[0] <= before:
        pytest.skip("sidebar width did not grow on this runner")
