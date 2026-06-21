"""Catalog context menu extensions."""

from __future__ import annotations

import pytest
from PySide6.QtWidgets import QApplication


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_catalog_tree_has_run_file_signal(qapp) -> None:
    from app.qt.widgets.catalog_panel import CatalogTreeView

    tree = CatalogTreeView()
    assert hasattr(tree, "run_file_requested")
    assert hasattr(tree, "run_vanessa_file_requested")
    assert hasattr(tree, "run_vanessa_folder_requested")
    assert hasattr(tree, "run_folder_history_requested")
