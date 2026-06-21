"""Editor toolbar row: actions + run target (PyCharm style) + URL + next step."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QSize, Signal
from PySide6.QtGui import QFontMetrics
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QLineEdit, QSizePolicy, QToolButton, QWidget

from app.qt import icons
from app.qt.theme import COLOR_MUTED, COLOR_PRIMARY, COLOR_TEXT, COLOR_WARNING
from app.qt.widgets.quick_toolbar import QuickToolBar


class EditorActionBar(QWidget):
    """Window-level action bar: toolbar icons, active scenario, URL, workflow hint."""

    url_edit_requested = Signal()
    url_changed = Signal(str)
    fetch_url_from_tab_requested = Signal()
    next_step_clicked = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setProperty("role", "editor-action-bar")
        self.setMinimumHeight(56)
        self.setMinimumWidth(0)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.toolbar = QuickToolBar(self)
        root.addWidget(self.toolbar, 0, Qt.AlignmentFlag.AlignVCenter)

        root.addWidget(self._separator())

        run_box = QWidget()
        self._run_box = run_box
        run_box.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Preferred)
        run_layout = QHBoxLayout(run_box)
        run_layout.setContentsMargins(8, 0, 8, 0)
        run_layout.setSpacing(6)
        run_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        run_caption = QLabel("Сценарий")
        run_caption.setStyleSheet(f"color: {COLOR_MUTED}; font-size: 8pt;")
        run_layout.addWidget(run_caption, 0, Qt.AlignmentFlag.AlignVCenter)

        self._file_icon = QLabel()
        self._file_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._file_icon.setPixmap(icons.scenario_file_icon(size=16).pixmap(16, 16))
        self._file_icon.setFixedSize(16, 16)
        run_layout.addWidget(self._file_icon, 0, Qt.AlignmentFlag.AlignVCenter)

        self._file_name = QLabel("—")
        self._file_name.setStyleSheet(f"color: {COLOR_TEXT}; font-size: 9pt; font-weight: 600;")
        self._file_name.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        run_layout.addWidget(self._file_name, 0, Qt.AlignmentFlag.AlignVCenter)

        self._file_hint = QLabel("")
        self._file_hint.setStyleSheet(f"color: {COLOR_MUTED}; font-size: 8pt;")
        run_layout.addWidget(self._file_hint, 0, Qt.AlignmentFlag.AlignVCenter)

        run_layout.addStretch(0)
        root.addWidget(run_box, 0)

        root.addWidget(self._separator())

        url_box = QWidget()
        self._url_box = url_box
        url_box.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred)
        url_layout = QHBoxLayout(url_box)
        url_layout.setContentsMargins(4, 0, 4, 0)
        url_layout.setSpacing(4)
        url_layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        url_caption = QLabel("URL")
        url_caption.setStyleSheet(f"color: {COLOR_MUTED}; font-size: 8pt;")
        url_layout.addWidget(url_caption)

        self._url_edit = QLineEdit()
        self._url_edit.setPlaceholderText("https://site.com")
        self._url_edit.setFixedWidth(260)
        self._url_edit.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self._url_edit.returnPressed.connect(self._commit_url)
        url_layout.addWidget(self._url_edit)

        url_from_tab = QToolButton()
        url_from_tab.setText("↗")
        url_from_tab.setToolTip("URL из вкладки браузера")
        url_from_tab.setProperty("compact-icon", True)
        url_from_tab.setAutoRaise(True)
        url_from_tab.clicked.connect(self.fetch_url_from_tab_requested.emit)
        url_layout.addWidget(url_from_tab)

        root.addWidget(url_box, 0)

        root.addWidget(self._separator())

        self._next_step = QToolButton()
        self._next_step.setProperty("workflow-next", True)
        self._next_step.setAutoRaise(True)
        self._next_step.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
        self._next_step.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        self._set_next_step_label("Далее: Браузер", f"color: {COLOR_PRIMARY}; font-size: 8pt;")
        self._next_step.clicked.connect(self._on_next_step)
        root.addWidget(self._next_step, 0)

        self._next_action = "browser"
        self._density_chrome_width = 0
        self._user_simple_toolbar = False
        self._reserve_chrome_layout()
        self._sync_toolbar_density()

    def set_toolbar_simple_mode(self, enabled: bool) -> None:
        self._user_simple_toolbar = enabled
        self._sync_toolbar_density()

    def is_toolbar_simple_mode(self) -> bool:
        return self._user_simple_toolbar

    def _reserve_chrome_layout(self) -> None:
        """Keep right-side chrome width stable when labels change."""
        hint_metrics = QFontMetrics(self._file_hint.font())
        self._file_hint.setFixedWidth(hint_metrics.horizontalAdvance("не сохранён") + 8)

        next_font = self._next_step.font()
        next_font.setPointSize(8)
        next_metrics = QFontMetrics(next_font)
        next_labels = (
            "Откройте сценарий",
            "Далее: Сохранить",
            "Исправьте сценарий",
            "Далее: Запустить",
            "Далее: Браузер",
            "Далее: Запись",
            "Ожидание…",
            "Идёт запись…",
        )
        next_width = max(next_metrics.horizontalAdvance(label) + 20 for label in next_labels)
        self._next_step.setFixedWidth(next_width)

    def minimumSizeHint(self) -> QSize:  # noqa: N802
        hint = super().minimumSizeHint()
        return QSize(self._minimum_width(compact_toolbar=True), hint.height())

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        self._sync_toolbar_density()

    def _measured_chrome_width(self) -> int:
        return (
            self._run_box.sizeHint().width()
            + self._url_box.sizeHint().width()
            + self._next_step.width()
            + 20
        )

    def _fixed_chrome_width(self) -> int:
        measured = self._measured_chrome_width()
        self._density_chrome_width = max(self._density_chrome_width, measured)
        return self._density_chrome_width

    def _minimum_width(self, *, compact_toolbar: bool) -> int:
        toolbar = self.toolbar
        if self._user_simple_toolbar:
            toolbar_w = toolbar.simple_layout_min_width()
        elif compact_toolbar:
            toolbar_w = toolbar.compact_layout_min_width()
        else:
            toolbar_w = toolbar.full_layout_min_width()
        return self._measured_chrome_width() + toolbar_w

    def _sync_toolbar_density(self) -> None:
        if self.width() <= 0:
            return
        if self._user_simple_toolbar:
            self.toolbar.set_simple_mode(True)
            self.toolbar.set_auto_compact(False)
            return
        self.toolbar.set_simple_mode(False)
        available = self.width() - self._fixed_chrome_width()
        self.toolbar.set_auto_compact(available < self.toolbar.full_layout_min_width())

    def _separator(self) -> QFrame:
        line = QFrame()
        line.setFrameShape(QFrame.Shape.VLine)
        line.setProperty("role", "v-divider")
        line.setFixedWidth(1)
        return line

    def _set_next_step_label(self, text: str, style: str) -> None:
        self._next_step.setText(text)
        self._next_step.setStyleSheet(style)

    def _on_next_step(self) -> None:
        self.next_step_clicked.emit(self._next_action)

    def _commit_url(self) -> None:
        self.url_changed.emit(self._url_edit.text().strip())

    def set_run_target(
        self,
        *,
        title: str,
        path: Path | None,
        unapplied: bool,
        unsaved: bool,
        is_welcome: bool = False,
        tags: list[str] | None = None,
    ) -> None:
        badges = ""
        if unapplied:
            badges += " ●"
        if unsaved:
            badges += " *"
        self._file_name.setText(f"{title}{badges}")
        if is_welcome:
            self._file_hint.setText("")
            self._file_name.setToolTip("Стартовая страница")
        elif path is not None:
            tags = " ".join(f"@{tag}" for tag in (tags or ()))
            self._file_hint.setText(tags)
            self._file_name.setToolTip(str(path))
        else:
            self._file_hint.setText("не сохранён")
            self._file_name.setToolTip("Файл ещё не сохранён на диск")

    def set_url(self, url: str) -> None:
        blocked = self._url_edit.blockSignals(True)
        self._url_edit.setText(url)
        self._url_edit.blockSignals(blocked)

    def set_editor_fields_enabled(self, enabled: bool) -> None:
        self._url_edit.setEnabled(enabled)
        for child in self._url_box.findChildren(QToolButton):
            child.setEnabled(enabled)

    def sync_workflow(
        self,
        *,
        pending: bool,
        browser_open: bool,
        recording: bool,
        playing: bool,
        has_steps: bool,
        unapplied: bool,
        file_unsaved: bool,
        editor_active: bool = True,
    ) -> None:
        self.set_editor_fields_enabled(editor_active)
        self._next_step.setEnabled(not pending and not playing and editor_active)

        if not editor_active:
            self._next_action = ""
            self._set_next_step_label("Откройте сценарий", f"color: {COLOR_MUTED}; font-size: 8pt;")
            return

        if pending or playing:
            self._next_action = ""
            self._set_next_step_label("Ожидание…", f"color: {COLOR_MUTED}; font-size: 8pt;")
            return

        if not browser_open:
            self._next_action = "browser"
            self._set_next_step_label("Далее: Браузер", f"color: {COLOR_PRIMARY}; font-size: 8pt;")
            return

        if recording:
            self._next_action = ""
            self._next_step.setEnabled(False)
            self._set_next_step_label("Идёт запись…", "color: #f48771; font-size: 8pt;")
            return

        self._next_step.setEnabled(True)

        if unapplied:
            self._next_action = ""
            self._next_step.setEnabled(False)
            self._set_next_step_label("Исправьте сценарий", f"color: {COLOR_WARNING}; font-size: 8pt;")
            return

        if not has_steps:
            self._next_action = "record"
            self._set_next_step_label("Далее: Запись", f"color: {COLOR_PRIMARY}; font-size: 8pt;")
            return

        if file_unsaved:
            self._next_action = "save"
            self._set_next_step_label("Далее: Сохранить", f"color: {COLOR_TEXT}; font-size: 8pt;")
            return

        self._next_action = "play"
        self._set_next_step_label("Далее: Запустить", f"color: {COLOR_PRIMARY}; font-size: 8pt;")
