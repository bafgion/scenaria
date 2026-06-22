"""Welcome checklist and batch selection UI."""

from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtWidgets import QApplication

from app.qt.widgets.catalog_panel import CatalogTreeView
from app.qt.widgets.welcome_panel import WelcomePanel


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_welcome_checklist_states(qapp) -> None:
    panel = WelcomePanel()
    panel.update_checklist(
        project_open=False,
        recorded=False,
        played_success=False,
        dismissed=False,
    )
    assert "→" in panel._checklist_rows[1].text()
    assert "○" in panel._checklist_rows[2].text()
    assert "○" in panel._checklist_rows[3].text()

    panel.update_checklist(
        project_open=True,
        recorded=False,
        played_success=False,
        dismissed=False,
    )
    assert "✓" in panel._checklist_rows[1].text()
    assert "→" in panel._checklist_rows[2].text()

    panel.update_checklist(
        project_open=True,
        recorded=True,
        played_success=False,
        dismissed=False,
    )
    assert "✓" in panel._checklist_rows[2].text()
    assert "→" in panel._checklist_rows[3].text()

    panel.update_checklist(
        project_open=True,
        recorded=True,
        played_success=False,
        dismissed=True,
    )
    assert not panel._checklist_box.isVisible()


def test_catalog_selection_mode_click(tmp_path: Path) -> None:
    feature = tmp_path / "demo.feature"
    feature.write_text('Функция: demo\n  Сценарий: s\n    Дано открываю "https://example.com"\n', encoding="utf-8")
    toggled: list[Path] = []

    tree = CatalogTreeView()
    tree.set_selection_mode(True)
    tree.set_toggle_run_selection_handler(lambda path: toggled.append(path))

    from app.mvc.models.catalog_model import CatalogNode

    node = CatalogNode("file", feature, feature.name)
    tree.show_tree(node, expand_all=True)

    model = tree.model()
    assert model is not None
    root = model.item(0)
    assert root is not None
    index = root.index()
    assert "☐" in root.text()

    from PySide6.QtCore import QPoint, Qt
    from PySide6.QtGui import QMouseEvent
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance()
    assert app is not None
    pos = tree.visualRect(index).center()
    event = QMouseEvent(
        QMouseEvent.Type.MouseButtonPress,
        QPoint(pos),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    tree.mousePressEvent(event)
    assert toggled == [feature.resolve()]
