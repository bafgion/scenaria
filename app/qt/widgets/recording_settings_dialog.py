"""Recording and selector strategy preferences."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from app.browser_config import BROWSER_ENGINE_LABELS, BROWSER_ENGINES, normalize_browser_engine
from app.qt.dialogs import BTN_OK, ok_cancel_button_box
from app.selector_build import ALL_SELECTOR_STRATEGIES, SELECTOR_STRATEGY_LABELS, normalize_selector_priority
from app.settings import load_settings, save_settings


class RecordingSettingsDialog(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Запись и селекторы")
        self.setMinimumWidth(420)

        settings = load_settings()
        self._priority = normalize_selector_priority(settings.get("selector_priority"))

        root = QVBoxLayout(self)

        intro = QLabel(
            "Порядок стратегий при записи: сверху — предпочтительнее. "
            "Нижние пункты используются, если верхние не подходят."
        )
        intro.setWordWrap(True)
        root.addWidget(intro)

        list_row = QHBoxLayout()
        self._list = QListWidget(self)
        for key in self._priority:
            item = QListWidgetItem(SELECTOR_STRATEGY_LABELS.get(key, key))
            item.setData(Qt.ItemDataRole.UserRole, key)
            self._list.addItem(item)
        list_row.addWidget(self._list, stretch=1)

        move_col = QVBoxLayout()
        up_btn = QPushButton("↑")
        up_btn.setFixedWidth(36)
        up_btn.clicked.connect(self._move_up)
        down_btn = QPushButton("↓")
        down_btn.setFixedWidth(36)
        down_btn.clicked.connect(self._move_down)
        move_col.addWidget(up_btn)
        move_col.addWidget(down_btn)
        move_col.addStretch()
        list_row.addLayout(move_col)
        root.addLayout(list_row)

        form = QFormLayout()
        self._browser_engine = QComboBox(self)
        current_engine = normalize_browser_engine(settings.get("browser_engine"))
        for engine in BROWSER_ENGINES:
            self._browser_engine.addItem(BROWSER_ENGINE_LABELS.get(engine, engine), engine)
        index = self._browser_engine.findData(current_engine)
        if index >= 0:
            self._browser_engine.setCurrentIndex(index)
        self._browser_engine.setToolTip("Движок для записи и прогона Playwright")
        form.addRow("Браузер:", self._browser_engine)

        self._hover_min_ms = QSpinBox(self)
        self._hover_min_ms.setRange(100, 2000)
        self._hover_min_ms.setSingleStep(50)
        self._hover_min_ms.setSuffix(" мс")
        self._hover_min_ms.setValue(int(settings.get("hover_record_min_ms", 300)))
        self._hover_min_ms.setToolTip("Минимальное время наведения перед записью шага «навожу»")
        form.addRow("Пауза наведения:", self._hover_min_ms)

        self._scroll_before_click = QCheckBox("Прокручивать к элементу перед кликом")
        self._scroll_before_click.setToolTip(
            "Если элемент вне экрана, перед кликом записывается шаг «скроллю к …»"
        )
        self._scroll_before_click.setChecked(bool(settings.get("scroll_before_click")))
        form.addRow(self._scroll_before_click)

        self._open_report_after = QCheckBox("Открывать HTML-отчёт после прогона")
        self._open_report_after.setChecked(bool(settings.get("open_html_report_after_run")))
        form.addRow(self._open_report_after)
        root.addLayout(form)

        buttons = ok_cancel_button_box()
        buttons.accepted.connect(self._save_and_accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

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

    def _save_and_accept(self) -> None:
        priority: list[str] = []
        for index in range(self._list.count()):
            item = self._list.item(index)
            if item is None:
                continue
            key = item.data(Qt.ItemDataRole.UserRole)
            if key:
                priority.append(str(key))
        priority = normalize_selector_priority(priority)

        settings = load_settings()
        settings["selector_priority"] = priority
        settings["hover_record_min_ms"] = self._hover_min_ms.value()
        settings["scroll_before_click"] = self._scroll_before_click.isChecked()
        settings["open_html_report_after_run"] = self._open_report_after.isChecked()
        settings["browser_engine"] = str(self._browser_engine.currentData() or "chromium")
        save_settings(settings)
        self.accept()


def open_recording_settings_dialog(parent: QWidget | None) -> bool:
    dialog = RecordingSettingsDialog(parent)
    return dialog.exec() == QDialog.DialogCode.Accepted
