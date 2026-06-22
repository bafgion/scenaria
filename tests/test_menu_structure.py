"""Main menu workflow structure (F4-1 / F4-2)."""

from __future__ import annotations

import pytest
from PySide6.QtWidgets import QApplication, QMenuBar


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def _top_level_menus(window) -> list[str]:
    bar: QMenuBar = window.menuBar()
    return [action.text() for action in bar.actions()]


def _menu_action_labels(menu) -> list[str]:
    labels: list[str] = []
    for action in menu.actions():
        if action.isSeparator():
            continue
        if action.menu() is not None:
            labels.append(action.text())
        else:
            labels.append(action.text())
    return labels


def test_main_menu_top_level_structure(qapp) -> None:
    from app.mvc.controllers.app_controller import AppController
    from app.qt.main_window import MainWindow

    window = MainWindow(AppController())
    titles = _top_level_menus(window)
    assert titles == [
        "Проект",
        "Сценарий",
        "Запись и тест",
        "Плагины",
        "Вид",
        "Справка",
    ]
    assert "Файл" not in titles
    assert "Правка" not in titles
    assert "Запуск" not in titles



def test_scenario_menu_has_file_and_edit_actions(qapp) -> None:
    from app.mvc.controllers.app_controller import AppController
    from app.qt.main_window import MainWindow

    window = MainWindow(AppController())
    labels = _menu_action_labels(window._scenario_menu)
    assert "Новый" in labels
    assert "Сохранить" in labels
    assert "Найти и заменить…" in labels
    assert "Теги сценария…" in labels
    assert "Синтаксис Gherkin" in labels
    assert "Отменить шаг записи" not in labels


def test_project_menu_has_settings(qapp) -> None:
    from app.mvc.controllers.app_controller import AppController
    from app.qt.main_window import MainWindow

    window = MainWindow(AppController())
    bar = window.menuBar()
    project_menu = None
    for action in bar.actions():
        if action.text() == "Проект":
            project_menu = action.menu()
            break
    assert project_menu is not None
    labels = _menu_action_labels(project_menu)
    assert "Настройки…" in labels
    assert window._act_settings.shortcut().toString() in {"Ctrl+,", "Ctrl+,"}


def test_record_test_menu_has_playback_and_undo_record_step(qapp) -> None:
    from app.mvc.controllers.app_controller import AppController
    from app.qt.main_window import MainWindow

    window = MainWindow(AppController())
    labels = _menu_action_labels(window._record_test_menu)
    assert "Запись" in labels
    assert "Запустить" in labels
    assert "Селекторы на странице" in labels
    assert "Настройки…" in labels
    assert "Отменить шаг записи" in labels
    assert "Открыть последний отчёт" in labels


def test_plugins_menu_not_in_record_test(qapp) -> None:
    from app.mvc.controllers.app_controller import AppController
    from app.qt.main_window import MainWindow

    window = MainWindow(AppController())
    record_labels = _menu_action_labels(window._record_test_menu)
    assert not any("Vanessa" in label for label in record_labels)
    assert not any(label.startswith("Пакетный запуск") for label in record_labels)
    assert not any(label.startswith("Установить") for label in record_labels)

    plugin_labels = _menu_action_labels(window._plugins_menu)
    assert plugin_labels, "меню «Плагины» не должно быть пустым"


def test_runner_segment_hidden_without_project(qapp) -> None:
    from app.mvc.controllers.app_controller import AppController
    from app.qt.main_window import MainWindow

    window = MainWindow(AppController())
    window._sync_status_runner()
    assert not window.status_bar._runner.isVisible()


def test_shortcuts_preserved(qapp) -> None:
    from app.mvc.controllers.app_controller import AppController
    from app.qt.main_window import MainWindow

    window = MainWindow(AppController())
    assert window._act_save.shortcut().toString() in {"Ctrl+S", "Ctrl+S,"}
    assert "Ctrl+R" in window._act_record.shortcut().toString()
    assert "Ctrl+B" in window._act_browser.shortcut().toString()
