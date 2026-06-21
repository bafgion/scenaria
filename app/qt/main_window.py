"""Main window — VS Code–like layout."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QTimer, QUrl
from PySide6.QtGui import QAction, QDesktopServices, QDragEnterEvent, QDropEvent, QKeySequence, QShortcut
from PySide6.QtWidgets import QFileDialog, QHBoxLayout, QMainWindow, QMessageBox, QVBoxLayout, QWidget

from app.feature_store import get_root, resolve_project_root
from app.plugins.installer import PluginInstallError, install_from_zip, install_plugin
from app.plugins.registry import get_registry
from app.progress_state import ProgressState
from app.qt.plugin_host import PluginsMenuHost
from app.qt.drag_drop import classify_drop_paths, paths_from_drop_urls
from app.mvc.controllers.app_controller import AppController
from app.mvc.controllers.catalog_controller import CatalogController
from app.http_auth import apply_url_credentials_to_settings, host_from_url, strip_url_credentials
from app.qt.dialogs import BTN_OK, alert, confirm, prompt_text
from app.qt.widgets.http_auth_dialog import HttpAuthDialog
from app.qt.widgets.browser_session_dialog import BrowserSessionDialog
from app.qt.sync_prompts import install_prompt_service
from app.qt.file_dialogs import FEATURE_FILTER, pick_open_file
from app.qt.widgets.browser_overlay import BrowserOverlayPanel
from app.qt.widgets.activity_bar import ActivityBar
from app.qt.widgets.bottom_panel import BottomPanel
from app.qt.widgets.editor_workspace import EditorWorkspace
from app.qt.widgets.hotkeys_dialog import HotkeysDialog
from app.qt.widgets.ide_status_bar import IdeStatusBar
from app.qt.widgets.sidebar import Sidebar
from app.qt.widgets.zone_divider import zone_divider
from app.qt.widgets.ide_splitter import IdeSplitter, HIT_SIZE
from app.qt.worker_bridge import WorkerBridge
from app.recent import recent_features, recent_projects, remember_feature, remember_project
from app.release_info import github_repo
from app.scenario_hints import gherkin_template_text
from app.qt.branding import about_text, brand_mark_pixmap
from app.brand import BRAND_NAME
from app.qt.update_ui import (
    UpdateCheckRunner,
    UpdateDownloadRunner,
    current_version_label,
    updates_supported,
)
from app.settings import load_settings, save_settings


class MainWindow(QMainWindow):
    def __init__(self, controller: AppController) -> None:
        super().__init__()
        self._controller = controller
        self.setWindowTitle(BRAND_NAME)
        self.resize(1200, 760)
        self.setMinimumSize(900, 560)

        self._bridge = WorkerBridge()
        install_prompt_service(self)
        controller.recording.set_parent_widget(self)
        controller.scenario_controller.set_parent_widget(self)
        controller.recording.attach_bridge(self._bridge)
        self._bridge.start()

        self._catalog_controller = CatalogController(controller.catalog, parent_widget=self)
        controller.attach_catalog_ui(self._catalog_controller)

        root = QWidget()
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        body_splitter = IdeSplitter(Qt.Orientation.Vertical)
        body_splitter.setProperty("role", "main-splitter")

        top = QWidget()
        top_row = QHBoxLayout(top)
        top_row.setContentsMargins(0, 0, 0, 0)
        top_row.setSpacing(0)

        self.activity_bar = ActivityBar(top)
        self.sidebar = Sidebar(controller.catalog, self._catalog_controller, top)
        self.workspace = EditorWorkspace(controller, top)

        self._side_splitter = IdeSplitter(Qt.Orientation.Horizontal)
        self._side_splitter.setProperty("role", "side-splitter")
        self._side_splitter.setChildrenCollapsible(False)
        self._side_splitter.addWidget(self.sidebar)
        self._side_splitter.addWidget(self.workspace)
        self._side_splitter.setStretchFactor(0, 0)
        self._side_splitter.setStretchFactor(1, 1)
        self._side_splitter.setSizes([260, 740])
        self._side_splitter.splitterMoved.connect(self._on_side_splitter_moved)

        top_row.addWidget(self.activity_bar)
        top_row.addWidget(zone_divider(top))
        top_row.addWidget(self._side_splitter, stretch=1)
        body_splitter.addWidget(top)

        self.bottom_panel = BottomPanel()
        self.bottom_panel.setMinimumHeight(0)
        body_splitter.addWidget(self.bottom_panel)
        body_splitter.setCollapsible(0, False)
        body_splitter.setCollapsible(1, True)
        body_splitter.setStretchFactor(0, 1)
        body_splitter.setHandleWidth(0)
        body_splitter.setSizes([560, 0])
        self._panel_splitter = body_splitter
        self._panel_visible = False
        self._sidebar_width = 260

        root_layout.addWidget(body_splitter)

        self.status_bar = IdeStatusBar(root)
        self.status_bar.panel_clicked.connect(lambda: self._show_bottom_panel("log"))
        self.status_bar.project_clicked.connect(self._open_project)
        self.status_bar.runner_clicked.connect(self._pick_default_runner)
        self.status_bar.progress_cancelled.connect(self._on_progress_cancelled)
        root_layout.addWidget(self.status_bar)

        self.setCentralWidget(root)

        self._browser_overlay = BrowserOverlayPanel()
        self._browser_overlay.hide()

        self._build_menus()
        self._wire_signals()
        self._bind_hotkeys()
        self._apply_toolbar_compact(bool(load_settings().get("toolbar_compact")))
        self.setAcceptDrops(True)
        self._start_autosave_timer()
        self._start_browser_watch_timer()
        self._sync_menu_states()

        controller.initialize()
        QTimer.singleShot(0, self._on_startup)

    def _on_startup(self) -> None:
        self._refresh_welcome_recents()
        self._apply_toolbar_compact(bool(load_settings().get("toolbar_compact")))
        root = resolve_project_root()
        if root is not None:
            if self._controller.catalog.features_root != root:
                self._controller.catalog.set_features_root(root)
            self.status_bar.set_message(str(root))
            self.workspace.restore_session_tab()
            self.workspace.ensure_welcome_tab(activate=not self.workspace.has_editor_tabs())
        else:
            self.workspace.ensure_welcome_tab(activate=True)
            self.status_bar.set_message("Проект → Открыть проект…", "info")
        self._update_run_selection_menu()
        self._update_window_title()
        if updates_supported():
            self._maybe_check_updates_on_startup()

    def _refresh_welcome_recents(self) -> None:
        self.workspace.welcome_panel.refresh_recents(recent_features(), recent_projects())

    def _wire_signals(self) -> None:
        rec = self._controller.recording

        rec.browser_raise.connect(self._raise_browser_window)
        rec.status.connect(self._on_status)
        rec.log.connect(self.bottom_panel.log_panel.append)
        rec.switch_tab.connect(self._on_switch_tab)
        rec.play_step.connect(self._on_play_step)
        rec.focus_failed_step.connect(self._on_focus_failed)
        rec.play_results.connect(self._on_play_results)
        rec.batch_results.connect(self._on_batch_results)
        rec.batch_partial.connect(self._on_batch_partial_results)
        rec.progress.connect(self._on_progress)
        rec.validation_results.connect(self._on_validation_results)
        rec.save_prompt.connect(self._on_save_prompt)
        rec.picker_done.connect(self._on_picker_done)

        self._controller.scenario.status_message.connect(self._on_status)
        self._controller.scenario.status_message.connect(
            lambda text, tone: self.bottom_panel.log_panel.append(text, tone)
        )
        self._controller.catalog.root_changed.connect(self._on_project_changed)
        self._controller.catalog.feature_selected.connect(self._on_feature_selected)
        self._controller.catalog.directory_selected.connect(self._on_directory_selected)
        self._catalog_controller.file_open_requested.connect(self._on_catalog_file_open)
        self._controller.session.changed.connect(self._sync_menu_states)
        self._controller.scenario.changed.connect(self._on_scenario_changed)
        self.workspace.gherkin_panel.dirty_changed.connect(lambda _d: self._sync_menu_states())

        self.sidebar.new_btn.clicked.connect(self._new_scenario)
        self.sidebar.run_selected_requested.connect(self._run_selected_features)
        self.sidebar.run_folder_requested.connect(self._run_folder_features)
        self.sidebar.run_history_requested.connect(self._show_run_history)
        self.sidebar.run_file_requested.connect(self._run_single_feature)
        self.sidebar.run_vanessa_file_requested.connect(self._run_vanessa_file)
        self.sidebar.run_vanessa_folder_requested.connect(self._run_vanessa_folder)
        self.sidebar.run_folder_history_requested.connect(self._show_folder_run_history)
        self._controller.catalog.run_selection_changed.connect(self._update_run_selection_menu)
        self.workspace.welcome_panel.open_project.connect(self._open_project)
        self.workspace.welcome_panel.create_feature.connect(self._new_scenario)
        self.workspace.welcome_panel.open_feature.connect(self._open_feature_file)
        self.workspace.welcome_panel.open_recent_feature.connect(self._open_recent_feature)
        self.workspace.welcome_panel.open_recent_project.connect(self._open_recent_project)
        self.workspace.welcome_panel.quick_start.connect(self._quick_start)
        self.workspace.welcome_panel.insert_template.connect(self._new_scenario_with_template)
        self.workspace.welcome_activated.connect(self._refresh_welcome_recents)
        self.workspace.welcome_activated.connect(self._sync_menu_states)
        self.workspace.empty_panel.show_start.connect(
            lambda: self.workspace.ensure_welcome_tab(activate=True)
        )
        self.workspace.empty_panel.open_project.connect(self._open_project)
        self.workspace.empty_panel.create_feature.connect(self._new_scenario)
        self.workspace.empty_panel.open_feature.connect(self._open_feature_file)
        self.workspace.state_changed.connect(self.status_bar.set_session_state)

        ws = self.workspace
        bar = ws.editor_action_bar
        bar.next_step_clicked.connect(self._on_workflow_next_step)
        bar.url_changed.connect(self._set_start_url)
        bar.fetch_url_from_tab_requested.connect(rec.fetch_url_from_tab)
        ws.recording_modes.filter_toggled.connect(self._on_filter_toggled)
        ws.recording_modes.nav_only_toggled.connect(self._on_nav_only_toggled)
        ws.recording_modes.headless_toggled.connect(self._on_headless_toggled)
        ws.recording_modes.saved_session_toggled.connect(self._on_saved_session_toggled)
        ws.recording_modes.hover_record_toggled.connect(self._on_hover_record_toggled)
        ws.post_record_banner.apply_and_test_clicked.connect(self._post_record_apply_and_test)
        ws.post_record_banner.save_clicked.connect(self._post_record_save)
        ws.post_record_banner.fix_hover_clicked.connect(self._post_record_fix_hover)
        ws.post_record_banner.hint_fix_requested.connect(self._post_record_hint_fix)
        ws.post_record_banner.hint_show_step_requested.connect(self._post_record_hint_show_step)
        ws.post_record_banner.dismiss_clicked.connect(ws.hide_post_record)

        self.activity_bar.explorer_toggled.connect(self._toggle_explorer)
        self.activity_bar.panel_toggled.connect(self._toggle_bottom_panel)

        tb = self.workspace.quick_toolbar
        rec = self._controller.recording
        tb.save_clicked.connect(self._save_current)
        tb.browser_clicked.connect(lambda: rec.open_browser(self._start_url()))
        tb.focus_browser_clicked.connect(rec.focus_browser)
        tb.record_clicked.connect(lambda: rec.start_recording(self._start_url()))
        tb.continue_record_clicked.connect(self._continue_recording)
        tb.quick_record_clicked.connect(lambda: rec.quick_record(self._start_url()))
        tb.stop_clicked.connect(self._stop_active_run)
        tb.pause_clicked.connect(rec.toggle_pause)
        tb.play_clicked.connect(self._play_with_apply)
        tb.validate_clicked.connect(self._validate_with_apply)
        tb.picker_clicked.connect(rec.pick_selector)
        tb.check_clicked.connect(self.workspace.gherkin_panel._validate)
        tb.url_clicked.connect(self._edit_start_url)
        tb.undo_step_clicked.connect(rec.undo_last_step)
        tb.log_clicked.connect(lambda: self._show_bottom_panel("log"))
        tb.results_clicked.connect(lambda: self._show_bottom_panel("results"))

        overlay = self._browser_overlay
        overlay.record_clicked.connect(lambda: rec.start_recording(self._start_url()))
        overlay.stop_clicked.connect(self._stop_active_run)
        overlay.pause_clicked.connect(rec.toggle_pause)
        overlay.picker_clicked.connect(rec.pick_selector)
        overlay.focus_browser_clicked.connect(rec.focus_browser)

        self.bottom_panel.validate_panel.step_focus_requested.connect(self._on_validate_step_focus)
        self.bottom_panel.results_panel.set_jump_handler(
            lambda: self.workspace.focus_failed_step(self._controller.session.last_failed_step_index or 0)
        )
        self.bottom_panel.results_panel.set_history_handler(self._show_run_history)
        self.bottom_panel.results_panel.set_rerun_failed_handler(self._rerun_vanessa_failed)
        self.bottom_panel.results_panel.set_open_allure_handler(self._open_allure_results)
        self.bottom_panel.error_panel.set_handlers(
            on_jump=lambda: self.workspace.focus_failed_step(
                self._controller.session.last_failed_step_index or 0
            ),
            on_retry=self._play_with_apply,
        )

    def _on_side_splitter_moved(self, _pos: int, _index: int) -> None:
        sizes = self._side_splitter.sizes()
        if sizes and sizes[0] > 0:
            self._sidebar_width = sizes[0]

    def _toggle_explorer(self, visible: bool) -> None:
        self.sidebar.setVisible(visible)
        splitter = self._side_splitter
        sizes = splitter.sizes()
        total = sum(sizes) or max(splitter.width(), 600)
        if visible:
            splitter.setHandleWidth(HIT_SIZE)
            sidebar_w = self._sidebar_width if self._sidebar_width > 0 else 260
            splitter.setSizes([sidebar_w, max(1, total - sidebar_w)])
        else:
            if sizes and sizes[0] > 0:
                self._sidebar_width = sizes[0]
            splitter.setHandleWidth(0)
            splitter.setSizes([0, total])

    def _toggle_bottom_panel(self, visible: bool) -> None:
        self._panel_visible = visible
        splitter = self._panel_splitter
        sizes = splitter.sizes()
        total = sum(sizes) or max(splitter.height(), 600)
        if visible:
            splitter.setHandleWidth(HIT_SIZE)
            panel_h = max(140, int(total * 0.35))
            splitter.setSizes([max(1, total - panel_h), panel_h])
        else:
            splitter.setHandleWidth(0)
            splitter.setSizes([total, 0])
        self.activity_bar.set_panel_checked(visible)

    def _show_bottom_panel(self, page: str) -> None:
        self.bottom_panel.show_page(page)
        self._toggle_bottom_panel(True)

    def _on_feature_selected(self, path: object) -> None:
        from pathlib import Path

        if not isinstance(path, Path):
            return
        resolved = path.resolve()
        current = self.workspace.current_tab()
        if current is not None and current.path is not None and current.path.resolve() == resolved:
            return
        self.workspace.open_file(resolved, reload_if_clean=True)

    def _on_catalog_file_open(self, path: object) -> None:
        from pathlib import Path

        if isinstance(path, Path) and self.workspace.open_file(path, reload_if_clean=True):
            self._controller.catalog.select_feature(path)

    def _on_directory_selected(self, path: object) -> None:
        from pathlib import Path

        if isinstance(path, Path):
            self.status_bar.set_message(f"Папка: {path.name}", "info")

    def _on_project_changed(self, root: object) -> None:
        if root is None:
            self.status_bar.set_message("Проект не открыт", "info")
            if not self.workspace.has_editor_tabs():
                self.workspace.ensure_welcome_tab(activate=True)
        else:
            self.status_bar.set_message(str(root))
        self._refresh_plugins_menu()
        self._sync_menu_states()

    def _require_project(self) -> bool:
        if get_root() is not None:
            return True
        alert(self, BRAND_NAME, "Сначала откройте папку проекта.")
        self._open_project()
        return get_root() is not None

    def _open_project(self) -> None:
        if self._catalog_controller.open_project():
            root = get_root()
            if root is not None:
                remember_project(root)
                self._refresh_welcome_recents()
                self.status_bar.set_message(str(root))
            if not self.workspace.has_editor_tabs():
                self.workspace.ensure_welcome_tab(activate=True)

    def _new_scenario(self) -> None:
        self.workspace.open_untitled()

    def _new_scenario_with_template(self) -> None:
        text = gherkin_template_text(url=self._start_url())
        self.workspace.open_untitled(initial_text=text)

    def _save_current(self) -> None:
        if not self.workspace.has_editor_tabs():
            return
        tab = self.workspace.current_tab()
        if tab is None or tab.is_welcome:
            return
        if not self.workspace.apply_before_action():
            return
        tab = self.workspace.current_tab()
        text = self.workspace.gherkin_panel.get_text()
        ok, saved_text = self._controller.scenario_controller.save_current_scenario(
            editor_text=text,
            target_path=tab.path if tab is not None else None,
        )
        if not ok:
            return
        path = self._controller.scenario.feature_path
        if path is None:
            return
        self.workspace.on_document_saved(path)
        remember_feature(path)
        remember_project(path.parent.resolve())
        self._refresh_welcome_recents()
        self.workspace.steps_strip.set_steps(self._controller.scenario.steps)
        root = get_root()
        if root is not None and root in path.resolve().parents:
            self._controller.catalog.select_feature(path.resolve())
            self._controller.catalog.refresh_tree()
        self._sync_menu_states()

    def _open_feature_file(self) -> None:
        path = pick_open_file(
            self,
            title="Открыть feature файл",
            filter_spec=FEATURE_FILTER,
            initial_dir=get_root(),
        )
        if path is None:
            return
        root = get_root()
        if root is not None and root in path.parents:
            self._controller.catalog.select_feature(path)
            self.workspace.open_file(path, reload_if_clean=True)
        else:
            self.workspace.open_file(path)
        remember_feature(path)
        self._refresh_welcome_recents()

    def _open_recent_feature(self, path: object) -> None:
        from pathlib import Path

        if isinstance(path, Path):
            root = get_root()
            resolved = path.resolve()
            if root is not None and root in resolved.parents:
                self._controller.catalog.select_feature(resolved)
            self.workspace.open_file(resolved, reload_if_clean=True)
            remember_feature(resolved)
            self._refresh_welcome_recents()

    def _open_recent_project(self, path: object) -> None:
        from pathlib import Path

        if isinstance(path, Path):
            self._controller.catalog.set_features_root(path)
            remember_project(path)
            self._refresh_welcome_recents()
            self.status_bar.set_message(str(path.resolve()))
            self.workspace.ensure_welcome_tab(activate=not self.workspace.has_editor_tabs())

    def _quick_start(self, url: str) -> None:
        if url and not url.startswith("http"):
            alert(self, BRAND_NAME, "Укажите корректный URL (https://…)")
            return
        if url:
            self._controller.scenario.set_start_url(url)
        if not self.workspace.has_editor_tabs():
            self.workspace.open_untitled(initial_text=gherkin_template_text(url=url or self._start_url()))
        else:
            self.workspace.show_editor()
        rec = self._controller.recording
        rec.quick_record(url or self._start_url())

    def _delete_selected_feature(self) -> None:
        path = self._controller.scenario.feature_path
        if self._controller.scenario_controller.delete_selected_feature():
            if path is not None:
                self.workspace.close_tabs_for_path(path, force=True)

    def _build_menus(self) -> None:
        bar = self.menuBar()
        sc = self._controller.scenario_controller
        rec = self._controller.recording

        project_menu = bar.addMenu("Проект")
        project_menu.addAction("Открыть проект…", self._open_project)
        project_menu.addSeparator()
        quit_action = QAction("Выход", self)
        quit_action.setShortcut(QKeySequence.StandardKey.Quit)
        quit_action.triggered.connect(self.close)
        project_menu.addAction(quit_action)

        scenario_menu = bar.addMenu("Сценарий")
        self._scenario_menu = scenario_menu
        self._act_new = QAction("Новый", self)
        self._act_new.setShortcut(QKeySequence.StandardKey.New)
        self._act_new.triggered.connect(self._new_scenario)
        scenario_menu.addAction(self._act_new)
        self._act_open_file = QAction("Открыть…", self)
        self._act_open_file.setShortcut(QKeySequence.StandardKey.Open)
        self._act_open_file.triggered.connect(self._open_feature_file)
        scenario_menu.addAction(self._act_open_file)
        self._act_save = QAction("Сохранить", self)
        self._act_save.setShortcut(QKeySequence.StandardKey.Save)
        self._act_save.triggered.connect(self._save_current)
        scenario_menu.addAction(self._act_save)
        scenario_menu.addAction("Дублировать", sc.duplicate_selected_feature)
        scenario_menu.addAction("Удалить", self._delete_selected_feature)
        scenario_menu.addSeparator()
        scenario_menu.addAction("Экспорт .feature…", self._export_with_apply(sc.export_feature_file))
        scenario_menu.addAction("Экспорт Playwright (TypeScript)…", self._export_with_apply(sc.export_playwright_file))
        scenario_menu.addAction(
            "Экспорт Playwright (Python)…",
            self._export_with_apply(lambda: sc.export_playwright_file(python=True)),
        )
        scenario_menu.addAction("Экспорт ZIP…", self._export_with_apply(sc.export_zip_file))
        scenario_menu.addAction("Экспорт JSON…", self._export_with_apply(sc.export_json_file))
        scenario_menu.addAction("Импорт…", sc.import_feature_file)
        scenario_menu.addAction("Импорт JSON…", sc.import_json_file)
        scenario_menu.addSeparator()
        find_action = scenario_menu.addAction("Найти и заменить…", self._open_find_replace)
        find_action.setShortcut(QKeySequence("Ctrl+H"))
        scenario_menu.addAction("Замена по проекту…", self._open_project_replace)
        refactor_menu = scenario_menu.addMenu("Рефакторинг")
        refactor_menu.addAction("Обновить стартовый URL…", self._refactor_update_start_urls)
        refactor_menu.addAction("Нормализовать отступы шагов", self._refactor_normalize_indents)
        refactor_menu.addAction("Удалить пустые строки между шагами", self._refactor_collapse_blank_lines)
        palette_action = scenario_menu.addAction("Палитра сниппетов…", self._open_snippet_palette)
        palette_action.setShortcut(QKeySequence("Ctrl+Shift+Space"))
        scenario_menu.addSeparator()
        scenario_menu.addAction("Обновить сценарий", self.workspace.gherkin_panel._apply).setShortcut(
            QKeySequence("Ctrl+Shift+S")
        )
        scenario_menu.addAction("Проверить текст сценария", self.workspace.gherkin_panel._validate)
        scenario_menu.addSeparator()
        scenario_menu.addAction(
            "Наведение для меню…",
            self.workspace.gherkin_panel.insert_hover_step,
        )
        scenario_menu.addAction(
            "Починить клик с hover-меню…",
            self.workspace.gherkin_panel.fix_menu_click_at_cursor,
        )
        scenario_menu.addSeparator()
        scenario_menu.addAction("Теги сценария…", self._edit_scenario_tags)

        record_test_menu = bar.addMenu("Запись и тест")
        self._record_test_menu = record_test_menu
        self._act_browser = QAction("Браузер", self)
        self._act_browser.setShortcut(QKeySequence("Ctrl+B"))
        self._act_browser.triggered.connect(lambda: rec.open_browser(self._start_url()))
        record_test_menu.addAction(self._act_browser)
        record_test_menu.addAction("Закрыть браузер", rec.close_browser)
        record_test_menu.addSeparator()
        record_test_menu.addAction("Стартовый URL…", self._edit_start_url)
        record_test_menu.addAction("HTTP-авторизация для сайтов…", self._edit_http_auth)
        record_test_menu.addAction("Сессии браузера…", self._edit_browser_sessions)
        record_test_menu.addAction("URL из вкладки", rec.fetch_url_from_tab)
        record_test_menu.addSeparator()
        self._act_record = QAction("Запись", self)
        self._act_record.setShortcut(QKeySequence("Ctrl+R"))
        self._act_record.triggered.connect(lambda: rec.start_recording(self._start_url()))
        record_test_menu.addAction(self._act_record)
        self._act_stop = QAction("Стоп", self)
        self._act_stop.triggered.connect(self._stop_active_run)
        record_test_menu.addAction(self._act_stop)
        record_test_menu.addAction("Пауза", rec.toggle_pause)
        record_test_menu.addAction("Отменить шаг записи", rec.undo_last_step)
        record_test_menu.addSeparator()
        self._act_play = QAction("Запустить", self)
        self._act_play.setShortcut(QKeySequence("Ctrl+Return"))
        self._act_play.triggered.connect(self._play_with_apply)
        record_test_menu.addAction(self._act_play)
        record_test_menu.addAction("Проверить элементы", self._validate_with_apply)
        self._act_run_selected = QAction("Запустить выбранные", self)
        self._act_run_selected.triggered.connect(self._run_selected_features)
        record_test_menu.addAction(self._act_run_selected)
        record_test_menu.addAction("Запустить все сценарии проекта", rec.run_project_suite)
        record_test_menu.addAction("Запустить сценарии с тегом…", self._run_project_tag)
        record_test_menu.addAction("Указать элемент…", rec.pick_selector)
        record_test_menu.addAction("Быстрая запись", lambda: rec.quick_record(self._start_url()))
        record_test_menu.addSeparator()
        self._act_filter = QAction("Только важные", self)
        self._act_filter.setCheckable(True)
        self._act_filter.setChecked(self._controller.session.filter_recording)
        self._act_filter.toggled.connect(self._on_filter_toggled)
        record_test_menu.addAction(self._act_filter)
        self._act_nav_only = QAction("Только ссылки", self)
        self._act_nav_only.setCheckable(True)
        self._act_nav_only.setChecked(self._controller.session.nav_only_recording)
        self._act_nav_only.toggled.connect(self._on_nav_only_toggled)
        record_test_menu.addAction(self._act_nav_only)
        self._act_headless = QAction("Без окна браузера", self)
        self._act_headless.setCheckable(True)
        self._act_headless.setChecked(self._controller.session.headless)
        self._act_headless.toggled.connect(self._on_headless_toggled)
        record_test_menu.addAction(self._act_headless)
        self._act_saved_session = QAction("Использовать сохранённую сессию", self)
        self._act_saved_session.setCheckable(True)
        self._act_saved_session.setChecked(bool(load_settings().get("use_saved_browser_session", True)))
        self._act_saved_session.toggled.connect(self._on_saved_session_toggled)
        record_test_menu.addAction(self._act_saved_session)
        record_test_menu.addSeparator()
        record_test_menu.addAction("Запись и селекторы…", self._open_recording_settings)
        record_test_menu.addAction("Открыть последний отчёт", self._open_latest_report)

        self._plugins_menu = bar.addMenu("Плагины")
        self._plugins_menu_actions: list[QAction] = []
        self._plugins_menu_separator: QAction | None = None
        self._refresh_plugins_menu()

        view_menu = bar.addMenu("Вид")
        view_menu.addAction("Старт", lambda: self.workspace.ensure_welcome_tab(activate=True))
        view_menu.addAction("Сценарии", lambda: self.activity_bar.explorer_btn.setChecked(True))
        view_menu.addAction("Журнал", lambda: self._show_bottom_panel("log"))
        view_menu.addAction("Результаты", lambda: self._show_bottom_panel("results"))
        view_menu.addAction("Проверка элементов", lambda: self._show_bottom_panel("validate"))
        view_menu.addAction("Ошибка", lambda: self._show_bottom_panel("error"))
        view_menu.addSeparator()
        view_menu.addAction("Сбросить макет окон", self._reset_layout)
        self._act_toolbar_compact = QAction("Компактная панель инструментов", self)
        self._act_toolbar_compact.setCheckable(True)
        self._act_toolbar_compact.setChecked(bool(load_settings().get("toolbar_compact")))
        self._act_toolbar_compact.toggled.connect(self._on_toolbar_compact_toggled)
        view_menu.addAction(self._act_toolbar_compact)

        help_menu = bar.addMenu("Справка")
        help_menu.addAction("Шаги…", self._open_step_help).setShortcut("F1")
        help_menu.addAction("Горячие клавиши", self._show_hotkeys).setShortcut("Shift+F1")
        if updates_supported():
            help_menu.addAction("Проверить обновления…", self._check_updates_manual)
        help_menu.addAction("О программе", self._show_about)

    def _refresh_plugins_menu(self) -> None:
        for action in self._plugins_menu_actions:
            self._plugins_menu.removeAction(action)
        self._plugins_menu_actions.clear()
        if self._plugins_menu_separator is not None:
            self._plugins_menu.removeAction(self._plugins_menu_separator)
            self._plugins_menu_separator = None

        registry = get_registry()
        registry.reload(project_root=get_root())
        for info in registry.runner_infos():
            if info.id == "playwright":
                continue
            if info.available:
                action = QAction(f"Пакетный запуск ({info.label})…", self)

                def _run_batch(checked: bool = False, runner_id: str = info.id) -> None:
                    self._run_batch_with_runner(runner_id)

                action.triggered.connect(_run_batch)
                self._plugins_menu.addAction(action)
                self._plugins_menu_actions.append(action)
            elif not info.installed:
                action = QAction(f"Установить {info.label}…", self)

                def _install(checked: bool = False, plugin_id: str = info.id) -> None:
                    self._install_runner_addon(plugin_id)

                action.triggered.connect(_install)
                self._plugins_menu.addAction(action)
                self._plugins_menu_actions.append(action)

        host = PluginsMenuHost(self)
        registry.contribute_menus(host)

        if not self._plugins_menu_actions:
            placeholder = QAction("Нет установленных плагинов", self)
            placeholder.setEnabled(False)
            self._plugins_menu.addAction(placeholder)
            self._plugins_menu_actions.append(placeholder)

    def _refresh_runner_menu(self) -> None:
        """Backward-compatible alias."""
        self._refresh_plugins_menu()

    def _is_plugin_installed(self, plugin_id: str) -> bool:
        return get_registry().get_runner(plugin_id) is not None

    def _run_batch_with_runner(self, runner_id: str) -> None:
        root = get_root()
        if root is None:
            alert(self, BRAND_NAME, "Сначала откройте проект с .feature файлами")
            return
        if not self._prepare_batch_run():
            return
        self._controller.recording.run_project_suite_with_runner(runner_id)

    def _install_runner_addon(self, plugin_id: str) -> bool:
        if self._is_plugin_installed(plugin_id):
            return True
        if confirm(self, BRAND_NAME, f"Скачать add-on «{plugin_id}» с GitHub Releases?"):
            try:
                install_plugin(plugin_id)
            except PluginInstallError as exc:
                if not confirm(self, BRAND_NAME, f"{exc}\n\nУказать локальный zip?"):
                    return False
                path, _ = QFileDialog.getOpenFileName(
                    self,
                    "Выберите zip add-on",
                    "",
                    "Zip (*.zip)",
                )
                if not path:
                    return False
                try:
                    install_from_zip(Path(path), plugin_id=plugin_id)
                except PluginInstallError as exc2:
                    alert(self, BRAND_NAME, str(exc2))
                    return False
            self._refresh_plugins_menu()
            alert(self, BRAND_NAME, f"Add-on «{plugin_id}» установлен.")
            return self._is_plugin_installed(plugin_id)

        path, _ = QFileDialog.getOpenFileName(
            self,
            "Выберите zip add-on",
            "",
            "Zip (*.zip)",
        )
        if not path:
            return False
        try:
            install_from_zip(Path(path), plugin_id=plugin_id)
        except PluginInstallError as exc:
            alert(self, BRAND_NAME, str(exc))
            return False
        self._refresh_plugins_menu()
        alert(self, BRAND_NAME, f"Add-on «{plugin_id}» установлен.")
        return self._is_plugin_installed(plugin_id)

    def _start_url(self) -> str:
        return self._controller.scenario.start_url.strip()

    def _apply_start_url(self, url: str) -> bool:
        url = url.strip()
        if url and not url.startswith("http"):
            return False
        settings = load_settings()
        url, settings = apply_url_credentials_to_settings(url, settings)
        save_settings(settings)
        url = strip_url_credentials(url)
        self._controller.scenario.set_start_url(url)
        self.workspace.editor_action_bar.set_url(url)
        return True

    def _edit_start_url(self) -> None:
        current = self._start_url()
        value = prompt_text(
            self,
            "Стартовый URL",
            "URL для браузера и записи:\n(можно указать https://логин:пароль@сайт — пароль сохранится локально)",
            initial=current,
        )
        if value is None:
            return
        if not self._apply_start_url(value):
            alert(self, BRAND_NAME, "Укажите корректный URL (https://…)")
            return
        url = self._start_url()
        if url:
            self.status_bar.set_message(f"Стартовый URL: {url}", "success")
        else:
            self.status_bar.set_message("Стартовый URL не задан", "info")

    def _edit_http_auth(self) -> None:
        dialog = HttpAuthDialog(self, suggested_host=host_from_url(self._start_url()))
        dialog.exec()

    def _edit_browser_sessions(self) -> None:
        rec = self._controller.recording
        dialog = BrowserSessionDialog(self, suggested_url=self._start_url())

        if self._controller.session.browser_open:
            def save_current(label: str) -> None:
                rec.save_browser_session(
                    label,
                    on_saved=dialog.on_session_saved,
                    on_error=lambda exc: alert(self, BRAND_NAME, f"Не удалось сохранить сессию:\n{exc}"),
                )

            dialog._save_callback = save_current
            dialog._update_save_enabled()
        dialog.exec()

    def _edit_scenario_tags(self) -> None:
        current = ", ".join(self._controller.scenario.tags)
        value = prompt_text(
            self,
            "Теги сценария",
            "Теги через запятую (без @):\nнапример: smoke, regression",
            initial=current,
        )
        if value is None:
            return
        tags = [part.strip().lstrip("@") for part in value.replace(";", ",").split(",") if part.strip()]
        self._controller.scenario_controller.set_tags(tags)
        self.workspace.gherkin_panel.sync_from_model(force=True)
        self.workspace._sync_steps_from_controller()

    def _set_start_url(self, url: str) -> None:
        if not self._apply_start_url(url):
            alert(self, BRAND_NAME, "Укажите корректный URL (https://…)")
            self.workspace.editor_action_bar.set_url(self._start_url())
            return

    def _on_workflow_next_step(self, action: str) -> None:
        rec = self._controller.recording
        if action == "browser":
            rec.open_browser(self._start_url())
        elif action == "record":
            rec.start_recording(self._start_url())
        elif action == "apply":
            self.workspace.gherkin_panel._apply()
        elif action == "save":
            self._save_current()
        elif action == "play":
            self._play_with_apply()

    def _raise_browser_window(self, title_hint: str) -> None:
        from app.browser_focus import activate_browser_window_ui_thread

        activate_browser_window_ui_thread(title_hint)

    def _open_find_replace(self) -> None:
        from app.qt.widgets.find_replace_dialog import open_find_replace_dialog

        open_find_replace_dialog(self, self.workspace.gherkin_panel.editor)

    def _active_editor_text(self) -> tuple[object, str]:
        editor = self.workspace.gherkin_panel.editor
        return editor, editor.toPlainText()

    def _set_active_editor_text(self, editor: object, text: str) -> None:
        editor.setPlainText(text)
        self.workspace.gherkin_panel._auto_apply_timer.stop()
        self.workspace.gherkin_panel._auto_apply_if_valid()

    def _refactor_update_start_urls(self) -> None:
        from PySide6.QtWidgets import QInputDialog

        from app.gherkin_refactor import update_start_urls

        editor, text = self._active_editor_text()
        current = self._start_url().strip()
        new_url, ok = QInputDialog.getText(
            self,
            "Обновить стартовый URL",
            "Новый URL для всех шагов «открыт»:",
            text=current,
        )
        if not ok or not str(new_url).strip():
            return
        updated, count = update_start_urls(text, str(new_url).strip())
        if count <= 0:
            return
        self._set_active_editor_text(editor, updated)

    def _refactor_normalize_indents(self) -> None:
        from app.gherkin_refactor import normalize_step_indents

        editor, text = self._active_editor_text()
        self._set_active_editor_text(editor, normalize_step_indents(text))

    def _refactor_collapse_blank_lines(self) -> None:
        from app.gherkin_refactor import collapse_blank_lines_between_steps

        editor, text = self._active_editor_text()
        self._set_active_editor_text(editor, collapse_blank_lines_between_steps(text))

    def _open_snippet_palette(self) -> None:
        from app.qt.widgets.snippet_palette_dialog import open_snippet_palette

        open_snippet_palette(self, self.workspace.gherkin_panel.editor)

    def _open_step_help(self) -> None:
        from app.qt.widgets.step_help_panel import open_step_help_panel

        editor = self.workspace.gherkin_panel.editor
        open_step_help_panel(self, editor=editor)

    def _open_project_replace(self) -> None:
        from app.feature_store import get_root
        from app.qt.widgets.project_replace_dialog import open_project_replace_dialog

        open_project_replace_dialog(
            self,
            current_path=self._controller.scenario.feature_path,
            open_paths=self.workspace.open_feature_paths(),
            project_root=get_root(),
            dirty_paths=self.workspace.dirty_feature_paths(),
            on_applied=self._on_project_replace_applied,
        )

    def _on_project_replace_applied(self, changed: dict) -> None:
        self.workspace.sync_replaced_files(changed)
        self._controller.catalog.refresh_tree()

    def _show_run_history(self, path: object) -> None:
        from pathlib import Path

        from app.qt.widgets.run_history_dialog import open_run_history_dialog

        if isinstance(path, Path):
            open_run_history_dialog(self, path)

    def _continue_recording(self) -> None:
        from app.qt.widgets.continue_recording_dialog import ask_continue_recording

        step_count = len(self._controller.scenario.steps)
        if step_count == 0:
            return
        prepare = ask_continue_recording(self, step_count=step_count)
        if prepare is None:
            return
        self._controller.recording.continue_recording(
            self._start_url(),
            prepare_browser=prepare,
        )

    def _play_with_apply(self) -> None:
        if not self.workspace.apply_before_action():
            return
        self.workspace.steps_strip.set_steps(self._controller.scenario.steps)
        self._controller.recording.play()

    def _validate_with_apply(self) -> None:
        if not self.workspace.apply_before_action():
            return
        self._controller.recording.validate_current()

    def _stop_active_run(self) -> None:
        rec = self._controller.recording
        session = self._controller.session
        if rec.is_batch_running:
            rec.stop_batch()
        elif session.vanessa_running:
            rec.stop_vanessa()
        elif session.recording:
            rec.stop_recording()
        elif session.playing:
            rec.stop_playback()
        elif session.player_browser:
            rec.close_player_browser()

    def _prepare_batch_run(self) -> bool:
        self.workspace.persist_current_tab()
        if self.workspace.gherkin_panel.has_parse_error:
            if not confirm(
                self,
                BRAND_NAME,
                "В тексте сценария есть ошибки.\n"
                "Пакетный запуск читает файлы с диска — продолжить?",
            ):
                return False
        self.workspace.flush_all_tabs_to_disk()
        return True

    def _run_selected_features(self) -> None:
        paths = self._controller.catalog.run_selection_paths
        if not paths:
            return
        if not self._prepare_batch_run():
            return
        self._controller.recording.run_selected_features(paths)

    def _run_folder_features(self, folder: object) -> None:
        from pathlib import Path

        from app.mvc.models.catalog_model import collect_feature_paths_under

        if not isinstance(folder, Path):
            return
        paths = collect_feature_paths_under(folder)
        if not paths:
            alert(self, BRAND_NAME, "В этой папке нет .feature сценариев")
            return
        if not self._prepare_batch_run():
            return
        self._controller.recording.run_selected_features(paths)

    def _run_single_feature(self, path: object) -> None:
        from pathlib import Path

        if not isinstance(path, Path):
            return
        if not self._prepare_batch_run():
            return
        self._controller.recording.run_selected_features([path])

    def _run_vanessa_file(self, path: object) -> None:
        from pathlib import Path

        if not isinstance(path, Path):
            return
        if not self._is_plugin_installed("vanessa"):
            if not self._install_runner_addon("vanessa"):
                return
        self._run_vanessa_paths([path])

    def _run_vanessa_folder(self, folder: object) -> None:
        from pathlib import Path

        from app.mvc.models.catalog_model import collect_feature_paths_under

        if not isinstance(folder, Path):
            return
        if not self._is_plugin_installed("vanessa"):
            if not self._install_runner_addon("vanessa"):
                return
        paths = collect_feature_paths_under(folder)
        if not paths:
            alert(self, BRAND_NAME, "В этой папке нет .feature сценариев")
            return
        self._run_vanessa_paths(paths)

    def _run_vanessa_paths(self, paths: list[Path]) -> None:
        if not paths:
            return
        if not self._prepare_batch_run():
            return
        if len(paths) == 1:
            label = f"Прогон Vanessa — {paths[0].name}"
        else:
            label = f"Прогон Vanessa ({len(paths)} файлов)"
        self._controller.recording.run_features_with_runner(
            paths,
            runner_id="vanessa",
            label=label,
        )

    def _show_folder_run_history(self, folder: object) -> None:
        from pathlib import Path

        from PySide6.QtWidgets import QInputDialog

        from app.mvc.models.catalog_model import collect_feature_paths_under
        from app.run_status_store import get_run_history

        if not isinstance(folder, Path):
            return
        paths = [item for item in collect_feature_paths_under(folder) if get_run_history(item)]
        if not paths:
            alert(self, BRAND_NAME, "В папке нет сохранённой истории прогонов.")
            return
        if len(paths) == 1:
            self._show_run_history(paths[0])
            return
        root = get_root()
        labels = []
        for item in paths:
            if root is not None:
                try:
                    labels.append(str(item.resolve().relative_to(root.resolve())))
                except ValueError:
                    labels.append(item.name)
            else:
                labels.append(item.name)
        choice, ok = QInputDialog.getItem(
            self,
            "История прогонов папки",
            "Выберите сценарий:",
            labels,
            editable=False,
        )
        if not ok or not choice:
            return
        index = labels.index(str(choice))
        self._show_run_history(paths[index])

    def _reset_layout(self) -> None:
        self.activity_bar.explorer_btn.setChecked(True)
        self._toggle_explorer(True)
        self._sidebar_width = 260
        splitter = self._side_splitter
        total = sum(splitter.sizes()) or max(splitter.width(), 1000)
        splitter.setHandleWidth(HIT_SIZE)
        splitter.setSizes([260, max(1, total - 260)])
        self._toggle_bottom_panel(False)
        self.workspace.reset_editor_layout()
        self.status_bar.set_message("Макет окон сброшен", "success")

    def _apply_toolbar_compact(self, enabled: bool) -> None:
        self.workspace.editor_action_bar.set_toolbar_simple_mode(enabled)
        if hasattr(self, "_act_toolbar_compact"):
            blocked = self._act_toolbar_compact.blockSignals(True)
            self._act_toolbar_compact.setChecked(enabled)
            self._act_toolbar_compact.blockSignals(blocked)

    def _on_toolbar_compact_toggled(self, checked: bool) -> None:
        settings = load_settings()
        settings["toolbar_compact"] = checked
        save_settings(settings)
        self._apply_toolbar_compact(checked)

    def _collect_palette_commands(self):
        from app.qt.widgets.command_palette import PaletteCommand, normalize_menu_label, shortcut_text

        commands: list[PaletteCommand] = []
        seen: set[str] = set()

        def walk_menu(menu, prefix: str = "") -> None:
            for action in menu.actions():
                if action.isSeparator():
                    continue
                sub = action.menu()
                if sub is not None:
                    part = normalize_menu_label(action.text())
                    next_prefix = f"{prefix}{part} → " if part else prefix
                    walk_menu(sub, next_prefix)
                    continue
                label = normalize_menu_label(action.text())
                if not label:
                    continue
                full_label = f"{prefix}{label}" if prefix else label
                if full_label in seen:
                    continue
                seen.add(full_label)
                commands.append(
                    PaletteCommand(
                        id=full_label.lower(),
                        label=full_label,
                        shortcut=shortcut_text(action),
                        run=action.trigger,
                    )
                )

        for top in self.menuBar().actions():
            menu = top.menu()
            if menu is not None:
                walk_menu(menu)
        return sorted(commands, key=lambda item: item.label.lower())

    def _open_command_palette(self) -> None:
        from app.qt.widgets.command_palette import open_command_palette

        commands = self._collect_palette_commands()
        settings = load_settings()
        recent = list(settings.get("palette_recent_commands") or [])
        selected = open_command_palette(self, commands, recent_ids=recent)
        if selected is None:
            return
        recent = [selected.id] + [item for item in recent if item != selected.id]
        settings["palette_recent_commands"] = recent[:5]
        save_settings(settings)
        selected.run()

    def _run_project_tag(self) -> None:
        from app.mvc.models.catalog_model import parse_catalog_filter

        _, tag_from_filter = parse_catalog_filter(self._controller.catalog.filter_text)
        initial = tag_from_filter or ""
        value = prompt_text(
            self,
            "Запуск по тегу",
            "Тег (без @), например smoke:",
            initial=initial,
        )
        if value is None:
            return
        tag = value.strip().lstrip("@")
        if not tag:
            alert(self, BRAND_NAME, "Укажите тег")
            return
        if not self._prepare_batch_run():
            return
        self._controller.recording.run_project_tag(tag)

    def _update_run_selection_menu(self) -> None:
        count = self._controller.catalog.run_selection_count
        self._act_run_selected.setText(
            f"Запустить выбранные ({count})" if count else "Запустить выбранные"
        )
        self._act_run_selected.setEnabled(count > 0)

    def _export_with_apply(self, action):
        def _run() -> None:
            if not self.workspace.apply_before_action():
                return
            action()

        return _run

    def _on_scenario_changed(self) -> None:
        if self._controller.session.recording:
            self.workspace.gherkin_panel.sync_from_model(force=True)
        self._sync_menu_states()

    def _sync_menu_states(self) -> None:
        s = self._controller.session
        editor_active = self.workspace.is_editor_tab_active()
        has_steps = editor_active and bool(self._controller.scenario.steps)
        pending = s.pending
        unapplied = self.workspace.gherkin_panel.has_parse_error if editor_active else False
        batch_running = self._controller.recording.is_batch_running or s.vanessa_running
        browser_active = s.browser_session_active()
        for action in (self._act_save, self._act_browser, self._act_record, self._act_play):
            action.setEnabled(not pending)
        if not pending:
            self._act_browser.setEnabled(
                not browser_active and not s.recording and not batch_running and not s.playing
            )
            self._act_record.setEnabled(
                editor_active
                and s.browser_open
                and not s.recording
                and not s.playing
                and not batch_running
            )
            self._act_play.setEnabled(
                editor_active
                and not s.recording
                and not s.playing
                and has_steps
                and not batch_running
                and not self._controller.recording.player_worker_active
                and not unapplied
            )
            self._act_save.setEnabled(editor_active and not s.recording)
        self._act_stop.setEnabled(
            s.recording
            or s.playing
            or batch_running
            or s.vanessa_running
            or s.player_browser
            or self._controller.recording.is_picking
        )
        self._update_run_selection_menu()
        self._act_run_selected.setEnabled(
            self._controller.catalog.run_selection_count > 0 and not pending and not batch_running
        )
        self.workspace.quick_toolbar.sync_states(
            pending=pending,
            browser_open=browser_active,
            recorder_browser_open=s.browser_open,
            player_browser_open=s.player_browser,
            recording=s.recording,
            playing=s.playing,
            has_steps=has_steps,
            unapplied=unapplied,
            batch_running=batch_running,
            picking=self._controller.recording.is_picking,
            editor_active=editor_active,
        )
        self.workspace.sync_chrome(
            pending=pending,
            browser_open=browser_active,
            recorder_browser_open=s.browser_open,
            recording=s.recording,
            playing=s.playing,
            has_steps=has_steps,
        )
        self._act_filter.setChecked(s.filter_recording)
        self._act_nav_only.setChecked(s.nav_only_recording)
        self._act_headless.setChecked(s.headless)
        self._act_saved_session.setChecked(bool(load_settings().get("use_saved_browser_session", True)))
        self._update_window_title()
        root = get_root()
        scenario = self._controller.scenario
        project = ""
        if not editor_active:
            project = "Старт"
        elif scenario.feature_path:
            project = scenario.feature_path.name
        elif root is not None:
            project = root.name
        self.status_bar.sync(
            browser_open=browser_active,
            recording=s.recording,
            step_count=len(scenario.steps) if editor_active else 0,
            gherkin_unapplied=unapplied,
            project_label=project,
        )
        self._sync_status_runner()
        self._sync_browser_overlay()

    def _resolve_active_runner_id(self) -> str:
        from app.project_config import default_runner

        s = self._controller.session
        rec = self._controller.recording
        if s.vanessa_running:
            return "vanessa"
        if rec.is_batch_running:
            return rec.batch_runner_id
        if s.playing:
            return "playwright"
        return default_runner(get_root())

    def _runner_label(self, runner_id: str) -> str:
        for info in get_registry().runner_infos():
            if info.id == runner_id:
                return info.label
        return runner_id

    def _sync_status_runner(self) -> None:
        root = get_root()
        if root is None:
            self.status_bar.set_runner(None)
            return
        runner_id = self._resolve_active_runner_id()
        label = self._runner_label(runner_id)
        s = self._controller.session
        rec = self._controller.recording
        active = s.vanessa_running or rec.is_batch_running or s.playing
        if active:
            tooltip = f"Сейчас выполняется прогон через {label}"
        elif runner_id == "vanessa":
            tooltip = "Пакетный запуск 1С через Vanessa Automation. Нажмите, чтобы сменить runner."
        else:
            tooltip = "Встроенный прогон Playwright в браузере. Нажмите, чтобы сменить runner."
        self.status_bar.set_runner(f"Runner · {label}", tooltip=tooltip)

    def _pick_default_runner(self) -> None:
        from PySide6.QtWidgets import QMenu

        from app.project_config import default_runner, set_default_runner

        root = get_root()
        if root is None:
            alert(self, BRAND_NAME, "Сначала откройте проект.")
            return
        menu = QMenu(self)
        current = default_runner(root)
        for info in get_registry().runner_infos():
            if info.id != "playwright" and not info.installed:
                continue
            action = menu.addAction(info.label)
            action.setCheckable(True)
            action.setChecked(info.id == current)
            enabled = info.id == "playwright" or info.available
            action.setEnabled(enabled)
            if not enabled:
                action.setToolTip(info.reason or "Runner недоступен")

            def _select(checked: bool = False, runner_id: str = info.id) -> None:
                set_default_runner(root, runner_id)
                self._sync_menu_states()

            action.triggered.connect(_select)
        menu.exec(self.status_bar.mapToGlobal(self.status_bar.rect().bottomRight()))

    def _open_latest_report(self) -> None:
        from app.report_locator import find_latest_report

        hints = self.bottom_panel.results_panel.latest_report_hints()
        target = find_latest_report(hints=hints, project_root=get_root())
        if target is None:
            alert(self, BRAND_NAME, "Отчётов пока нет.\nЗапустите сценарий или пакетный прогон.")
            return
        self._open_report_target(target)

    def _open_report_target(self, target) -> None:
        from PySide6.QtCore import QUrl
        from PySide6.QtGui import QDesktopServices

        if target.kind == "html":
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(target.path.resolve())))
            return
        self._open_allure_results(target.path)

    def _sync_browser_overlay(self) -> None:
        s = self._controller.session
        rec = self._controller.recording
        if not s.browser_session_active():
            self._browser_overlay.hide()
            return
        self._browser_overlay.sync_state(
            visible=s.browser_session_active(),
            recording=s.recording,
            playing=s.playing,
            paused=s.paused,
            recorder_browser=s.browser_open,
            player_browser=s.player_browser,
            picking=rec.is_picking,
        )

    def _on_filter_toggled(self, checked: bool) -> None:
        session = self._controller.session
        session.filter_recording = checked
        if checked:
            self._act_nav_only.setChecked(False)
            session.nav_only_recording = False
        self._controller.recording.apply_recording_modes()
        settings = load_settings()
        settings["filter_recording"] = checked
        if checked:
            settings["nav_only_recording"] = False
        save_settings(settings)
        self._sync_menu_states()

    def _on_nav_only_toggled(self, checked: bool) -> None:
        session = self._controller.session
        session.nav_only_recording = checked
        if checked:
            self._act_filter.setChecked(False)
            session.filter_recording = False
        self._controller.recording.apply_recording_modes()
        settings = load_settings()
        settings["nav_only_recording"] = checked
        if checked:
            settings["filter_recording"] = False
        save_settings(settings)
        self._sync_menu_states()

    def _on_headless_toggled(self, checked: bool) -> None:
        self._controller.session.headless = checked
        self._act_headless.setChecked(checked)
        settings = load_settings()
        settings["headless"] = checked
        save_settings(settings)
        self._sync_menu_states()

    def _on_saved_session_toggled(self, checked: bool) -> None:
        self._act_saved_session.setChecked(checked)
        settings = load_settings()
        settings["use_saved_browser_session"] = checked
        save_settings(settings)
        self.workspace.recording_modes.sync(
            visible=self.workspace.recording_modes.isVisible(),
            filter_recording=self._controller.session.filter_recording,
            nav_only_recording=self._controller.session.nav_only_recording,
            headless=self._controller.session.headless,
            use_saved_session=checked,
            hover_recording=self._controller.session.hover_recording,
        )
        self._sync_menu_states()

    def _on_hover_record_toggled(self, checked: bool) -> None:
        session = self._controller.session
        session.hover_recording = checked
        self._controller.recording.apply_recording_modes()
        settings = load_settings()
        settings["hover_record_enabled"] = checked
        save_settings(settings)
        self._sync_menu_states()

    def _open_recording_settings(self) -> None:
        from app.qt.widgets.recording_settings_dialog import open_recording_settings_dialog

        if open_recording_settings_dialog(self):
            self._controller.recording.apply_recording_modes()
            self.status_bar.set_message("Настройки записи сохранены", "success")
            self._sync_menu_states()

    def _update_window_title(self) -> None:
        title = BRAND_NAME
        s = self._controller.session
        if s.recording:
            title = f"● {title} — Запись"
        elif s.playing:
            title = f"▶ {title} — Тест"
        self.setWindowTitle(title)

    def _post_record_apply_and_test(self) -> None:
        if self.workspace.gherkin_panel.has_parse_error:
            return
        self._controller.recording.play()

    def _post_record_save(self) -> None:
        self._save_current()
        self.workspace.hide_post_record()

    def _post_record_fix_hover(self) -> None:
        from app.scenario_hints import find_suspicious_menu_clicks

        self.workspace.gherkin_panel.sync_from_model(force=True)
        steps = list(self._controller.scenario.steps)
        suspicious = find_suspicious_menu_clicks(steps)
        if not suspicious:
            return
        index = suspicious[0]
        if self._controller.scenario_controller.try_fix_menu_hover(index):
            self.workspace._sync_steps_from_controller(select_row=index + 1)
            self.workspace.hide_post_record()
            self.status_bar.set_message("Шаг разбит: наведение + клик", "success")
            return
        self.workspace.focus_failed_step(index + 1)
        self.workspace.gherkin_panel.fix_menu_click_at_cursor()

    def _post_record_hint_fix(self, hint) -> None:
        from app.scenario_hints import ScenarioHint, collect_all_hints

        if not isinstance(hint, ScenarioHint):
            return
        self.workspace.gherkin_panel.sync_from_model(force=True)
        if self._controller.scenario_controller.apply_scenario_hint(hint):
            row = hint.step_indices[0] + 1 if hint.step_indices else None
            self.workspace._sync_steps_from_controller(select_row=row)
            steps = list(self._controller.scenario.steps)
            self.workspace.post_record_banner.show_recording(len(steps), hints=collect_all_hints(steps))
            self.status_bar.set_message("Подсказка применена", "success")
            return
        self._post_record_hint_show_step(hint.step_indices[0] + 1 if hint.step_indices else 1)

    def _post_record_hint_show_step(self, step_index: int) -> None:
        if step_index < 1:
            return
        self.workspace.focus_failed_step(step_index)
        self.workspace.gherkin_panel.focus_step(step_index)

    def _show_hotkeys(self) -> None:
        HotkeysDialog(self).exec()

    def _start_autosave_timer(self) -> None:
        self._autosave_timer = QTimer(self)
        self._autosave_timer.setInterval(30_000)
        self._autosave_timer.timeout.connect(self._autosave_draft)
        self._autosave_timer.start()

    def _start_browser_watch_timer(self) -> None:
        self._browser_watch_timer = QTimer(self)
        self._browser_watch_timer.setInterval(400)
        self._browser_watch_timer.timeout.connect(self._refresh_browser_chrome)
        self._browser_watch_timer.start()

    def _refresh_browser_chrome(self) -> None:
        self._controller.recording.sync_browser_state()
        self._sync_browser_overlay()

    def _autosave_draft(self) -> None:
        settings = load_settings()
        if not settings.get("autosave_enabled", True):
            return
        if not self.workspace.has_editor_tabs():
            return
        tab = self.workspace.current_tab()
        if tab is None or tab.is_welcome:
            return
        scenario = self._controller.scenario
        if scenario.feature_path is not None:
            return
        editor_text = self.workspace.gherkin_panel.get_text()
        scenario.save_draft_if_needed(enabled=True, editor_text=editor_text)

    def _bind_hotkeys(self) -> None:
        escape = QShortcut(QKeySequence("Escape"), self)
        escape.setContext(Qt.ShortcutContext.ApplicationShortcut)
        escape.activated.connect(self._controller.recording.handle_escape)
        QShortcut(QKeySequence("Ctrl+`"), self, lambda: self.activity_bar.panel_btn.toggle())
        QShortcut(QKeySequence("Shift+F1"), self, self._show_hotkeys)
        palette = QShortcut(QKeySequence("Ctrl+Shift+P"), self)
        palette.setContext(Qt.ShortcutContext.ApplicationShortcut)
        palette.activated.connect(self._open_command_palette)

    def _on_switch_tab(self, name: str) -> None:
        if name == "log":
            self._show_bottom_panel("log")
        elif name == "results":
            self._show_bottom_panel("results")
        elif name in ("editor", "gherkin", "steps"):
            self.workspace.show_editor()

    def _on_status(self, text: str, tone: str) -> None:
        self.status_bar.set_message(text, tone)

    def _on_progress(self, state: object) -> None:
        if state is None or not isinstance(state, ProgressState):
            self.status_bar.set_progress(None)
            return
        self.status_bar.set_progress(state)

    def _on_progress_cancelled(self, task_id: str) -> None:
        if task_id == "batch-run":
            self._controller.recording.stop_batch()

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:  # noqa: N802
        if not event.mimeData().hasUrls():
            return
        urls = [url.toLocalFile() for url in event.mimeData().urls()]
        paths = paths_from_drop_urls(urls)
        if not paths:
            return
        features, directories = classify_drop_paths(paths)
        if not features and not directories:
            return
        event.acceptProposedAction()
        hints: list[str] = []
        if features:
            hints.append(f"{len(features)} .feature")
        if directories:
            hints.append(f"проект «{directories[0].name}»")
        self.status_bar.set_message(f"Отпустите для открытия: {', '.join(hints)}", "info")

    def dragLeaveEvent(self, event) -> None:  # noqa: N802
        self._restore_status_after_drag()
        super().dragLeaveEvent(event)

    def dropEvent(self, event: QDropEvent) -> None:  # noqa: N802
        if not event.mimeData().hasUrls():
            return
        urls = [url.toLocalFile() for url in event.mimeData().urls()]
        paths = paths_from_drop_urls(urls)
        features, directories = classify_drop_paths(paths)
        ignored = len(paths) - len(features) - len(directories)

        if directories:
            self._open_dropped_project(directories[0])

        if features:
            if not self.workspace.apply_before_action():
                event.acceptProposedAction()
                self._restore_status_after_drag()
                return
            opened = self.workspace.open_files(features, reload_if_clean=True)
            root = get_root()
            for path in features:
                remember_feature(path)
                if root is not None and root in path.parents:
                    self._controller.catalog.select_feature(path)
            self._refresh_welcome_recents()
            self.status_bar.set_message(f"Открыто файлов: {opened}", "success")

        if ignored > 0:
            alert(
                self,
                BRAND_NAME,
                f"Пропущено элементов: {ignored} (ожидаются .feature или папка проекта).",
            )

        event.acceptProposedAction()
        if not features:
            self._restore_status_after_drag()

    def _open_dropped_project(self, folder: Path) -> None:
        resolved = folder.resolve()
        current = get_root()
        if current is not None and current.resolve() != resolved:
            if not confirm(
                self,
                BRAND_NAME,
                f"Открыть проект «{resolved.name}»?\nТекущий: {current}",
            ):
                return
        self._controller.catalog.set_features_root(resolved)
        remember_project(resolved)
        self._refresh_welcome_recents()
        self.status_bar.set_message(str(resolved))
        self.workspace.ensure_welcome_tab(activate=not self.workspace.has_editor_tabs())

    def _restore_status_after_drag(self) -> None:
        root = get_root()
        if root is not None:
            self.status_bar.set_message(str(root))
        else:
            self.status_bar.set_message("Проект → Открыть проект…", "info")

    def _on_play_step(self, index: int) -> None:
        self.workspace.clear_play_highlight()
        self.workspace.highlight_play_step(index)

    def _on_focus_failed(self, index: int) -> None:
        self.workspace.mark_failed_step(index)
        display = index + 1
        self._show_error_for_step(index, display_index=display)
        self._show_bottom_panel("error")

    def _show_error_for_step(self, step_index: int, *, display_index: int | None = None) -> None:
        steps = self._controller.scenario.steps
        step = steps[step_index] if 0 <= step_index < len(steps) else {}
        selector = str(step.get("selector") or step.get("url") or "")
        self.bottom_panel.error_panel.show_failure(
            step_index=display_index if display_index is not None else step_index + 1,
            selector=selector,
            message="Шаг не выполнен — см. журнал и результаты",
            screenshot_path=None,
        )

    def _on_validation_results(self, payload: dict) -> None:
        self.bottom_panel.validate_panel.show_results(payload)
        self.workspace.show_editor()
        self._show_bottom_panel("validate")

    def _on_validate_step_focus(self, step_index: int) -> None:
        self.workspace.show_editor()
        payload = self.bottom_panel.validate_panel.results_as_payload()
        status = ""
        for item in payload.get("results", []):
            if int(item.get("step_index", 0)) == step_index:
                status = str(item.get("status", "") or "")
                break
        failed = status not in {"", "ok", "fragile", "skipped"}
        self.workspace.gherkin_panel.highlight_step(step_index, failed=failed)

    def _on_play_results(self, payload: dict, _duration_ms: int) -> None:
        has_failed = self._controller.session.last_failed_step_index is not None
        self.bottom_panel.results_panel.show_results(payload, has_failed_step=has_failed)
        self.workspace.clear_play_highlight()
        if has_failed:
            idx = int(self._controller.session.last_failed_step_index or -1)
            self.workspace.mark_failed_step(idx)
            steps = self._controller.scenario.steps
            step = steps[idx] if 0 <= idx < len(steps) else {}
            selector = str(step.get("selector") or step.get("url") or "")
            display = int(payload.get("failed_step") or (idx + 1 if idx >= 0 else 0))
            self.bottom_panel.error_panel.show_failure(
                step_index=display,
                selector=selector,
                message=str(payload.get("message", "")),
                screenshot_path=payload.get("screenshot_path"),
                trace_path=payload.get("trace_path"),
            )
            self._show_bottom_panel("error")
        else:
            self.bottom_panel.error_panel.clear()
            self._show_bottom_panel("results")
        self._maybe_open_html_report(payload)

    def _maybe_open_html_report(self, payload: dict) -> None:
        from app.settings import load_settings

        if not load_settings().get("open_html_report_after_run", False):
            return
        from app.report_locator import ReportTarget, find_latest_report

        hints = {
            "html_report_path": payload.get("html_report_path"),
            "suite_html_index": payload.get("suite_html_index"),
            "allure_dir": payload.get("allure_dir"),
        }
        target = find_latest_report(hints=hints, project_root=get_root())
        if target is None:
            report_path = payload.get("html_report_path") or payload.get("suite_html_index")
            if report_path:
                path = Path(str(report_path))
                if path.is_file():
                    target = ReportTarget("html", path)
        if target is not None:
            self._open_report_target(target)

    def _on_save_prompt(self, count: int) -> None:
        _ = count
        self.workspace.show_post_record(list(self._controller.scenario.steps))

    def _on_picker_done(self, selector: str) -> None:
        from PySide6.QtGui import QGuiApplication

        if not selector.strip():
            return
        QGuiApplication.clipboard().setText(selector)
        self.workspace.gherkin_panel.insert_picked_selector(selector)
        self.workspace.show_editor()

    def _rerun_vanessa_failed(self) -> None:
        self._controller.recording.rerun_vanessa_failed()

    def _open_allure_results(self, allure_dir: object) -> None:
        from pathlib import Path

        from scenaria_vanessa.allure_helpers import open_allure_directory, run_allure_serve
        from scenaria_vanessa.settings import load_vanessa_settings

        if not isinstance(allure_dir, Path):
            return
        settings = load_vanessa_settings()
        cli = str(settings.get("allure_cli_path", "allure") or "allure")
        if run_allure_serve(allure_dir, cli) is None:
            open_allure_directory(allure_dir)

    def _on_batch_results(self, payload: dict, _duration_ms: int) -> None:
        self.bottom_panel.results_panel.show_results(payload, has_failed_step=not payload.get("success"))
        self.bottom_panel.error_panel.clear()
        self._show_bottom_panel("results")
        self._maybe_open_html_report(payload)

    def _on_batch_partial_results(self, payload: dict) -> None:
        if str(payload.get("runner", "") or "") != "vanessa":
            return
        panel = self.bottom_panel.results_panel
        total_hint = int(payload.get("total", 0) or 0)
        if payload.get("bootstrap"):
            panel.begin_live_suite(total_hint=total_hint)
            self._show_bottom_panel("results")
            return
        cases = list(payload.get("cases") or [])
        if not cases:
            return
        panel.update_suite_cases(cases)
        self._show_bottom_panel("results")

    def _show_about(self) -> None:
        box = QMessageBox(self)
        box.setWindowTitle(BRAND_NAME)
        pixmap = brand_mark_pixmap(96)
        if not pixmap.isNull():
            box.setIconPixmap(pixmap)
        else:
            box.setIcon(QMessageBox.Icon.Information)
        box.setText(f"{about_text()}\n\nВерсия {current_version_label()}")
        box.addButton("ОК", QMessageBox.ButtonRole.AcceptRole)
        box.exec()

    def _maybe_check_updates_on_startup(self) -> None:
        settings = load_settings()
        if not settings.get("check_updates_on_startup", True):
            return
        dismissed = str(settings.get("dismissed_update_version", "")).strip()
        self._check_updates(silent=True, skip_version=dismissed)

    def _check_updates_manual(self) -> None:
        self._check_updates(silent=False)

    def _cancel_update_check(self) -> None:
        self._update_check_token = getattr(self, "_update_check_token", 0) + 1
        self._update_check_running = False
        self._stop_update_check_watchdog()

    def _dismiss_download_progress(self) -> None:
        progress = getattr(self, "_download_progress", None)
        self._download_progress = None
        if progress is None:
            return
        progress.hide()
        progress.setVisible(False)
        progress.close()
        progress.deleteLater()

    def _check_updates(self, *, silent: bool, skip_version: str = "") -> None:
        if getattr(self, "_download_runner", None) is not None:
            if not silent:
                alert(self, BRAND_NAME, "Загрузка обновления уже выполняется…")
            return
        if getattr(self, "_update_check_running", False):
            if not silent:
                alert(self, BRAND_NAME, "Проверка обновлений уже выполняется…")
            return

        self._update_check_token = getattr(self, "_update_check_token", 0) + 1
        token = self._update_check_token
        self._update_check_running = True
        if not silent:
            self.status_bar.set_message("Проверка обновлений…", "info")

        self._update_runner = UpdateCheckRunner(self)
        self._update_runner.finished.connect(
            lambda info, error: self._on_update_check_finished(
                info, error, token=token, silent=silent, skip_version=skip_version
            )
        )
        if not silent:
            self._update_check_watchdog = QTimer(self)
            self._update_check_watchdog.setSingleShot(True)
            self._update_check_watchdog.timeout.connect(
                lambda: self._on_update_check_timeout(silent=silent)
            )
            self._update_check_watchdog.start(45_000)
        self._update_runner.start()

    def _stop_update_check_watchdog(self) -> None:
        watchdog = getattr(self, "_update_check_watchdog", None)
        if watchdog is not None:
            watchdog.stop()
            watchdog.deleteLater()
            self._update_check_watchdog = None

    def _on_update_check_timeout(self, *, silent: bool) -> None:
        if silent or not getattr(self, "_update_check_running", False):
            return
        self._cancel_update_check()
        alert(
            self,
            BRAND_NAME,
            "Проверка обновлений заняла слишком много времени. "
            "Проверьте доступ к github.com и повторите попытку.",
        )

    def _on_update_check_finished(
        self,
        info,
        error: str | None,
        *,
        token: int,
        silent: bool,
        skip_version: str,
    ) -> None:
        if token != getattr(self, "_update_check_token", 0):
            return
        self._update_check_running = False
        self._update_runner = None
        self._stop_update_check_watchdog()
        if error:
            if not silent:
                alert(self, BRAND_NAME, error)
            return
        if info is None:
            if not silent:
                alert(self, BRAND_NAME, f"Установлена актуальная версия ({current_version_label()}).")
            return
        if skip_version and info.version == skip_version:
            return
        self._offer_update(info)

    def _offer_update(self, info) -> None:
        asset = info.update or info.portable
        size_mb = round(asset.size / (1024 * 1024), 1) if asset and asset.size else None
        size_line = f"\nРазмер загрузки: ~{size_mb} МБ." if size_mb else ""
        notes = f"\n\n{info.notes}" if info.notes else ""
        text = (
            f"Доступна версия {info.version} (сейчас {current_version_label()})."
            f"{size_line}{notes}"
        )
        box = QMessageBox(self)
        box.setWindowTitle("Обновление")
        box.setText(text)
        box.setIcon(QMessageBox.Icon.Information)
        install = box.addButton("Установить", QMessageBox.ButtonRole.AcceptRole)
        box.addButton("Позже", QMessageBox.ButtonRole.RejectRole)
        later = box.addButton("Не напоминать", QMessageBox.ButtonRole.DestructiveRole)
        box.exec()
        clicked = box.clickedButton()
        if clicked == install:
            self._start_update_download(info)
            return
        if clicked == later:
            settings = load_settings()
            settings["dismissed_update_version"] = info.version
            save_settings(settings)

    def _start_update_download(self, info) -> None:
        if getattr(self, "_download_runner", None) is not None:
            alert(self, BRAND_NAME, "Загрузка обновления уже выполняется…")
            return

        progress = QMessageBox(self)
        progress.setWindowTitle("Загрузка обновления")
        progress.setText("Скачивание и установка…")
        progress.setStandardButtons(QMessageBox.StandardButton.NoButton)
        progress.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        progress.show()

        self._download_progress = progress
        self._download_runner = UpdateDownloadRunner(info)
        self._download_runner.progress.connect(self._on_update_download_progress)
        self._download_runner.finished.connect(self._on_update_download_finished)
        self._download_runner.start()

    def _on_update_download_progress(self, done: int, total: int) -> None:
        progress = getattr(self, "_download_progress", None)
        if progress is None:
            return
        percent = int(done * 100 / total) if total else 0
        progress.setText(f"Скачивание… {percent}%")

    def _on_update_download_finished(self, error: str | None) -> None:
        runner = self._download_runner
        self._download_runner = None
        if runner is not None:
            try:
                runner.progress.disconnect(self._on_update_download_progress)
            except (RuntimeError, TypeError):
                pass
            try:
                runner.finished.disconnect(self._on_update_download_finished)
            except (RuntimeError, TypeError):
                pass
        self._dismiss_download_progress()
        if error:
            self._show_update_download_error(error)

    def _show_update_download_error(self, message: str) -> None:
        box = QMessageBox(self)
        box.setWindowTitle(BRAND_NAME)
        box.setIcon(QMessageBox.Icon.Warning)
        box.setText(message)
        open_page = box.addButton("Открыть страницу загрузки", QMessageBox.ButtonRole.ActionRole)
        box.addButton(BTN_OK, QMessageBox.ButtonRole.AcceptRole)
        box.exec()
        if box.clickedButton() == open_page:
            QDesktopServices.openUrl(QUrl(f"https://github.com/{github_repo()}/releases/latest"))

    def closeEvent(self, event) -> None:  # noqa: N802
        self._dismiss_download_progress()
        self._cancel_update_check()
        self._browser_watch_timer.stop()
        self._browser_overlay.hide()
        editor_text = self.workspace.prepare_shutdown()
        self._bridge.stop()
        self._controller.shutdown(editor_text=editor_text)
        super().closeEvent(event)
