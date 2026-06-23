"""Splitter and panel layout helpers for MainWindow (T7-1)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.qt.widgets.ide_splitter import HIT_SIZE
from app.settings import load_settings, save_settings

if TYPE_CHECKING:
    from app.qt.main_window import MainWindow


class MainWindowLayoutMixin:
    def _on_side_splitter_moved(self: MainWindow, _pos: int, _index: int) -> None:
        sizes = self._side_splitter.sizes()
        if sizes and sizes[0] > 0:
            self._sidebar_width = sizes[0]

    def _toggle_explorer(self: MainWindow, visible: bool) -> None:
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

    def _toggle_bottom_panel(self: MainWindow, visible: bool) -> None:
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

    def _show_bottom_panel(self: MainWindow, page: str) -> None:
        self.bottom_panel.show_page(page)
        self._toggle_bottom_panel(True)

    def _reset_layout(self: MainWindow) -> None:
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

    def _apply_toolbar_compact(self: MainWindow, enabled: bool) -> None:
        self.workspace.editor_action_bar.set_toolbar_simple_mode(enabled)
        if hasattr(self, "_act_toolbar_compact"):
            blocked = self._act_toolbar_compact.blockSignals(True)
            self._act_toolbar_compact.setChecked(enabled)
            self._act_toolbar_compact.setText(
                "Расширенная панель" if enabled else "Компактная панель"
            )
            self._act_toolbar_compact.blockSignals(blocked)

    def _on_toolbar_compact_toggled(self: MainWindow, checked: bool) -> None:
        settings = load_settings()
        settings["toolbar_compact"] = checked
        save_settings(settings)
        self._apply_toolbar_compact(checked)
