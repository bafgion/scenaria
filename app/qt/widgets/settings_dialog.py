"""Unified application settings (F6-5)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from app.brand import BRAND_NAME
from app.browser_config import BROWSER_ENGINE_LABELS, BROWSER_ENGINES, normalize_browser_engine
from app.feature_store import get_root
from app.playwright_browsers import browser_install_status, install_browser_engine
from app.plugins.registry import get_registry
from app.qt.dialogs import ok_cancel_button_box
from app.qt.theme import COLOR_MUTED, COLOR_SUCCESS, COLOR_WARNING
from app.qt.update_ui import updates_supported
from app.qt.widgets.command_palette import match_score
from app.selector_build import SELECTOR_STRATEGY_LABELS, normalize_selector_priority
from app.settings import load_settings, save_settings

SettingsTab = str  # "recording" | "selectors" | "plugins" | "updates" | "interface"

_TAB_LABELS: dict[str, str] = {
    "recording": "Запись и браузер",
    "selectors": "Селекторы",
    "plugins": "Плагины",
    "updates": "Обновления",
    "interface": "Интерфейс",
}


@dataclass
class SettingsSaveResult:
    saved: bool = False
    toolbar_compact: bool = False
    toolbar_compact_changed: bool = False
    interface_changed: bool = False
    recording_changed: bool = False


@dataclass
class _SearchTarget:
    tab: SettingsTab
    widget: QWidget
    section: QWidget | None
    text: str


def _scroll_page(content: QWidget) -> QScrollArea:
    scroll = QScrollArea()
    scroll.setProperty("role", "settings-scroll")
    scroll.setWidgetResizable(True)
    scroll.setFrameShape(QFrame.Shape.NoFrame)
    scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    scroll.setWidget(content)
    return scroll


def _section(title: str, hint: str = "") -> tuple[QWidget, QVBoxLayout]:
    block = QWidget()
    block.setProperty("role", "settings-section")
    layout = QVBoxLayout(block)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(8)
    if title:
        heading = QLabel(title)
        heading.setProperty("role", "settings-section-title")
        layout.addWidget(heading)
    if hint:
        sub = QLabel(hint)
        sub.setProperty("role", "settings-section-hint")
        sub.setWordWrap(True)
        layout.addWidget(sub)
    return block, layout


def _option_row(title: str, hint: str, control: QWidget) -> QWidget:
    row = QWidget()
    row.setProperty("role", "settings-option")
    layout = QHBoxLayout(row)
    layout.setContentsMargins(12, 10, 12, 10)
    layout.setSpacing(12)

    text_col = QVBoxLayout()
    text_col.setSpacing(2)
    title_label = QLabel(title)
    title_label.setProperty("role", "settings-option-title")
    text_col.addWidget(title_label)
    if hint:
        hint_label = QLabel(hint)
        hint_label.setProperty("role", "settings-option-hint")
        hint_label.setWordWrap(True)
        text_col.addWidget(hint_label)
    layout.addLayout(text_col, stretch=1)
    layout.addWidget(control, alignment=Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignRight)
    return row


def _checkbox_option(title: str, hint: str, *, checked: bool = False) -> tuple[QWidget, QCheckBox]:
    box = QCheckBox()
    box.setChecked(checked)
    return _option_row(title, hint, box), box


class _BrowserInstallThread(QThread):
    line = Signal(str)
    done = Signal(str)
    failed = Signal(str)

    def __init__(self, engine: str) -> None:
        super().__init__()
        self._engine = engine

    def run(self) -> None:
        try:
            path = install_browser_engine(self._engine, on_line=lambda text: self.line.emit(text))
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))
            return
        self.done.emit(str(path))


class SelectorPriorityWidget(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        settings = load_settings()
        self._priority = normalize_selector_priority(settings.get("selector_priority"))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        section, section_layout = _section(
            "Приоритет стратегий",
            "При записи Scenaria выбирает селектор по списку сверху вниз. "
            "Перетащите порядок кнопками ↑↓.",
        )
        section_layout.addLayout(self._build_list_row(), stretch=1)
        layout.addWidget(section)
        layout.addStretch()

    def _build_list_row(self) -> QHBoxLayout:
        list_row = QHBoxLayout()
        list_row.setSpacing(8)
        self._list = QListWidget(self)
        self._list.setProperty("role", "settings-list")
        self._list.setMinimumHeight(220)
        for key in self._priority:
            item = QListWidgetItem(SELECTOR_STRATEGY_LABELS.get(key, key))
            item.setData(Qt.ItemDataRole.UserRole, key)
            self._list.addItem(item)
        list_row.addWidget(self._list, stretch=1)

        move_col = QVBoxLayout()
        move_col.setSpacing(4)
        up_btn = QPushButton("↑")
        up_btn.setFixedSize(36, 28)
        up_btn.setToolTip("Выше в приоритете")
        up_btn.clicked.connect(self._move_up)
        down_btn = QPushButton("↓")
        down_btn.setFixedSize(36, 28)
        down_btn.setToolTip("Ниже в приоритете")
        down_btn.clicked.connect(self._move_down)
        move_col.addWidget(up_btn)
        move_col.addWidget(down_btn)
        move_col.addStretch()
        list_row.addLayout(move_col)
        return list_row

    def priority(self) -> list[str]:
        keys: list[str] = []
        for index in range(self._list.count()):
            item = self._list.item(index)
            if item is None:
                continue
            key = item.data(Qt.ItemDataRole.UserRole)
            if key:
                keys.append(str(key))
        return normalize_selector_priority(keys)

    def _move_up(self) -> None:
        row = self._list.currentRow()
        if row <= 0:
            return
        item = self._list.takeItem(row)
        self._list.insertItem(row - 1, item)
        self._list.setCurrentRow(row - 1)

    def _move_down(self) -> None:
        row = self._list.currentRow()
        if row < 0 or row >= self._list.count() - 1:
            return
        item = self._list.takeItem(row)
        self._list.insertItem(row + 1, item)
        self._list.setCurrentRow(row + 1)


class SettingsDialog(QDialog):
    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        initial_tab: SettingsTab = "interface",
        on_vanessa_settings: Callable[[], None] | None = None,
    ) -> None:
        super().__init__(parent)
        self.setProperty("role", "settings-dialog")
        self.setWindowTitle(f"Настройки — {BRAND_NAME}")
        self.setMinimumSize(560, 460)
        self.resize(600, 500)
        self._on_vanessa_settings = on_vanessa_settings
        self._initial_toolbar_compact = bool(load_settings().get("toolbar_compact"))
        self._initial_steps_height = int(load_settings().get("steps_panel_height", 160))
        self._initial_steps_visible = bool(load_settings().get("steps_panel_visible", True))
        self._search_targets: list[_SearchTarget] = []
        self._sections: list[QWidget] = []
        self._browser_install_thread: _BrowserInstallThread | None = None

        settings = load_settings()
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        search_header = QWidget(self)
        search_header.setProperty("role", "settings-search-header")
        search_layout = QHBoxLayout(search_header)
        search_layout.setContentsMargins(12, 10, 12, 8)
        self._search_edit = QLineEdit(search_header)
        self._search_edit.setPlaceholderText("Поиск настроек")
        self._search_edit.setClearButtonEnabled(True)
        self._search_edit.textChanged.connect(self._apply_search)
        search_layout.addWidget(self._search_edit)
        root.addWidget(search_header)

        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)

        self._nav = QListWidget(self)
        self._nav.setProperty("role", "settings-nav")
        self._nav.setFixedWidth(156)
        self._nav.setSpacing(2)
        self._nav.currentRowChanged.connect(self._on_nav_changed)

        self._stack = QStackedWidget(self)
        self._stack.setProperty("role", "settings-content")

        self._tab_keys: list[SettingsTab] = []
        self._add_page("recording", self._build_recording_tab(settings))
        self._selector_priority = SelectorPriorityWidget(self)
        self._add_page("selectors", _scroll_page(self._selector_priority))
        self._track(
            "selectors",
            self._selector_priority,
            None,
            _TAB_LABELS["selectors"],
            "приоритет селекторов",
            "testid aria css text chain",
            *SELECTOR_STRATEGY_LABELS.values(),
        )
        self._add_page("plugins", _scroll_page(self._build_plugins_tab()))
        if updates_supported():
            self._updates_tab = self._build_updates_tab(settings)
            self._add_page("updates", _scroll_page(self._updates_tab))
        else:
            self._updates_tab = None
        self._add_page("interface", _scroll_page(self._build_interface_tab(settings)))

        body.addWidget(self._nav)
        divider = QFrame()
        divider.setFrameShape(QFrame.Shape.NoFrame)
        divider.setProperty("role", "settings-nav-divider")
        divider.setFixedWidth(1)
        body.addWidget(divider)

        content_wrap = QWidget(self)
        content_layout = QVBoxLayout(content_wrap)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)
        content_layout.addWidget(self._stack, stretch=1)
        self._no_results = QLabel("Ничего не найдено")
        self._no_results.setProperty("role", "settings-empty-search")
        self._no_results.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._no_results.hide()
        content_layout.addWidget(self._no_results, stretch=1)
        body.addWidget(content_wrap, stretch=1)
        root.addLayout(body, stretch=1)

        footer_line = QFrame()
        footer_line.setFrameShape(QFrame.Shape.NoFrame)
        footer_line.setProperty("role", "settings-footer-line")
        footer_line.setFixedHeight(1)
        root.addWidget(footer_line)

        footer = QWidget()
        footer.setProperty("role", "settings-footer")
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(16, 10, 16, 12)
        buttons = ok_cancel_button_box()
        buttons.accepted.connect(self._save_and_accept)
        buttons.rejected.connect(self.reject)
        footer_layout.addStretch()
        footer_layout.addWidget(buttons)
        root.addWidget(footer)

        initial_index = self._tab_keys.index(initial_tab) if initial_tab in self._tab_keys else 0
        self._nav.setCurrentRow(initial_index)

    def _add_page(self, key: SettingsTab, widget: QWidget) -> None:
        label = _TAB_LABELS[key]
        self._tab_keys.append(key)
        self._stack.addWidget(widget)
        item = QListWidgetItem(label)
        item.setData(Qt.ItemDataRole.UserRole, key)
        self._nav.addItem(item)

    def _on_nav_changed(self, row: int) -> None:
        if row >= 0:
            self._stack.setCurrentIndex(row)
            if self._search_edit.text().strip():
                self._stack.setVisible(True)
                self._no_results.hide()

    def _track(
        self,
        tab: SettingsTab,
        widget: QWidget,
        section: QWidget | None,
        *keywords: str,
    ) -> None:
        text = " ".join(str(part) for part in keywords if part)
        self._search_targets.append(_SearchTarget(tab, widget, section, text))
        if section is not None and section not in self._sections:
            self._sections.append(section)

    def _apply_search(self, query: str) -> None:
        needle = query.strip()
        if not needle:
            for target in self._search_targets:
                target.widget.setVisible(True)
            for section in self._sections:
                section.setVisible(True)
            for index in range(self._nav.count()):
                self._nav.item(index).setHidden(False)
            self._stack.setVisible(True)
            self._no_results.hide()
            return

        tabs_with_hits: set[SettingsTab] = set()
        for target in self._search_targets:
            visible = match_score(needle, target.text) is not None
            target.widget.setVisible(visible)
            if visible:
                tabs_with_hits.add(target.tab)

        for section in self._sections:
            layout = section.layout()
            if layout is None:
                section.setVisible(True)
                continue
            any_visible = False
            for index in range(layout.count()):
                item = layout.itemAt(index)
                widget = item.widget() if item is not None else None
                if widget is not None and widget.isVisible():
                    any_visible = True
                    break
            section.setVisible(any_visible)

        for index, key in enumerate(self._tab_keys):
            item = self._nav.item(index)
            if item is not None:
                item.setHidden(key not in tabs_with_hits)

        if not tabs_with_hits:
            self._stack.hide()
            self._no_results.show()
            return

        self._no_results.hide()
        self._stack.show()
        current_row = self._nav.currentRow()
        current_key = self._tab_keys[current_row] if 0 <= current_row < len(self._tab_keys) else ""
        if current_key not in tabs_with_hits:
            first_index = next(i for i, key in enumerate(self._tab_keys) if key in tabs_with_hits)
            self._nav.setCurrentRow(first_index)

    def _build_recording_tab(self, settings: dict) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        modes_section, modes_layout = _section(
            "Режим записи",
            "Фильтры действий в браузере. «Только важные» и «Только ссылки» не сочетаются.",
        )
        row, self._filter_recording = _checkbox_option(
            "Только важные клики",
            "Пропускать второстепенные элементы при записи.",
            checked=bool(settings.get("filter_recording")),
        )
        modes_layout.addWidget(row)
        self._track(
            "recording",
            row,
            modes_section,
            "только важные клики",
            "filter запись",
            _TAB_LABELS["recording"],
        )
        row, self._nav_only_recording = _checkbox_option(
            "Только переходы по ссылкам",
            "Записывать только навигацию goto.",
            checked=bool(settings.get("nav_only_recording")),
        )
        modes_layout.addWidget(row)
        self._track(
            "recording",
            row,
            modes_section,
            "только ссылки",
            "goto навигация nav",
        )
        self._filter_recording.toggled.connect(self._on_filter_toggled)
        self._nav_only_recording.toggled.connect(self._on_nav_only_toggled)
        layout.addWidget(modes_section)

        browser_section, browser_layout = _section(
            "Браузер",
            "Поведение окна и сессии при записи и прогоне Playwright.",
        )
        row, self._headless = _checkbox_option(
            "Без окна браузера",
            "Headless-режим: браузер работает в фоне.",
            checked=bool(settings.get("headless")),
        )
        browser_layout.addWidget(row)
        self._track("recording", row, browser_section, "headless", "без окна браузера")
        row, self._saved_session = _checkbox_option(
            "Сохранённая сессия",
            "Подставлять cookies и storage для текущего URL.",
            checked=bool(settings.get("use_saved_browser_session", True)),
        )
        browser_layout.addWidget(row)
        self._track("recording", row, browser_section, "сессия", "cookies storage сохранённая")

        self._browser_engine = QComboBox()
        self._browser_engine.setMinimumWidth(160)
        current_engine = normalize_browser_engine(settings.get("browser_engine"))
        for engine in BROWSER_ENGINES:
            self._browser_engine.addItem(BROWSER_ENGINE_LABELS.get(engine, engine), engine)
        index = self._browser_engine.findData(current_engine)
        if index >= 0:
            self._browser_engine.setCurrentIndex(index)
        browser_layout.addWidget(
            _option_row("Движок браузера", "Chromium, Firefox или WebKit.", self._browser_engine)
        )
        engine_row = browser_layout.itemAt(browser_layout.count() - 1).widget()
        if engine_row is not None:
            self._track(
                "recording",
                engine_row,
                browser_section,
                "движок браузера",
                "chromium firefox webkit playwright",
            )

        install_row = QWidget()
        install_layout = QHBoxLayout(install_row)
        install_layout.setContentsMargins(12, 0, 12, 10)
        install_layout.setSpacing(8)
        self._browser_engine_status = QLabel()
        self._browser_engine_status.setWordWrap(True)
        install_layout.addWidget(self._browser_engine_status, stretch=1)
        self._browser_install_btn = QPushButton("Установить движок")
        self._browser_install_btn.clicked.connect(self._install_browser_engine)
        install_layout.addWidget(self._browser_install_btn)
        browser_layout.addWidget(install_row)
        self._track(
            "recording",
            install_row,
            browser_section,
            "установка движка",
            "playwright браузер chromium firefox webkit",
        )

        self._browser_install_progress = QLabel("")
        self._browser_install_progress.setWordWrap(True)
        self._browser_install_progress.setStyleSheet(f"color: {COLOR_MUTED};")
        self._browser_install_progress.hide()
        browser_layout.addWidget(self._browser_install_progress)

        self._browser_engine.currentIndexChanged.connect(lambda _index: self._refresh_browser_engine_status())
        self._refresh_browser_engine_status()
        layout.addWidget(browser_section)

        hover_section, hover_layout = _section("Наведение и прокрутка")
        row, self._hover_enabled = _checkbox_option(
            "Записывать наведение мыши",
            "Шаг «навожу» перед кликом по меню и подсказкам.",
            checked=bool(settings.get("hover_record_enabled")),
        )
        hover_layout.addWidget(row)
        self._track("recording", row, hover_section, "наведение", "hover навожу")
        self._hover_min_ms = QSpinBox()
        self._hover_min_ms.setRange(100, 2000)
        self._hover_min_ms.setSingleStep(50)
        self._hover_min_ms.setSuffix(" мс")
        self._hover_min_ms.setValue(int(settings.get("hover_record_min_ms", 300)))
        hover_layout.addWidget(
            _option_row("Пауза наведения", "Минимальное время hover перед записью шага.", self._hover_min_ms)
        )
        hover_delay_row = hover_layout.itemAt(hover_layout.count() - 1).widget()
        if hover_delay_row is not None:
            self._track("recording", hover_delay_row, hover_section, "пауза наведения", "hover мс")
        row, self._scroll_before_click = _checkbox_option(
            "Прокрутка перед кликом",
            "Если элемент вне экрана — шаг «скроллю к …».",
            checked=bool(settings.get("scroll_before_click")),
        )
        hover_layout.addWidget(row)
        self._track("recording", row, hover_section, "прокрутка", "scroll скролл")
        layout.addWidget(hover_section)

        reports_section, reports_layout = _section("Отчёты")
        row, self._open_report_after = _checkbox_option(
            "HTML-отчёт после прогона",
            "Автоматически открывать отчёт при успешном завершении.",
            checked=bool(settings.get("open_html_report_after_run")),
        )
        reports_layout.addWidget(row)
        self._track("recording", row, reports_section, "html отчёт", "отчёт прогон")
        layout.addWidget(reports_section)
        layout.addStretch()
        return _scroll_page(page)

    def _build_plugins_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        section, section_layout = _section(
            "Runner’ы и add-on’ы",
            "Playwright встроен. Дополнительные runner’ы устанавливаются через меню «Плагины».",
        )

        registry = get_registry()
        registry.reload(project_root=get_root())
        for info in registry.runner_infos():
            card = QWidget()
            card.setProperty("role", "settings-plugin-card")
            card_layout = QHBoxLayout(card)
            card_layout.setContentsMargins(12, 10, 12, 10)
            name = QLabel(info.label)
            name.setProperty("role", "settings-option-title")
            card_layout.addWidget(name, stretch=1)
            if info.id == "playwright":
                status = "встроен"
                color = COLOR_MUTED
            elif info.installed and info.available:
                status = "установлен"
                color = COLOR_SUCCESS
            elif info.installed:
                status = "недоступен"
                color = COLOR_WARNING
            else:
                status = "не установлен"
                color = COLOR_MUTED
            badge = QLabel(status)
            badge.setStyleSheet(f"color: {color}; font-size: 8pt;")
            card_layout.addWidget(badge)
            section_layout.addWidget(card)
            self._track("plugins", card, section, info.label, info.id, status, _TAB_LABELS["plugins"])

        self._vanessa_btn = QPushButton("Настройки Vanessa…")
        self._vanessa_btn.setEnabled(registry.get_runner("vanessa") is not None)
        self._vanessa_btn.clicked.connect(self._open_vanessa_settings)
        section_layout.addWidget(self._vanessa_btn)
        self._track("plugins", self._vanessa_btn, section, "vanessa", "1с настройки")

        hint = QLabel("Установка add-on’ов: меню «Плагины» в главном окне.")
        hint.setProperty("role", "settings-section-hint")
        hint.setWordWrap(True)
        section_layout.addWidget(hint)
        layout.addWidget(section)
        layout.addStretch()
        return page

    def _build_updates_tab(self, settings: dict) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        section, section_layout = _section(
            "Обновления",
            "Portable-сборка проверяет GitHub Releases. Ручная проверка: Справка → Проверить обновления…",
        )
        row, self._check_on_startup = _checkbox_option(
            "Проверять при запуске",
            "Один раз при старте приложения.",
            checked=bool(settings.get("check_updates_on_startup", True)),
        )
        section_layout.addWidget(row)
        self._track("updates", row, section, "обновление", "startup запуск", _TAB_LABELS["updates"])

        dismissed = str(settings.get("dismissed_update_version", "")).strip()
        self._dismissed_info = QLabel(dismissed or "—")
        self._dismissed_info.setProperty("role", "settings-option-title")
        section_layout.addWidget(
            _option_row("Пропущенная версия", "Версия, для которой нажали «Позже».", self._dismissed_info)
        )
        dismissed_row = section_layout.itemAt(section_layout.count() - 1).widget()
        if dismissed_row is not None:
            self._track("updates", dismissed_row, section, "пропущенная версия", "позже dismiss")

        clear_btn = QPushButton("Сбросить пропуск")
        clear_btn.setEnabled(bool(dismissed))
        clear_btn.clicked.connect(self._clear_dismissed_version)
        section_layout.addWidget(clear_btn, alignment=Qt.AlignmentFlag.AlignLeft)
        self._track("updates", clear_btn, section, "сбросить пропуск", "версия")
        layout.addWidget(section)
        layout.addStretch()
        return page

    def _build_interface_tab(self, settings: dict) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        toolbar_section, toolbar_layout = _section(
            "Панель инструментов",
            "Компактный режим — один ряд основных кнопок. Расширенный — в меню «Вид».",
        )
        row, self._toolbar_compact = _checkbox_option(
            "Компактная панель",
            "Меньше кнопок на панели; остальные — в меню и Command Palette.",
            checked=bool(settings.get("toolbar_compact")),
        )
        toolbar_layout.addWidget(row)
        self._track("interface", row, toolbar_section, "компактная панель", "toolbar", _TAB_LABELS["interface"])
        layout.addWidget(toolbar_section)

        steps_section, steps_layout = _section(
            "Панель шагов",
            "Список шагов под редактором Gherkin.",
        )
        row, self._steps_panel_visible = _checkbox_option(
            "Показывать панель шагов",
            "Можно свернуть вручную кнопкой ▼ на панели.",
            checked=bool(settings.get("steps_panel_visible", True)),
        )
        steps_layout.addWidget(row)
        self._track("interface", row, steps_section, "панель шагов", "показывать steps")
        self._steps_panel_height = QSpinBox()
        self._steps_panel_height.setRange(80, 480)
        self._steps_panel_height.setSingleStep(10)
        self._steps_panel_height.setSuffix(" px")
        self._steps_panel_height.setValue(int(settings.get("steps_panel_height", 160)))
        self._steps_height_row = _option_row(
            "Высота панели",
            "Применяется, когда панель развёрнута.",
            self._steps_panel_height,
        )
        steps_layout.addWidget(self._steps_height_row)
        self._track("interface", self._steps_height_row, steps_section, "высота панели", "шаги px")
        self._steps_panel_visible.toggled.connect(self._sync_steps_height_enabled)
        self._sync_steps_height_enabled()
        layout.addWidget(steps_section)
        layout.addStretch()
        return page

    def _sync_steps_height_enabled(self) -> None:
        enabled = self._steps_panel_visible.isChecked()
        self._steps_panel_height.setEnabled(enabled)
        self._steps_height_row.setEnabled(enabled)

    def _on_filter_toggled(self, checked: bool) -> None:
        if checked and self._nav_only_recording.isChecked():
            self._nav_only_recording.setChecked(False)

    def _on_nav_only_toggled(self, checked: bool) -> None:
        if checked and self._filter_recording.isChecked():
            self._filter_recording.setChecked(False)

    def _current_browser_engine(self) -> str:
        return normalize_browser_engine(str(self._browser_engine.currentData() or "chromium"))

    def _refresh_browser_engine_status(self) -> None:
        if self._browser_install_thread is not None and self._browser_install_thread.isRunning():
            return
        engine = self._current_browser_engine()
        label = BROWSER_ENGINE_LABELS.get(engine, engine)
        installed, detail = browser_install_status(engine)
        if installed:
            self._browser_engine_status.setText(f"{label}: установлен\n{detail}")
            self._browser_engine_status.setStyleSheet(f"color: {COLOR_SUCCESS};")
            self._browser_install_btn.setEnabled(True)
            self._browser_install_btn.setText("Переустановить")
        else:
            self._browser_engine_status.setText(f"{label}: не установлен — нужна загрузка перед записью и прогоном.")
            self._browser_engine_status.setStyleSheet(f"color: {COLOR_WARNING};")
            self._browser_install_btn.setEnabled(True)
            self._browser_install_btn.setText("Установить движок")
        self._browser_install_progress.hide()
        self._browser_install_progress.setText(detail if installed else "")

    def _install_browser_engine(self) -> None:
        if self._browser_install_thread is not None and self._browser_install_thread.isRunning():
            return
        engine = self._current_browser_engine()
        label = BROWSER_ENGINE_LABELS.get(engine, engine)
        self._browser_install_btn.setEnabled(False)
        self._browser_install_progress.show()
        self._browser_install_progress.setText(f"Установка {label}…")
        self._browser_install_thread = _BrowserInstallThread(engine)
        self._browser_install_thread.line.connect(self._on_browser_install_line)
        self._browser_install_thread.done.connect(self._on_browser_install_done)
        self._browser_install_thread.failed.connect(self._on_browser_install_failed)
        self._browser_install_thread.start()

    def _on_browser_install_line(self, line: str) -> None:
        self._browser_install_progress.setText(line)

    def _on_browser_install_done(self, path: str) -> None:
        self._browser_install_progress.setText(f"Готово: {path}")
        self._refresh_browser_engine_status()

    def _on_browser_install_failed(self, message: str) -> None:
        self._browser_install_progress.setText(message)
        self._browser_install_progress.setStyleSheet(f"color: {COLOR_WARNING};")
        self._refresh_browser_engine_status()

    def _open_vanessa_settings(self) -> None:
        if self._on_vanessa_settings is not None:
            self._on_vanessa_settings()

    def _clear_dismissed_version(self) -> None:
        settings = load_settings()
        settings["dismissed_update_version"] = ""
        save_settings(settings)
        self._dismissed_info.setText("—")

    def _save_and_accept(self) -> None:
        settings = load_settings()
        settings["filter_recording"] = self._filter_recording.isChecked()
        settings["nav_only_recording"] = self._nav_only_recording.isChecked()
        if settings["filter_recording"] and settings["nav_only_recording"]:
            settings["nav_only_recording"] = False
        settings["headless"] = self._headless.isChecked()
        settings["use_saved_browser_session"] = self._saved_session.isChecked()
        settings["hover_record_enabled"] = self._hover_enabled.isChecked()
        settings["hover_record_min_ms"] = self._hover_min_ms.value()
        settings["scroll_before_click"] = self._scroll_before_click.isChecked()
        settings["browser_engine"] = str(self._browser_engine.currentData() or "chromium")
        settings["open_html_report_after_run"] = self._open_report_after.isChecked()
        settings["selector_priority"] = self._selector_priority.priority()
        if self._updates_tab is not None:
            settings["check_updates_on_startup"] = self._check_on_startup.isChecked()
        settings["toolbar_compact"] = self._toolbar_compact.isChecked()
        settings["steps_panel_height"] = self._steps_panel_height.value()
        settings["steps_panel_visible"] = self._steps_panel_visible.isChecked()
        save_settings(settings)
        self.accept()

    def closeEvent(self, event) -> None:  # noqa: ANN001, N802
        if self._browser_install_thread is not None and self._browser_install_thread.isRunning():
            self._browser_install_thread.wait(5000)
        super().closeEvent(event)

    def save_result(self) -> SettingsSaveResult:
        settings = load_settings()
        toolbar_compact = bool(settings.get("toolbar_compact"))
        steps_height = int(settings.get("steps_panel_height", 160))
        steps_visible = bool(settings.get("steps_panel_visible", True))
        return SettingsSaveResult(
            saved=True,
            toolbar_compact=toolbar_compact,
            toolbar_compact_changed=toolbar_compact != self._initial_toolbar_compact,
            interface_changed=(
                steps_height != self._initial_steps_height
                or steps_visible != self._initial_steps_visible
            ),
            recording_changed=True,
        )


def open_settings_dialog(
    parent: QWidget | None,
    *,
    initial_tab: SettingsTab = "interface",
    on_vanessa_settings: Callable[[], None] | None = None,
) -> SettingsSaveResult:
    dialog = SettingsDialog(
        parent,
        initial_tab=initial_tab,
        on_vanessa_settings=on_vanessa_settings,
    )
    if dialog.exec() != QDialog.DialogCode.Accepted:
        return SettingsSaveResult()
    return dialog.save_result()
