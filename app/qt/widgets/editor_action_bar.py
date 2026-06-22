"""Editor toolbar row: actions + run target (PyCharm style) + URL."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QSize, Signal
from PySide6.QtGui import QFontMetrics
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QLineEdit, QSizePolicy, QToolButton, QWidget

from app.qt import icons
from app.qt.theme import COLOR_MUTED, COLOR_TEXT
from app.qt.widgets.quick_toolbar import QuickToolBar


class EditorActionBar(QWidget):
    """Window-level action bar: toolbar icons, active scenario, URL."""

    url_edit_requested = Signal()
    url_changed = Signal(str)
    fetch_url_from_tab_requested = Signal()

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

        self._toolbar_sep = self._separator()
        root.addWidget(self._toolbar_sep, 0, Qt.AlignmentFlag.AlignVCenter)

        run_box = QWidget()
        self._run_box = run_box
        run_box.setProperty("role", "scenario-chip")
        run_box.setFixedHeight(22)
        run_box.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)
        run_layout = QHBoxLayout(run_box)
        run_layout.setContentsMargins(8, 0, 8, 0)
        run_layout.setSpacing(5)
        run_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        self._file_icon = QLabel()
        self._file_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._file_icon.setPixmap(icons.scenario_file_icon(size=12).pixmap(12, 12))
        self._file_icon.setFixedSize(12, 12)
        self._file_icon.setToolTip("Текущий сценарий")
        run_layout.addWidget(self._file_icon, 0, Qt.AlignmentFlag.AlignVCenter)

        self._file_name = QLabel("—")
        self._file_name.setStyleSheet(f"color: {COLOR_TEXT}; font-size: 8pt;")
        self._file_name.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        run_layout.addWidget(self._file_name, 0, Qt.AlignmentFlag.AlignVCenter)

        self._file_hint = QLabel("")
        self._file_hint.setStyleSheet(f"color: {COLOR_MUTED}; font-size: 8pt;")
        run_layout.addWidget(self._file_hint, 0, Qt.AlignmentFlag.AlignVCenter)

        root.addWidget(run_box, 0, Qt.AlignmentFlag.AlignVCenter)

        self._url_sep = self._separator()
        root.addWidget(self._url_sep, 0, Qt.AlignmentFlag.AlignVCenter)

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

        root.addWidget(url_box, 0, Qt.AlignmentFlag.AlignVCenter)

        self._density_chrome_width = 0
        self._user_simple_toolbar = False
        self._file_title = "—"
        self._file_badges = ""
        self._set_scenario_chip_visible(False)
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
        self._file_hint.setFixedWidth(hint_metrics.horizontalAdvance("не сохранён") + 4)
        name_metrics = QFontMetrics(self._file_name.font())
        self._file_name.setFixedWidth(name_metrics.horizontalAdvance("длинное_имя_сценария.feature") + 2)

    def minimumSizeHint(self) -> QSize:  # noqa: N802
        hint = super().minimumSizeHint()
        return QSize(self._minimum_width(compact_toolbar=True), hint.height())

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        self._refresh_file_name()
        self._sync_toolbar_density()

    def _measured_chrome_width(self) -> int:
        chrome = self._url_box.sizeHint().width() + 10
        if self._run_box.isVisible():
            chrome += self._run_box.sizeHint().width() + 30
        return chrome

    def _set_scenario_chip_visible(self, visible: bool) -> None:
        self._run_box.setVisible(visible)
        self._toolbar_sep.setVisible(True)
        self._url_sep.setVisible(visible)
        self._sync_toolbar_density()

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
        line.setFrameShape(QFrame.Shape.NoFrame)
        line.setProperty("role", "v-divider")
        line.setFixedWidth(1)
        line.setFixedHeight(32)
        return line

    def _commit_url(self) -> None:
        self.url_changed.emit(self._url_edit.text().strip())

    def _refresh_file_name(self) -> None:
        metrics = QFontMetrics(self._file_name.font())
        text = f"{self._file_title}{self._file_badges}"
        width = max(40, self._file_name.width())
        self._file_name.setText(metrics.elidedText(text, Qt.TextElideMode.ElideMiddle, width))

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
        show_chip = not is_welcome and title != "—"
        self._set_scenario_chip_visible(show_chip)
        if not show_chip:
            return

        badges = ""
        if unapplied:
            badges += " ●"
        if unsaved:
            badges += " *"
        self._file_title = title
        self._file_badges = badges
        self._refresh_file_name()
        if path is not None:
            tags_text = " ".join(f"@{tag}" for tag in (tags or ()))
            self._file_hint.setText(tags_text)
            self._file_hint.setVisible(bool(tags_text))
            self._file_name.setToolTip(str(path))
        else:
            self._file_hint.setText("не сохранён")
            self._file_hint.setVisible(True)
            self._file_name.setToolTip("Файл ещё не сохранён на диск")

    def set_url(self, url: str) -> None:
        blocked = self._url_edit.blockSignals(True)
        self._url_edit.setText(url)
        self._url_edit.blockSignals(blocked)

    def set_editor_fields_enabled(self, enabled: bool) -> None:
        self._url_edit.setEnabled(enabled)
        for child in self._url_box.findChildren(QToolButton):
            child.setEnabled(enabled)
