"""Catalog tree should shrink with the sidebar splitter."""

from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from app.mvc.models.catalog_model import CatalogNode
from app.qt.widgets.catalog_panel import CatalogTreeView


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def _long_file_tree() -> CatalogNode:
    return CatalogNode(
        kind="root",
        path=Path("C:/project"),
        name="project",
        children=[
            CatalogNode(
                kind="file",
                path=Path("C:/project/very-long-scenario-name-with-domain.feature"),
                name="very-long-scenario-name-with-domain",
                step_count=12,
                domain="subdomain.example.com",
            )
        ],
    )


def test_tree_minimum_width_ignores_long_labels(qapp) -> None:
    tree = CatalogTreeView()
    tree.show()
    tree.show_tree(_long_file_tree(), expand_all=True)
    tree.resize(130, 320)
    qapp.processEvents()

    assert tree.minimumSizeHint().width() == 0
    assert tree.horizontalScrollBarPolicy() == Qt.ScrollBarPolicy.ScrollBarAlwaysOff
    assert tree.columnWidth(0) <= tree.viewport().width()


def test_tree_column_tracks_viewport_on_resize(qapp) -> None:
    tree = CatalogTreeView()
    tree.show()
    tree.show_tree(_long_file_tree(), expand_all=True)
    tree.resize(200, 320)
    qapp.processEvents()
    wide = tree.columnWidth(0)
    tree.resize(150, 320)
    qapp.processEvents()
    narrow = tree.columnWidth(0)

    assert narrow < wide
    assert narrow == tree.viewport().width()
