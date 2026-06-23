"""Manage saved TestClient profiles (cookies / localStorage)."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QListWidgetItem, QMessageBox, QWidget

from app.feature_store import get_root
from app.qt.dialogs import BTN_NO, BTN_YES, alert, prompt_text
from app.qt.file_dialogs import JSON_FILTER, pick_open_file, pick_save_file
from app.qt.widgets.list_manager_dialog import ListManagerDialog
from app.test_clients import (
    export_test_client,
    import_test_client,
    list_test_clients,
    remove_test_client,
)


class BrowserSessionDialog(ListManagerDialog):
    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        suggested_name: str = "",
        save_callback=None,
    ) -> None:
        super().__init__(
            parent,
            title="TestClient",
            hint=(
                "Именованные профили браузера (cookies и localStorage).\n"
                "Войдите вручную, сохраните TestClient, затем укажите его в блоке «Контекст» сценария."
            ),
        )
        self._save_callback = save_callback
        self._suggested_name = suggested_name.strip()

        self._list.itemDoubleClicked.connect(self._export_selected)
        self.add_action("Сохранить текущий TestClient…", self._save_current, primary=True)
        self.add_action("Импорт…", self._import_client)
        self.add_action("Экспорт…", self._export_selected)
        self.add_action("Удалить", self._delete_selected)
        self.add_close()

        self._reload_list()
        self._select_suggested_name()

    def _project_root(self) -> Path | None:
        return get_root()

    def _reload_list(self) -> None:
        self._list.clear()
        for item in list_test_clients(self._project_root()):
            label = item.name
            if item.label and item.label != item.name:
                label = f"{item.name} — {item.label}"
            if item.saved_at:
                label = f"{label} ({item.saved_at[:10]})"
            widget_item = QListWidgetItem(label)
            widget_item.setData(Qt.ItemDataRole.UserRole, item.name)
            self._list.addItem(widget_item)

    def _select_suggested_name(self) -> None:
        if not self._suggested_name:
            return
        for index in range(self._list.count()):
            item = self._list.item(index)
            if item and item.data(Qt.ItemDataRole.UserRole) == self._suggested_name:
                self._list.setCurrentItem(item)
                return

    def _selected_name(self) -> str | None:
        item = self._list.currentItem()
        if item is None:
            return None
        return str(item.data(Qt.ItemDataRole.UserRole) or "")

    def _save_current(self) -> None:
        if self._save_callback is None:
            alert(self, "TestClient", "Сначала откройте браузер.")
            return
        default_name = self._suggested_name or self._selected_name() or ""
        name = prompt_text(
            self,
            "Сохранить TestClient",
            "Имя TestClient (как в блоке «Контекст» сценария):",
            default_name,
        )
        if not name:
            return
        try:
            path = self._save_callback(name.strip())
        except Exception as exc:  # noqa: BLE001
            alert(self, "TestClient", str(exc))
            return
        alert(self, "TestClient", f"Сохранено:\n{path}")
        self._reload_list()

    def _delete_selected(self) -> None:
        name = self._selected_name()
        if not name:
            alert(self, "TestClient", "Выберите TestClient в списке.")
            return
        answer = QMessageBox.question(
            self,
            "TestClient",
            f"Удалить TestClient «{name}»?",
            BTN_YES | BTN_NO,
            BTN_NO,
        )
        if answer != BTN_YES:
            return
        remove_test_client(name, self._project_root())
        self._reload_list()

    def _export_selected(self) -> None:
        name = self._selected_name()
        if not name:
            alert(self, "TestClient", "Выберите TestClient в списке.")
            return
        target = pick_save_file(
            self,
            title="Экспорт TestClient",
            filter_spec=JSON_FILTER,
            default_name=f"{name}.json",
        )
        if target is None:
            return
        try:
            export_test_client(name, target, self._project_root())
        except Exception as exc:  # noqa: BLE001
            alert(self, "TestClient", str(exc))
            return
        alert(self, "TestClient", f"Экспортировано:\n{target}")

    def _import_client(self) -> None:
        source = pick_open_file(self, title="Импорт TestClient", filter_spec=JSON_FILTER)
        if source is None:
            return
        try:
            path = import_test_client(source, self._project_root())
        except Exception as exc:  # noqa: BLE001
            alert(self, "TestClient", str(exc))
            return
        alert(self, "TestClient", f"Импортировано:\n{path}")
        self._reload_list()
