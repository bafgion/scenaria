"""Manage HTTP Basic Auth credentials for multiple sites."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QListWidgetItem, QMessageBox, QWidget

from app.http_auth import credentials_for_host, list_http_auth_hosts, remove_host_credentials, store_host_credentials
from app.qt.dialogs import BTN_NO, BTN_YES, alert, prompt_http_auth
from app.qt.widgets.list_manager_dialog import ListManagerDialog
from app.settings import load_settings, save_settings


class HttpAuthDialog(ListManagerDialog):
    def __init__(self, parent: QWidget | None = None, *, suggested_host: str = "") -> None:
        super().__init__(
            parent,
            title="HTTP-авторизация для сайтов",
            hint=(
                "Логины для HTTP Basic Auth (окно «Войти» в браузере).\n"
                "Можно сохранить несколько сайтов — при запуске подставляются данные для текущего URL."
            ),
            min_size=(520, 360),
        )
        self._suggested_host = suggested_host.strip().lower()

        self._list.itemDoubleClicked.connect(self._edit_selected)
        self.add_action("Добавить сайт…", self._add_site, primary=True)
        self.add_action("Изменить…", self._edit_selected)
        self.add_action("Удалить", self._delete_selected)
        self.add_close()

        self._reload_list()
        self._select_suggested_host()

    def _reload_list(self) -> None:
        settings = load_settings()
        self._list.clear()
        for host in list_http_auth_hosts(settings):
            username, _password = credentials_for_host(host, settings)
            item = QListWidgetItem(f"{host}  —  {username}")
            item.setData(Qt.ItemDataRole.UserRole, host)
            self._list.addItem(item)

        if self._list.count() == 0:
            placeholder = QListWidgetItem("Нет сохранённых сайтов")
            placeholder.setFlags(Qt.ItemFlag.NoItemFlags)
            placeholder.setForeground(Qt.GlobalColor.gray)
            self._list.addItem(placeholder)

    def _select_suggested_host(self) -> None:
        if not self._suggested_host:
            return
        for row in range(self._list.count()):
            item = self._list.item(row)
            if item is None:
                continue
            host = item.data(Qt.ItemDataRole.UserRole)
            if host == self._suggested_host:
                self._list.setCurrentItem(item)
                break

    def _selected_host(self) -> str | None:
        item = self._list.currentItem()
        if item is None:
            return None
        host = item.data(Qt.ItemDataRole.UserRole)
        return str(host) if host else None

    def _add_site(self) -> None:
        settings = load_settings()
        initial_host = self._suggested_host or ""
        result = prompt_http_auth(self, host=initial_host)
        if result is None:
            return
        host, username, password = result
        if not host:
            alert(self, "HTTP-авторизация", "Укажите домен сайта")
            return
        if not username.strip():
            alert(self, "HTTP-авторизация", "Укажите имя пользователя")
            return
        settings = store_host_credentials(host, username, password, settings)
        save_settings(settings)
        self._reload_list()
        self._select_host(host)

    def _edit_selected(self) -> None:
        host = self._selected_host()
        if not host:
            return
        settings = load_settings()
        username, password = credentials_for_host(host, settings)
        result = prompt_http_auth(self, host=host, username=username, password=password)
        if result is None:
            return
        new_host, username, password = result
        if not new_host:
            alert(self, "HTTP-авторизация", "Укажите домен сайта")
            return
        if host != new_host.strip().lower():
            settings = remove_host_credentials(host, settings)
        if username.strip():
            settings = store_host_credentials(new_host, username, password, settings)
        else:
            settings = remove_host_credentials(new_host, settings)
        save_settings(settings)
        self._reload_list()
        self._select_host(new_host)

    def _select_host(self, host: str) -> None:
        host = host.strip().lower()
        for row in range(self._list.count()):
            item = self._list.item(row)
            if item is not None and item.data(Qt.ItemDataRole.UserRole) == host:
                self._list.setCurrentItem(item)
                break

    def _delete_selected(self) -> None:
        host = self._selected_host()
        if not host:
            return
        box = QMessageBox(self)
        box.setWindowTitle("HTTP-авторизация")
        box.setText(f"Удалить сохранённые данные для {host}?")
        box.setIcon(QMessageBox.Icon.Question)
        yes = box.addButton(BTN_YES, QMessageBox.ButtonRole.YesRole)
        no = box.addButton(BTN_NO, QMessageBox.ButtonRole.NoRole)
        box.setDefaultButton(no)
        box.exec()
        if box.clickedButton() != yes:
            return
        settings = load_settings()
        settings = remove_host_credentials(host, settings)
        save_settings(settings)
        self._reload_list()
