"""Editor area: welcome screen, tab bar, and Gherkin editor."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QSizePolicy, QStackedWidget, QTabBar, QToolButton, QVBoxLayout, QWidget

from app.gherkin_ru import GherkinParseError, gherkin_to_steps
from app.feature_store import feature_texts_equivalent, normalize_feature_text
from app.mvc.controllers.app_controller import AppController
from app.mvc.controllers.scenario_controller import ScenarioController
from app.mvc.models.scenario_model import ScenarioModel
from app.mvc.models.session_model import SessionModel
from app.qt.dialogs import confirm
from app.qt import icons
from app.qt.widgets.dirty_banner import DirtyBanner
from app.qt.widgets.gherkin_panel import GherkinPanel
from app.qt.widgets.ide_splitter import HIT_SIZE, IdeSplitter
from app.qt.widgets.post_record_banner import PostRecordBanner
from app.qt.widgets.editor_action_bar import EditorActionBar
from app.qt.widgets.recording_modes_bar import RecordingModesBar
from app.qt.widgets.steps_strip import StepsStrip
from app.qt.widgets.welcome_panel import WelcomePanel
from app.scenario_hints import ScenarioHint, collect_all_hints
from app.settings import load_settings, save_settings
from app.brand import BRAND_NAME

_PAGE_WELCOME = 0
_PAGE_EDITOR = 1
_WELCOME_KEY = "__welcome__"


@dataclass
class _EditorTab:
    key: str
    path: Path | None
    title: str
    text: str = ""
    unapplied: bool = False
    unsaved: bool = False

    @property
    def is_welcome(self) -> bool:
        return self.key == _WELCOME_KEY


class EditorWorkspace(QWidget):
    state_changed = Signal(str)
    welcome_activated = Signal()

    def __init__(self, controller: AppController, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setProperty("role", "workspace")
        self.setMinimumWidth(0)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._controller = controller
        self._model: ScenarioModel = controller.scenario
        self._scenario_controller: ScenarioController = controller.scenario_controller
        self._session: SessionModel = controller.session

        self._tabs: list[_EditorTab] = []
        self._current_index = -1
        self._untitled_counter = 0
        self._switching = False
        self._last_record_steps: list[dict] = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.editor_action_bar = EditorActionBar(self)
        layout.addWidget(self.editor_action_bar)

        self.tab_bar = QTabBar()
        self.tab_bar.setProperty("role", "editor-tabs")
        self.tab_bar.setDocumentMode(True)
        self.tab_bar.setTabsClosable(False)
        self.tab_bar.setExpanding(False)
        self.tab_bar.setDrawBase(True)
        self.tab_bar.setUsesScrollButtons(True)
        self.tab_bar.setElideMode(Qt.TextElideMode.ElideNone)
        self.tab_bar.currentChanged.connect(self._on_tab_changed)
        layout.addWidget(self.tab_bar)

        self.stack = QStackedWidget()
        self.stack.setProperty("role", "editor-stack")

        self.welcome_panel = WelcomePanel(self.stack)
        self.stack.addWidget(self.welcome_panel)

        editor_page = QWidget()
        editor_layout = QVBoxLayout(editor_page)
        editor_layout.setContentsMargins(0, 0, 0, 0)
        editor_layout.setSpacing(0)

        self.recording_modes = RecordingModesBar(editor_page)
        editor_layout.addWidget(self.recording_modes)

        self.dirty_banner = DirtyBanner(editor_page)
        editor_layout.addWidget(self.dirty_banner)

        self.post_record_banner = PostRecordBanner(editor_page)
        editor_layout.addWidget(self.post_record_banner)

        self.gherkin_panel = GherkinPanel(self._model, self._scenario_controller, editor_page, compact=True)

        self.steps_strip = StepsStrip(editor_page)

        self._editor_splitter = IdeSplitter(Qt.Orientation.Vertical, editor_page)
        self._editor_splitter.setProperty("role", "editor-splitter")
        self._editor_splitter.setHandleWidth(HIT_SIZE)
        self._editor_splitter.addWidget(self.gherkin_panel)
        self._editor_splitter.addWidget(self.steps_strip)
        self._editor_splitter.setCollapsible(0, False)
        self._editor_splitter.setCollapsible(1, True)
        self._editor_splitter.setStretchFactor(0, 1)
        self._editor_splitter.setStretchFactor(1, 0)
        editor_layout.addWidget(self._editor_splitter, stretch=1)

        self._steps_collapsed_bar = QWidget(editor_page)
        self._steps_collapsed_bar.setProperty("role", "steps-collapsed-bar")
        self._steps_collapsed_bar.setFixedHeight(24)
        collapsed_layout = QHBoxLayout(self._steps_collapsed_bar)
        collapsed_layout.setContentsMargins(8, 0, 8, 0)
        collapsed_layout.setSpacing(6)
        collapsed_title = QLabel("Шаги")
        collapsed_title.setStyleSheet("font-size: 8pt; font-weight: 600;")
        collapsed_layout.addWidget(collapsed_title)
        self._steps_collapsed_count = QLabel("")
        self._steps_collapsed_count.setStyleSheet("font-size: 8pt; color: #858585;")
        collapsed_layout.addWidget(self._steps_collapsed_count)
        collapsed_layout.addStretch()
        expand_btn = QPushButton("▲")
        expand_btn.setFixedWidth(28)
        expand_btn.setToolTip("Показать панель шагов")
        expand_btn.clicked.connect(self._expand_steps_panel)
        collapsed_layout.addWidget(expand_btn)
        self._steps_collapsed_bar.hide()
        editor_layout.addWidget(self._steps_collapsed_bar)

        self._steps_panel_height = 160
        self._steps_panel_visible = True
        self._steps_panel_layout_done = False

        self.stack.addWidget(editor_page)

        layout.addWidget(self.stack, stretch=1)

        self.dirty_banner.discard_clicked.connect(self.gherkin_panel.discard_changes)
        self.dirty_banner.apply_clicked.connect(self.gherkin_panel._apply)
        self.steps_strip.step_selected.connect(self.gherkin_panel.focus_step)
        self.steps_strip.fix_menu_clicked.connect(self._fix_menu_for_step)
        self.steps_strip.step_delete.connect(self._on_step_delete)
        self.steps_strip.step_move_up.connect(self._on_step_move_up)
        self.steps_strip.step_move_down.connect(self._on_step_move_down)
        self.steps_strip.step_edit.connect(self._on_step_edit)
        self.steps_strip.collapse_requested.connect(self._collapse_steps_panel)
        self.steps_strip.run_from_step.connect(self._run_from_step)
        self.steps_strip.run_until_step.connect(self._run_until_step)
        self._editor_splitter.splitterMoved.connect(self._on_steps_splitter_moved)

        self._load_steps_panel_settings()
        QTimer.singleShot(0, self._apply_steps_panel_layout)

        self._session.changed.connect(self._sync_state)
        self._model.changed.connect(self._on_model_changed)
        self.gherkin_panel.status_message.connect(self._forward_gherkin_status)
        self.gherkin_panel.dirty_changed.connect(self._on_editor_dirty_changed)
        self.gherkin_panel.applied.connect(self._on_gherkin_applied)
        self._sync_state()

    @property
    def quick_toolbar(self):
        return self.editor_action_bar.toolbar

    @property
    def start_url(self) -> str:
        return self._model.start_url

    def _forward_gherkin_status(self, text: str) -> None:
        if text:
            self.state_changed.emit(text)

    def _show_welcome_if_needed(self) -> None:
        from app.feature_store import get_root

        if get_root() is None:
            self.ensure_welcome_tab(activate=True)

    def ensure_welcome_tab(self, *, activate: bool = False) -> None:
        for index, tab in enumerate(self._tabs):
            if tab.is_welcome:
                self.tab_bar.setVisible(True)
                if activate:
                    self._activate_tab(index)
                return

        welcome = _EditorTab(key=_WELCOME_KEY, path=None, title="Старт", text="")
        self._tabs.insert(0, welcome)
        self._insert_tab_bar_tab(0, welcome)
        if self._current_index >= 0:
            self._current_index += 1
        self.tab_bar.setVisible(True)
        if activate:
            self._activate_tab(0)
        elif self._current_index >= 0:
            self.tab_bar.setCurrentIndex(self._current_index)

    def show_welcome(self) -> None:
        self.ensure_welcome_tab(activate=True)

    def show_editor(self) -> None:
        if not self._tabs:
            self._show_empty_workspace()
            return
        if self._current_index >= 0 and self._current_index < len(self._tabs):
            tab = self._tabs[self._current_index]
            if tab.is_welcome:
                for index, candidate in enumerate(self._tabs):
                    if not candidate.is_welcome:
                        self._activate_tab(index)
                        return
                self.open_untitled()
                return
        self.tab_bar.setVisible(bool(self._tabs))
        self.stack.setCurrentIndex(_PAGE_EDITOR)

    def has_open_tabs(self) -> bool:
        return bool(self._tabs)

    def has_editor_tabs(self) -> bool:
        return any(not tab.is_welcome for tab in self._tabs)

    def open_feature_paths(self) -> list[Path]:
        return [
            tab.path
            for tab in self._tabs
            if tab.path is not None and tab.path.is_file()
        ]

    def dirty_feature_paths(self) -> set[Path]:
        dirty: set[Path] = set()
        for index, tab in enumerate(self._tabs):
            if tab.path is None or tab.is_welcome:
                continue
            if tab.unapplied or tab.unsaved:
                dirty.add(tab.path.resolve())
                continue
            if index == self._current_index and self.gherkin_panel.is_dirty:
                dirty.add(tab.path.resolve())
        return dirty

    def sync_replaced_files(self, changed: dict[Path, tuple[str, int]]) -> None:
        for path, (new_text, _count) in changed.items():
            resolved = path.resolve()
            for index, tab in enumerate(self._tabs):
                if tab.path is not None and tab.path.resolve() == resolved:
                    tab.text = new_text
                    tab.unapplied = False
                    tab.unsaved = False
                    if index == self._current_index:
                        self.gherkin_panel.set_text(new_text, clean=True)
                    break

    def current_tab(self) -> _EditorTab | None:
        if self._current_index < 0 or self._current_index >= len(self._tabs):
            return None
        return self._tabs[self._current_index]

    def is_editor_tab_active(self) -> bool:
        tab = self.current_tab()
        return tab is not None and not tab.is_welcome

    def sync_chrome(
        self,
        *,
        pending: bool,
        browser_open: bool,
        recorder_browser_open: bool = False,
        recording: bool,
        playing: bool,
        has_steps: bool,
    ) -> None:
        if not recorder_browser_open:
            recorder_browser_open = browser_open
        editor_active = self.is_editor_tab_active()
        panel = self.gherkin_panel
        parse_error = panel.has_parse_error if editor_active else False
        text_unapplied = panel.is_unapplied if editor_active else False
        self.editor_action_bar.set_url(self._model.start_url)
        self.editor_action_bar.set_editor_fields_enabled(editor_active)
        self._update_run_target()
        self.recording_modes.sync(
            visible=(browser_open or recording) and editor_active,
            filter_recording=self._session.filter_recording,
            nav_only_recording=self._session.nav_only_recording,
            headless=self._session.headless,
            use_saved_session=bool(load_settings().get("use_saved_browser_session", True)),
            hover_recording=self._session.hover_recording,
        )
        if editor_active and not recording:
            if parse_error:
                self.dirty_banner.set_banner(visible=True, mode="parse_error")
            elif text_unapplied:
                self.dirty_banner.set_banner(visible=True, mode="unapplied")
            else:
                self.dirty_banner.set_visible(False)
        else:
            self.dirty_banner.set_visible(False)
        self._refresh_steps_strip()

    def show_post_record(self, steps: list[dict]) -> None:
        self._last_record_steps = list(steps)
        self.post_record_banner.reset_dismissed()
        hints = collect_all_hints(steps)
        self.post_record_banner.show_recording(len(steps), hints=hints)
        self.sync_after_recording()
        self._last_record_steps = []
        self.show_editor()

    def hide_post_record(self) -> None:
        self.post_record_banner.hide_banner()

    def _is_file_unsaved(self, tab: _EditorTab | None = None) -> bool:
        if tab is None:
            if self._current_index < 0:
                return False
            tab = self._tabs[self._current_index]
        text = (
            self.gherkin_panel.get_text()
            if self._current_index >= 0 and self._tabs[self._current_index] is tab
            else tab.text
        )
        if tab.path is None:
            return bool(text.strip())
        if tab.path.is_file():
            try:
                disk = tab.path.read_text(encoding="utf-8")
            except OSError:
                return bool(text.strip())
            return not self._text_matches_disk(text, disk)
        return bool(text.strip())

    @staticmethod
    def _text_matches_disk(editor_text: str, disk_text: str) -> bool:
        return normalize_feature_text(editor_text) == normalize_feature_text(disk_text)

    def _prepare_leave_current_tab(self) -> bool:
        """Flush the active editor into tab state (no confirmation dialogs)."""
        if self._current_index < 0:
            return True
        tab = self._tabs[self._current_index]
        if tab.is_welcome:
            return True
        self._persist_current_tab()
        return True

    def open_files(self, paths: list[Path], *, reload_if_clean: bool = False) -> int:
        opened = 0
        for path in paths:
            if self.open_file(path, reload_if_clean=reload_if_clean):
                opened += 1
        return opened

    def open_file(self, path: Path, *, reload_if_clean: bool = False) -> bool:
        resolved = path.resolve()
        key = str(resolved)
        for index, tab in enumerate(self._tabs):
            if tab.key == key:
                if reload_if_clean and not tab.unapplied and not tab.unsaved:
                    return self._reload_file_tab(index)
                return self._activate_tab(index)
        if not self._prepare_leave_current_tab():
            return False
        try:
            raw = resolved.read_text(encoding="utf-8")
        except OSError:
            raw = ""
        tab = _EditorTab(key=key, path=resolved, title=resolved.name, text=raw)
        self._tabs.append(tab)
        self._add_tab_bar_tab(tab)
        return self._activate_tab(len(self._tabs) - 1)

    def open_untitled(self, *, initial_text: str = "") -> bool:
        if not self._prepare_leave_current_tab():
            return False
        self._untitled_counter += 1
        title = f"Без названия {self._untitled_counter}"
        key = f"untitled:{self._untitled_counter}"
        tab = _EditorTab(key=key, path=None, title=title, text=initial_text)
        self._tabs.append(tab)
        self._add_tab_bar_tab(tab)
        return self._activate_tab(len(self._tabs) - 1)

    def restore_session_tab(self) -> None:
        if self._tabs:
            return
        settings = load_settings()
        saved_tabs = settings.get("open_tabs")
        if isinstance(saved_tabs, list) and saved_tabs:
            active = int(settings.get("active_tab_index", 0))
            if self._restore_saved_tabs(saved_tabs, active):
                return
        if self._model.feature_path:
            self.open_file(self._model.feature_path)
            return
        if not self._model.steps and not self._model.dirty:
            return
        draft_text = self._scenario_controller.commit_steps_to_gherkin()
        self._untitled_counter += 1
        key = f"untitled:{self._untitled_counter}"
        title = "Черновик"
        tab = _EditorTab(key=key, path=None, title=title, text=draft_text, unsaved=True)
        self._tabs.append(tab)
        self._add_tab_bar_tab(tab)
        self._activate_tab(len(self._tabs) - 1)

    def persist_session(self) -> None:
        self._persist_current_tab()
        settings = load_settings()
        payload: list[dict[str, object]] = []
        for tab in self._tabs:
            if tab.is_welcome:
                continue
            payload.append(
                {
                    "path": str(tab.path.resolve()) if tab.path is not None else "",
                    "title": tab.title,
                    "text": tab.text,
                    "unapplied": tab.unapplied,
                    "unsaved": tab.unsaved,
                    "key": tab.key,
                }
            )
        settings["open_tabs"] = payload
        settings["active_tab_index"] = max(0, self._current_index)
        save_settings(settings)

    def prepare_shutdown(self) -> str | None:
        self.persist_session()
        self.flush_all_tabs_to_disk()
        self._persist_current_tab()
        if not self.has_editor_tabs():
            return None
        if self._current_index >= 0 and self._tabs[self._current_index].is_welcome:
            return None
        return self.gherkin_panel.get_text()

    def flush_all_tabs_to_disk(self) -> None:
        self._persist_current_tab()
        for tab in self._tabs:
            if tab.path is None or tab.unapplied or not tab.text.strip():
                continue
            self._scenario_controller.flush_editor_to_disk(tab.text, path=tab.path)

    def close_tabs_for_path(self, path: Path, *, force: bool = False) -> None:
        key = str(path.resolve())
        for index in sorted(
            (i for i, tab in enumerate(self._tabs) if tab.key == key),
            reverse=True,
        ):
            self._close_tab_at(index, force=force)

    def _reload_file_tab(self, index: int) -> bool:
        if index < 0 or index >= len(self._tabs):
            return False
        tab = self._tabs[index]
        if tab.path is not None and tab.path.is_file():
            try:
                tab.text = tab.path.read_text(encoding="utf-8")
                tab.unapplied = False
                tab.unsaved = False
            except OSError:
                pass
        if index == self._current_index and self.stack.currentIndex() == _PAGE_EDITOR:
            self._current_index = -1
        return self._activate_tab(index)

    def _restore_saved_tabs(self, saved: list, active_index: int) -> bool:
        for item in saved:
            if not isinstance(item, dict):
                continue
            path_raw = str(item.get("path", "") or "").strip()
            path = Path(path_raw) if path_raw else None
            text = str(item.get("text", "") or "")
            title = str(item.get("title", "") or "")
            key = str(item.get("key", "") or "")
            if key == _WELCOME_KEY:
                continue
            unapplied = bool(item.get("unapplied"))
            unsaved = bool(item.get("unsaved"))
            if path is not None:
                if not path.is_file():
                    continue
                key = str(path.resolve())
                title = title or path.name
            else:
                if not key:
                    self._untitled_counter += 1
                    key = f"untitled:{self._untitled_counter}"
                if not title:
                    self._untitled_counter += 1
                    title = f"Без названия {self._untitled_counter}"
            tab = _EditorTab(
                key=key,
                path=path,
                title=title,
                text=text,
                unapplied=unapplied,
                unsaved=unsaved,
            )
            self._tabs.append(tab)
            self._add_tab_bar_tab(tab)
        if not self._tabs:
            return False
        index = min(max(0, active_index), len(self._tabs) - 1)
        self._activate_tab(index)
        return True

    def _add_tab_bar_tab(self, tab: _EditorTab) -> int:
        return self._insert_tab_bar_tab(self.tab_bar.count(), tab)

    def _insert_tab_bar_tab(self, index: int, tab: _EditorTab) -> int:
        if index >= self.tab_bar.count():
            index = self.tab_bar.addTab("")
        else:
            self.tab_bar.insertTab(index, "")
        close = QToolButton(self.tab_bar)
        close.setIcon(icons.icon("close", size=12))
        close.setIconSize(icons.icon_size(12))
        close.setAccessibleName("Закрыть вкладку")
        close.setCursor(Qt.CursorShape.PointingHandCursor)
        close.setAutoRaise(True)
        close.setFixedSize(16, 16)
        close.setProperty("tab-close", True)
        close.clicked.connect(self._on_close_button_clicked)
        self.tab_bar.setTabButton(index, QTabBar.ButtonPosition.RightSide, close)
        self._update_tab_bar_item(index)
        return index

    def _update_tab_bar_item(self, index: int) -> None:
        if index < 0 or index >= len(self._tabs):
            return
        tab = self._tabs[index]
        if tab.is_welcome:
            self.tab_bar.setTabIcon(index, icons.welcome_tab_icon())
            self.tab_bar.setTabText(index, tab.title)
            self.tab_bar.setTabToolTip(index, "Стартовая страница")
            return
        self.tab_bar.setTabIcon(index, QIcon())
        self.tab_bar.setTabText(index, self._tab_label(tab))
        self.tab_bar.setTabToolTip(index, str(tab.path) if tab.path is not None else tab.title)

    def _on_close_button_clicked(self) -> None:
        button = self.sender()
        for index in range(self.tab_bar.count()):
            if self.tab_bar.tabButton(index, QTabBar.ButtonPosition.RightSide) is button:
                self._on_tab_close_requested(index)
                return

    def _tab_label(self, tab: _EditorTab) -> str:
        label = tab.title
        if tab.unapplied:
            label += " ●"
        if tab.unsaved:
            label += " *"
        return label

    def _persist_current_tab(self) -> None:
        if self._current_index < 0 or self._current_index >= len(self._tabs):
            return
        tab = self._tabs[self._current_index]
        if tab.is_welcome:
            return
        tab.text = self.gherkin_panel.get_text()
        tab.unapplied = self.gherkin_panel.is_unapplied or self.gherkin_panel.has_parse_error
        tab.unsaved = self._is_file_unsaved()
        self._update_tab_bar_item(self._current_index)
        self._update_run_target()

    def persist_current_tab(self) -> None:
        """Public wrapper for flushing the active editor into tab state."""
        self._persist_current_tab()

    def _update_run_target(self) -> None:
        if self._current_index < 0 or self._current_index >= len(self._tabs):
            self.editor_action_bar.set_run_target(
                title="—",
                path=None,
                unapplied=False,
                unsaved=False,
            )
            return
        tab = self._tabs[self._current_index]
        if tab.is_welcome:
            self.editor_action_bar.set_run_target(
                title=tab.title,
                path=None,
                unapplied=False,
                unsaved=False,
                is_welcome=True,
            )
            return
        self.editor_action_bar.set_run_target(
            title=tab.title,
            path=tab.path,
            unapplied=tab.unapplied,
            unsaved=tab.unsaved,
            tags=self._model.tags,
        )

    def _restore_tab_content(self, tab: _EditorTab) -> None:
        if tab.path is not None:
            if not tab.path.is_file():
                self._scenario_controller.bind_feature_path(tab.path)
                self.gherkin_panel.set_text(tab.text, clean=False)
                return

            if tab.unapplied or tab.unsaved:
                self._scenario_controller.bind_feature_path(tab.path)
                self.gherkin_panel.set_text(tab.text, clean=False)
                self.gherkin_panel._auto_apply_timer.stop()
                self.gherkin_panel._auto_apply_if_valid()
                return

            try:
                self._scenario_controller.load_feature(tab.path)
                self.gherkin_panel.sync_from_model(force=True)
                tab.text = self.gherkin_panel.get_text()
                tab.unapplied = False
                tab.unsaved = False
            except (OSError, GherkinParseError):
                self._scenario_controller.bind_feature_path(tab.path)
                self.gherkin_panel.set_text(tab.text, clean=False)
                self.gherkin_panel._auto_apply_timer.stop()
                self.gherkin_panel._auto_apply_if_valid()
            return

        self._scenario_controller.new_scenario()
        if tab.text.strip():
            self.gherkin_panel.set_text(tab.text, clean=False)
            self.gherkin_panel._auto_apply_timer.stop()
            self.gherkin_panel._auto_apply_if_valid()
        else:
            self.gherkin_panel.set_text("", clean=True)

    def _activate_tab(self, index: int) -> bool:
        if index < 0 or index >= len(self._tabs):
            return False
        tab = self._tabs[index]
        if tab.is_welcome:
            if index == self._current_index and self.stack.currentIndex() == _PAGE_WELCOME:
                return True
            self._switching = True
            self._persist_current_tab()
            self._current_index = index
            self.tab_bar.setCurrentIndex(index)
            self.tab_bar.setVisible(True)
            self.stack.setCurrentIndex(_PAGE_WELCOME)
            self.editor_action_bar.set_run_target(
                title="Старт",
                path=None,
                unapplied=False,
                unsaved=False,
                is_welcome=True,
            )
            self.dirty_banner.set_visible(False)
            self._switching = False
            self.welcome_activated.emit()
            return True

        if index == self._current_index and self.stack.currentIndex() == _PAGE_EDITOR:
            return True

        self._switching = True
        self._persist_current_tab()
        self._current_index = index
        tab = self._tabs[index]
        self.tab_bar.setCurrentIndex(index)

        self.gherkin_panel.set_sync_from_model(False)
        try:
            self._restore_tab_content(tab)
        finally:
            self.gherkin_panel.set_sync_from_model(True)
            self._switching = False

        self.show_editor()
        self._refresh_steps_strip()
        self._update_run_target()
        return True

    def _on_tab_changed(self, index: int) -> None:
        if self._switching or index == self._current_index:
            return
        if index < 0:
            if not self._tabs:
                self._show_empty_workspace()
            return
        self._activate_tab(index)

    def _on_tab_close_requested(self, index: int) -> None:
        self._close_tab_at(index, force=False)

    def _close_tab_at(self, index: int, *, force: bool) -> bool:
        if index < 0 or index >= len(self._tabs):
            return False
        tab = self._tabs[index]
        is_current = index == self._current_index
        if not force and not tab.is_welcome:
            if is_current and self.gherkin_panel.is_dirty:
                if not confirm(
                    self,
                    BRAND_NAME,
                    f"Закрыть «{tab.title}»?\nНеприменённые изменения будут потеряны.",
                ):
                    return False
            elif tab.unapplied:
                if not confirm(
                    self,
                    BRAND_NAME,
                    f"Закрыть «{tab.title}»?\nВкладка содержит неприменённые изменения.",
                ):
                    return False
            elif tab.unsaved:
                if not confirm(
                    self,
                    BRAND_NAME,
                    f"Закрыть «{tab.title}»?\nЕсть несохранённые изменения.",
                ):
                    return False

        self._switching = True
        self.tab_bar.removeTab(index)
        self._tabs.pop(index)
        if not self._tabs:
            self._current_index = -1
            self._show_empty_workspace()
        elif is_current:
            new_index = min(index, len(self._tabs) - 1)
            self._current_index = -1
            self._activate_tab(new_index)
        elif index < self._current_index:
            self._current_index -= 1
        self._switching = False
        return True

    def _show_empty_workspace(self) -> None:
        self._scenario_controller.new_scenario()
        self.gherkin_panel.set_text("", clean=True)
        self.steps_strip.set_steps([])
        self.dirty_banner.set_visible(False)
        self.post_record_banner.hide_banner()
        self.editor_action_bar.set_run_target(
            title="—",
            path=None,
            unapplied=False,
            unsaved=False,
        )
        self.ensure_welcome_tab(activate=True)

    def _on_editor_dirty_changed(self, dirty: bool) -> None:
        if self._current_index < 0 or self._current_index >= len(self._tabs):
            return
        tab = self._tabs[self._current_index]
        if tab.is_welcome:
            return
        panel = self.gherkin_panel
        tab.unapplied = panel.is_unapplied or panel.has_parse_error
        tab.text = panel.get_text()
        tab.unsaved = self._is_file_unsaved()
        self._update_tab_bar_item(self._current_index)
        if not self._session.recording:
            if panel.has_parse_error:
                self.dirty_banner.set_banner(visible=True, mode="parse_error")
            elif panel.is_unapplied:
                self.dirty_banner.set_banner(visible=True, mode="unapplied")
            else:
                self.dirty_banner.set_visible(False)
        else:
            self.dirty_banner.set_visible(False)
        self._update_run_target()

    def _on_gherkin_applied(self) -> None:
        self._refresh_steps_strip()
        self.hide_post_record()
        if self._current_index >= 0:
            tab = self._tabs[self._current_index]
            tab.text = self.gherkin_panel.get_text()
            tab.unapplied = False
            tab.unsaved = self._is_file_unsaved(tab)
            self._update_tab_bar_item(self._current_index)
            self._update_run_target()

    def sync_after_recording(self) -> None:
        """Push recorded steps into the Gherkin editor and steps strip."""
        self.gherkin_panel.sync_from_model(force=True)
        self.steps_strip.set_steps(self._model.steps)
        if self._current_index >= 0:
            tab = self._tabs[self._current_index]
            tab.text = self.gherkin_panel.get_text()
            tab.unapplied = False
            tab.unsaved = self._is_file_unsaved()
            self._update_tab_bar_item(self._current_index)
        self._update_run_target()

    def apply_before_action(self) -> bool:
        """Parse current Gherkin editor text into the scenario model."""
        return self.gherkin_panel.apply_to_model()

    def _on_model_changed(self) -> None:
        if self._switching:
            return
        if self._session.recording:
            self.gherkin_panel.sync_from_model(force=True)
        self._refresh_steps_strip()
        if self._current_index >= 0:
            tab = self._tabs[self._current_index]
            tab.text = self.gherkin_panel.get_text()
            tab.unsaved = self._is_file_unsaved(tab)
            self._update_tab_bar_item(self._current_index)
            self._update_run_target()

    def _refresh_steps_strip(self) -> None:
        panel = self.gherkin_panel
        if panel.has_parse_error and not self._last_record_steps:
            raw = panel.get_text().strip()
            if raw:
                try:
                    self.steps_strip.set_steps(gherkin_to_steps(raw))
                    self._update_steps_collapsed_label()
                    return
                except GherkinParseError:
                    pass
            if self._model.steps:
                self.steps_strip.set_steps(self._model.steps)
                self._update_steps_collapsed_label()
            return
        self.steps_strip.set_steps(self._model.steps)
        self._update_steps_collapsed_label()

    def _update_steps_collapsed_label(self) -> None:
        count = self.steps_strip.step_count()
        self._steps_collapsed_count.setText(f"({count})" if count else "")

    def _load_steps_panel_settings(self) -> None:
        settings = load_settings()
        self._steps_panel_height = max(80, int(settings.get("steps_panel_height", 160)))
        self._steps_panel_visible = bool(settings.get("steps_panel_visible", True))

    def reload_interface_settings(self) -> None:
        self._load_steps_panel_settings()
        self._apply_steps_panel_layout()

    def _save_steps_panel_settings(self) -> None:
        settings = load_settings()
        settings["steps_panel_height"] = self._steps_panel_height
        settings["steps_panel_visible"] = self._steps_panel_visible
        save_settings(settings)

    def _splitter_total_height(self) -> int:
        total = sum(self._editor_splitter.sizes())
        if total > 0:
            return total
        return max(self._editor_splitter.height(), 400)

    def _apply_steps_panel_layout(self) -> None:
        total = self._splitter_total_height()
        if total < 120:
            QTimer.singleShot(50, self._apply_steps_panel_layout)
            return
        if self._steps_panel_visible:
            panel_h = max(80, min(self._steps_panel_height, total - 120))
            self._editor_splitter.setHandleWidth(HIT_SIZE)
            self._editor_splitter.setSizes([max(1, total - panel_h), panel_h])
            self._steps_collapsed_bar.hide()
        else:
            self._editor_splitter.setHandleWidth(0)
            self._editor_splitter.setSizes([max(1, total), 0])
            self._steps_collapsed_bar.show()
        self._steps_panel_layout_done = True
        self._update_steps_collapsed_label()

    def _on_steps_splitter_moved(self, _pos: int, _index: int) -> None:
        sizes = self._editor_splitter.sizes()
        if len(sizes) < 2:
            return
        if sizes[1] <= 0:
            self._steps_panel_visible = False
            self._editor_splitter.setHandleWidth(0)
            self._steps_collapsed_bar.show()
            self._update_steps_collapsed_label()
            self._save_steps_panel_settings()
            return
        self._steps_panel_height = sizes[1]
        self._steps_panel_visible = True
        self._steps_collapsed_bar.hide()
        self._editor_splitter.setHandleWidth(HIT_SIZE)
        self._save_steps_panel_settings()

    def reset_editor_layout(self) -> None:
        self._steps_panel_visible = False
        self._collapse_steps_panel()

    def _collapse_steps_panel(self) -> None:
        sizes = self._editor_splitter.sizes()
        if len(sizes) >= 2 and sizes[1] > 0:
            self._steps_panel_height = sizes[1]
        total = self._splitter_total_height()
        self._steps_panel_visible = False
        self._editor_splitter.setHandleWidth(0)
        self._editor_splitter.setSizes([max(1, total), 0])
        self._steps_collapsed_bar.show()
        self._update_steps_collapsed_label()
        self._save_steps_panel_settings()

    def _expand_steps_panel(self) -> None:
        total = self._splitter_total_height()
        panel_h = max(80, min(self._steps_panel_height, total - 120))
        self._steps_panel_visible = True
        self._editor_splitter.setHandleWidth(HIT_SIZE)
        self._editor_splitter.setSizes([max(1, total - panel_h), panel_h])
        self._steps_collapsed_bar.hide()
        self._save_steps_panel_settings()

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        if not self._steps_panel_layout_done:
            self._apply_steps_panel_layout()

    def _fix_menu_for_step(self, step_index: int) -> None:
        index = step_index - 1
        if self._scenario_controller.try_fix_menu_hover(index):
            self._sync_steps_from_controller(select_row=step_index)
            return
        self.gherkin_panel.focus_step(step_index)
        self.gherkin_panel.fix_menu_click_at_cursor()

    def _sync_steps_from_controller(self, *, select_row: int | None = None) -> None:
        text = self._scenario_controller.commit_steps_to_gherkin()
        self.gherkin_panel.set_text(text, clean=True)
        self.steps_strip.set_steps(self._model.steps)
        if self._current_index >= 0:
            tab = self._tabs[self._current_index]
            tab.text = text
            tab.unapplied = False
            tab.unsaved = self._is_file_unsaved(tab)
            self._update_tab_bar_item(self._current_index)
        if select_row is not None:
            self.steps_strip.select_row(select_row)
        self._update_run_target()

    def _on_step_delete(self, index: int) -> None:
        self._scenario_controller.delete_step(index)
        row = min(index, max(0, len(self._model.steps) - 1))
        self._sync_steps_from_controller(select_row=row if self._model.steps else None)

    def _on_step_move_up(self, index: int) -> None:
        _steps, new_index = self._scenario_controller.move_step_up(index)
        self._sync_steps_from_controller(select_row=new_index)

    def _on_step_move_down(self, index: int) -> None:
        _steps, new_index = self._scenario_controller.move_step_down(index)
        self._sync_steps_from_controller(select_row=new_index)

    def _on_step_edit(self, index: int) -> None:
        if self._scenario_controller.edit_step(self, index) is None:
            return
        self._sync_steps_from_controller(select_row=index)

    def _run_from_step(self, index: int) -> None:
        if not self.gherkin_panel.apply_to_model():
            return
        self._controller.recording.play(start_step=index)

    def _run_until_step(self, index: int) -> None:
        if not self.gherkin_panel.apply_to_model():
            return
        self._controller.recording.play(start_step=0, end_step=index)

    def on_document_saved(self, path: Path) -> None:
        if self._current_index < 0 or self._current_index >= len(self._tabs):
            return
        resolved = path.resolve()
        tab = self._tabs[self._current_index]
        tab.key = str(resolved)
        tab.path = resolved
        tab.title = resolved.name
        try:
            tab.text = resolved.read_text(encoding="utf-8")
        except OSError:
            tab.text = self.gherkin_panel.get_text()
        tab.unapplied = False
        tab.unsaved = False
        self._update_tab_bar_item(self._current_index)
        current = self.gherkin_panel.get_text()
        if feature_texts_equivalent(current, tab.text):
            self.gherkin_panel.mark_clean()
        else:
            self.gherkin_panel.set_text(tab.text, clean=True)
        self._update_run_target()

    def _sync_state(self) -> None:
        s = self._session
        if s.pending:
            text = "Ожидание…"
        elif s.recording:
            count = len(self._model.steps)
            text = f"Пауза · {count}" if s.paused else f"Запись · {count}"
        elif s.playing:
            text = "Тест"
        elif s.browser_open:
            text = "Браузер"
        else:
            text = ""
        self.state_changed.emit(text)

    def focus_failed_step(self, step_index: int) -> None:
        self.show_editor()
        ui = step_index + 1
        self.gherkin_panel.focus_step(ui)
        self.steps_strip.highlight_step(ui)

    def clear_play_highlight(self) -> None:
        self.gherkin_panel.clear_step_highlight()

    def highlight_play_step(self, step_index: int) -> None:
        self.show_editor()
        ui = step_index + 1
        self.gherkin_panel.highlight_step(ui)
        self.steps_strip.highlight_step(ui)

    def mark_failed_step(self, step_index: int) -> None:
        self.show_editor()
        ui = step_index + 1
        self.gherkin_panel.highlight_step(ui, failed=True)
        self.steps_strip.highlight_step(ui)
