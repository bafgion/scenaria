"""Menu bar construction for MainWindow (T2-2)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtGui import QAction, QKeySequence

from app.feature_store import get_root
from app.plugins.registry import get_registry
from app.qt.plugin_host import PluginsMenuHost
from app.qt.update_ui import updates_supported
from app.settings import load_settings

if TYPE_CHECKING:
    from app.qt.main_window import MainWindow


def build_menus(window: MainWindow) -> None:
    """Attach menu bar actions to *window* (sets QAction attributes on window)."""
    bar = window.menuBar()
    sc = window._controller.scenario_controller
    rec = window._controller.recording

    project_menu = bar.addMenu("Проект")
    project_menu.addAction("Открыть проект…", window._open_project)
    window._act_settings = QAction("Настройки…", window)
    window._act_settings.setShortcut(QKeySequence("Ctrl+,"))
    window._act_settings.triggered.connect(window._open_settings)
    project_menu.addAction(window._act_settings)
    project_menu.addSeparator()
    quit_action = QAction("Выход", window)
    quit_action.setShortcut(QKeySequence.StandardKey.Quit)
    quit_action.triggered.connect(window.close)
    project_menu.addAction(quit_action)

    scenario_menu = bar.addMenu("Сценарий")
    window._scenario_menu = scenario_menu
    window._act_new = QAction("Новый", window)
    window._act_new.setShortcut(QKeySequence.StandardKey.New)
    window._act_new.triggered.connect(window._new_scenario)
    scenario_menu.addAction(window._act_new)
    window._act_open_file = QAction("Открыть…", window)
    window._act_open_file.setShortcut(QKeySequence.StandardKey.Open)
    window._act_open_file.triggered.connect(window._open_feature_file)
    scenario_menu.addAction(window._act_open_file)
    window._act_save = QAction("Сохранить", window)
    window._act_save.setShortcut(QKeySequence.StandardKey.Save)
    window._act_save.triggered.connect(window._save_current)
    scenario_menu.addAction(window._act_save)
    scenario_menu.addAction("Дублировать", sc.duplicate_selected_feature)
    scenario_menu.addAction("Удалить", window._delete_selected_feature)
    scenario_menu.addSeparator()
    scenario_menu.addAction("Экспорт .feature…", window._export_with_apply(sc.export_feature_file))
    scenario_menu.addAction(
        "Экспорт Playwright (TypeScript)…",
        window._export_with_apply(sc.export_playwright_file),
    )
    scenario_menu.addAction(
        "Экспорт Playwright (Python)…",
        window._export_with_apply(lambda: sc.export_playwright_file(python=True)),
    )
    scenario_menu.addAction("Экспорт ZIP…", window._export_with_apply(sc.export_zip_file))
    scenario_menu.addAction("Экспорт JSON…", window._export_with_apply(sc.export_json_file))
    scenario_menu.addAction("Импорт…", sc.import_feature_file)
    scenario_menu.addAction("Импорт JSON…", sc.import_json_file)
    scenario_menu.addSeparator()
    find_action = scenario_menu.addAction("Найти и заменить…", window._open_find_replace)
    find_action.setShortcut(QKeySequence("Ctrl+H"))
    scenario_menu.addAction("Замена по проекту…", window._open_project_replace)
    refactor_menu = scenario_menu.addMenu("Рефакторинг")
    refactor_menu.addAction("Обновить стартовый URL…", window._refactor_update_start_urls)
    refactor_menu.addAction("Нормализовать отступы шагов", window._refactor_normalize_indents)
    refactor_menu.addAction("Удалить пустые строки между шагами", window._refactor_collapse_blank_lines)
    palette_action = scenario_menu.addAction("Палитра сниппетов…", window._open_snippet_palette)
    palette_action.setShortcut(QKeySequence("Ctrl+Shift+Space"))
    scenario_menu.addSeparator()
    scenario_menu.addAction("Обновить сценарий", window.workspace.gherkin_panel._apply).setShortcut(
        QKeySequence("Ctrl+Shift+S")
    )
    scenario_menu.addAction("Синтаксис Gherkin", window.workspace.gherkin_panel._validate)
    scenario_menu.addSeparator()
    scenario_menu.addAction(
        "Наведение для меню…",
        window.workspace.gherkin_panel.insert_hover_step,
    )
    scenario_menu.addAction(
        "Починить клик с hover-меню…",
        window.workspace.gherkin_panel.fix_menu_click_at_cursor,
    )
    scenario_menu.addSeparator()
    scenario_menu.addAction("Теги сценария…", window._edit_scenario_tags)

    record_test_menu = bar.addMenu("Запись и тест")
    window._record_test_menu = record_test_menu
    window._act_browser = QAction("Браузер", window)
    window._act_browser.setShortcut(QKeySequence("Ctrl+B"))
    window._act_browser.triggered.connect(lambda: rec.open_browser(window._start_url()))
    record_test_menu.addAction(window._act_browser)
    record_test_menu.addAction("Закрыть браузер", rec.close_browser)
    record_test_menu.addSeparator()
    record_test_menu.addAction("Стартовый URL…", window._edit_start_url)
    record_test_menu.addAction("HTTP-авторизация для сайтов…", window._edit_http_auth)
    record_test_menu.addAction("TestClient…", window._edit_browser_sessions)
    record_test_menu.addAction("URL из вкладки", rec.fetch_url_from_tab)
    record_test_menu.addSeparator()
    window._act_record = QAction("Запись", window)
    window._act_record.setShortcut(QKeySequence("Ctrl+R"))
    window._act_record.triggered.connect(lambda: rec.start_recording(window._start_url()))
    record_test_menu.addAction(window._act_record)
    window._act_stop = QAction("Стоп", window)
    window._act_stop.triggered.connect(window._stop_active_run)
    record_test_menu.addAction(window._act_stop)
    record_test_menu.addAction("Пауза", rec.toggle_pause)
    record_test_menu.addAction("Отменить шаг записи", rec.undo_last_step)
    record_test_menu.addSeparator()
    window._act_play = QAction("Запустить", window)
    window._act_play.setShortcut(QKeySequence("Ctrl+Return"))
    window._act_play.triggered.connect(window._play_with_apply)
    record_test_menu.addAction(window._act_play)
    record_test_menu.addAction("Селекторы на странице", window._validate_with_apply)
    window._act_run_selected = QAction("Запустить выбранные", window)
    window._act_run_selected.triggered.connect(window._run_selected_features)
    record_test_menu.addAction(window._act_run_selected)
    record_test_menu.addAction("Запустить все сценарии проекта", rec.run_project_suite)
    record_test_menu.addAction("Запустить сценарии с тегом…", window._run_project_tag)
    record_test_menu.addAction("Указать элемент…", rec.pick_selector)
    record_test_menu.addAction("Быстрая запись", lambda: rec.quick_record(window._start_url()))
    record_test_menu.addSeparator()
    window._act_filter = QAction("Только важные", window)
    window._act_filter.setCheckable(True)
    window._act_filter.setChecked(window._controller.session.filter_recording)
    window._act_filter.toggled.connect(window._on_filter_toggled)
    record_test_menu.addAction(window._act_filter)
    window._act_nav_only = QAction("Только ссылки", window)
    window._act_nav_only.setCheckable(True)
    window._act_nav_only.setChecked(window._controller.session.nav_only_recording)
    window._act_nav_only.toggled.connect(window._on_nav_only_toggled)
    record_test_menu.addAction(window._act_nav_only)
    window._act_headless = QAction("Без окна браузера", window)
    window._act_headless.setCheckable(True)
    window._act_headless.setChecked(window._controller.session.headless)
    window._act_headless.toggled.connect(window._on_headless_toggled)
    record_test_menu.addAction(window._act_headless)
    record_test_menu.addSeparator()
    record_test_menu.addAction("Настройки…", lambda: window._open_settings(tab="recording"))
    record_test_menu.addAction("Открыть последний отчёт", window._open_latest_report)

    window._plugins_menu = bar.addMenu("Плагины")
    window._plugins_menu_actions: list[QAction] = []
    window._plugins_menu_separator: QAction | None = None
    refresh_plugins_menu(window)

    view_menu = bar.addMenu("Вид")
    view_menu.addAction("Старт", lambda: window.workspace.ensure_welcome_tab(activate=True))
    view_menu.addAction("Сценарии", lambda: window.activity_bar.explorer_btn.setChecked(True))
    view_menu.addAction("Журнал", lambda: window._show_bottom_panel("log"))
    view_menu.addAction("Результаты", lambda: window._show_bottom_panel("results"))
    view_menu.addAction("Проверка селекторов", lambda: window._show_bottom_panel("validate"))
    view_menu.addAction("Ошибка", lambda: window._show_bottom_panel("error"))
    view_menu.addSeparator()
    view_menu.addAction("Сбросить макет окон", window._reset_layout)
    window._act_toolbar_compact = QAction("Компактная панель", window)
    window._act_toolbar_compact.setCheckable(True)
    window._act_toolbar_compact.setChecked(bool(load_settings().get("toolbar_compact")))
    window._act_toolbar_compact.toggled.connect(window._on_toolbar_compact_toggled)
    view_menu.addAction(window._act_toolbar_compact)

    help_menu = bar.addMenu("Справка")
    help_menu.addAction("Справка…", window._open_step_help).setShortcut("F1")
    help_menu.addAction("Горячие клавиши", window._show_hotkeys).setShortcut("Shift+F1")
    if updates_supported():
        help_menu.addAction("Проверить обновления…", window._check_updates_manual)
    help_menu.addAction("О программе", window._show_about)


def refresh_plugins_menu(window: MainWindow) -> None:
    for action in window._plugins_menu_actions:
        window._plugins_menu.removeAction(action)
    window._plugins_menu_actions.clear()
    if window._plugins_menu_separator is not None:
        window._plugins_menu.removeAction(window._plugins_menu_separator)
        window._plugins_menu_separator = None

    registry = get_registry()
    registry.reload(project_root=get_root())
    for info in registry.runner_infos():
        if info.id == "playwright":
            continue
        if info.available:
            action = QAction(f"Пакетный запуск ({info.label})…", window)

            def _run_batch(checked: bool = False, runner_id: str = info.id) -> None:
                window._run_batch_with_runner(runner_id)

            action.triggered.connect(_run_batch)
            window._plugins_menu.addAction(action)
            window._plugins_menu_actions.append(action)
        elif not info.installed:
            action = QAction(f"Установить {info.label}…", window)

            def _install(checked: bool = False, plugin_id: str = info.id) -> None:
                window._install_runner_addon(plugin_id)

            action.triggered.connect(_install)
            window._plugins_menu.addAction(action)
            window._plugins_menu_actions.append(action)

    host = PluginsMenuHost(window)
    registry.contribute_menus(host)

    if not window._plugins_menu_actions:
        placeholder = QAction("Нет установленных плагинов", window)
        placeholder.setEnabled(False)
        window._plugins_menu.addAction(placeholder)
        window._plugins_menu_actions.append(placeholder)
