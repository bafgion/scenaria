"""Toolbar labels must not block sidebar splitter resizing."""

from __future__ import annotations

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QHBoxLayout, QWidget

from app.mvc.controllers.app_controller import AppController
from app.mvc.controllers.catalog_controller import CatalogController
from app.mvc.models.catalog_model import CatalogModel
from app.qt.widgets.editor_action_bar import EditorActionBar
from app.qt.widgets.editor_workspace import EditorWorkspace
from app.qt.widgets.ide_splitter import IdeSplitter
from app.qt.widgets.sidebar import Sidebar


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def _full_toolbar_width(bar: EditorActionBar) -> int:
    return bar._fixed_chrome_width() + bar.toolbar.full_layout_min_width() + 80


def _resize_for_full_toolbar(bar: EditorActionBar, qapp) -> int:
    bar.show()
    qapp.processEvents()
    width = _full_toolbar_width(bar)
    bar.resize(width, bar.sizeHint().height())
    qapp.processEvents()
    assert not bar.toolbar.is_auto_compact(), (
        f"expected full toolbar at {width}px (chrome={bar._fixed_chrome_width()})"
    )
    return width


def _resize_workspace_for_full_toolbar(workspace: EditorWorkspace, qapp, *, width: int | None = None) -> int:
    workspace.show()
    qapp.processEvents()
    bar = workspace.editor_action_bar
    if width is None:
        width = _full_toolbar_width(bar)
    workspace.resize(width, 700)
    qapp.processEvents()
    assert not bar.toolbar.is_auto_compact(), f"expected full toolbar at workspace width {width}px"
    return width


def test_toolbar_switches_to_compact_when_action_bar_is_narrow(qapp) -> None:
    bar = EditorActionBar()
    full_width = _resize_for_full_toolbar(bar, qapp)
    assert bar.toolbar._buttons["validate"].text() == "Селекторы на странице"

    bar.resize(max(400, full_width - 500), bar.sizeHint().height())
    qapp.processEvents()

    assert bar.toolbar.is_auto_compact()
    assert bar.toolbar._buttons["validate"].text() == ""


def test_toolbar_reserves_space_for_scenario_labels(qapp) -> None:
    bar = EditorActionBar()
    bar.show()
    qapp.processEvents()

    assert bar._file_hint.width() > 0
    assert bar.minimumSizeHint().width() > bar.toolbar.compact_layout_min_width()


def test_toolbar_hides_scenario_chip_on_welcome(qapp) -> None:
    bar = EditorActionBar()
    bar.show()
    bar.set_run_target(
        title="Старт",
        path=None,
        unapplied=False,
        unsaved=False,
        is_welcome=True,
    )
    qapp.processEvents()

    assert not bar._run_box.isVisible()
    assert bar._toolbar_sep.isVisible()
    assert not bar._url_sep.isVisible()


def test_toolbar_shows_scenario_chip_for_open_file(qapp) -> None:
    bar = EditorActionBar()
    bar.show()
    bar.set_run_target(
        title="test2.feature",
        path=None,
        unapplied=False,
        unsaved=True,
    )
    qapp.processEvents()

    assert bar._run_box.isVisible()
    assert bar._toolbar_sep.isVisible()
    assert bar._url_sep.isVisible()
    assert "test2.feature" in bar._file_name.text()


def test_toolbar_elides_long_scenario_name_in_middle(qapp) -> None:
    bar = EditorActionBar()
    bar.show()
    bar.set_run_target(
        title="very_long_scenario_name_for_toolbar_preview.feature",
        path=None,
        unapplied=False,
        unsaved=True,
    )
    qapp.processEvents()

    assert "..." in bar._file_name.text() or "…" in bar._file_name.text()


def test_toolbar_shows_secondary_labels_only_with_room(qapp) -> None:
    bar = EditorActionBar()
    _resize_for_full_toolbar(bar, qapp)
    assert bar.toolbar._buttons["validate"].text() == "Селекторы на странице"


def test_workspace_minimum_width_stays_small_with_labeled_toolbar(qapp) -> None:
    controller = AppController()
    workspace = EditorWorkspace(controller)
    _resize_workspace_for_full_toolbar(workspace, qapp)
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
    host_width = max(3200, workspace_min + 1200)
    splitter.setSizes([320, host_width - 320])
    host.resize(host_width, 700)
    host.show()
    qapp.processEvents()
    _resize_workspace_for_full_toolbar(workspace, qapp, width=host_width - 320)

    before = splitter.sizes()[0]
    target_sidebar = before + 200
    splitter.setSizes([target_sidebar, host_width - target_sidebar])
    qapp.processEvents()

    assert splitter.sizes()[0] > before, (
        f"sidebar width did not grow: before={before}, after={splitter.sizes()[0]}"
    )
