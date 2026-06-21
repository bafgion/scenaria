"""Manage saved browser sessions (cookies / localStorage)."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.browser_session import (
    SavedSession,
    export_session,
    import_session,
    list_saved_sessions,
    remove_saved_session,
    session_origin,
)
from app.feature_store import get_root
from app.qt.dialogs import BTN_NO, BTN_YES, alert, prompt_text
from app.qt.file_dialogs import JSON_FILTER, pick_open_file, pick_save_file


class BrowserSessionDialog(QDialog):
    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        suggested_url: str = "",
        save_callback=None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Сессии браузера")
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        self.setMinimumSize(560, 380)
        self._save_callback = save_callback
        self._suggested_origin = session_origin(suggested_url)

        root = QVBoxLayout(self)
        root.addWidget(
            QLabel(
                "Cookies и localStorage по origin сайта.\n"
                "Войдите вручную в браузере, затем сохраните сессию — при следующем запуске логин подставится автоматически."
            )
        )

        self._list = QListWidget(self)
        self._list.itemDoubleClicked.connect(self._export_selected)
        root.addWidget(self._list, stretch=1)

        row = QHBoxLayout()
        self._save_btn = QPushButton("Сохранить текущую сессию…")
        self._save_btn.clicked.connect(self._save_current)
        row.addWidget(self._save_btn)
        import_btn = QPushButton("Импорт…")
        import_btn.clicked.connect(self._import_session)
        row.addWidget(import_btn)
        export_btn = QPushButton("Экспорт…")
        export_btn.clicked.connect(self._export_selected)
        row.addWidget(export_btn)
        delete_btn = QPushButton("Удалить")
        delete_btn.clicked.connect(self._delete_selected)
        row.addWidget(delete_btn)
        row.addStretch()
        close_btn = QPushButton("Закрыть")
        close_btn.clicked.connect(self.accept)
        row.addWidget(close_btn)
        root.addLayout(row)

        self._reload_list()
        self._select_suggested_origin()
        self._update_save_enabled()

    def _project_root(self) -> Path | None:
        return get_root()

    def _reload_list(self) -> None:
        self._list.clear()
        sessions = list_saved_sessions(self._project_root())
        for session in sessions:
            label = f"  ({session.label})" if session.label else ""
            when = session.saved_at[:19].replace("T", " ") if session.saved_at else ""
            suffix = f" — {when}" if when else ""
            item = QListWidgetItem(f"{session.origin}{label}{suffix}")
            item.setData(Qt.ItemDataRole.UserRole, session)
            self._list.addItem(item)
        if self._list.count() == 0:
            placeholder = QListWidgetItem("Нет сохранённых сессий")
            placeholder.setFlags(Qt.ItemFlag.NoItemFlags)
            placeholder.setForeground(Qt.GlobalColor.gray)
            self._list.addItem(placeholder)

    def _selected_session(self) -> SavedSession | None:
        item = self._list.currentItem()
        if item is None:
            return None
        session = item.data(Qt.ItemDataRole.UserRole)
        return session if isinstance(session, SavedSession) else None

    def _select_suggested_origin(self) -> None:
        if not self._suggested_origin:
            return
        for row in range(self._list.count()):
            item = self._list.item(row)
            session = item.data(Qt.ItemDataRole.UserRole) if item else None
            if isinstance(session, SavedSession) and session.origin == self._suggested_origin:
                self._list.setCurrentRow(row)
                return

    def _update_save_enabled(self) -> None:
        self._save_btn.setEnabled(self._save_callback is not None)

    def _save_current(self) -> None:
        if self._save_callback is None:
            alert(self, "Сессии", "Сначала откройте браузер.")
            return
        label = prompt_text(self, "Сохранить сессию", "Метка (необязательно):", initial="")
        if label is None:
            return
        self._save_callback(label.strip())

    def _delete_selected(self) -> None:
        session = self._selected_session()
        if session is None:
            return
        answer = QMessageBox.question(
            self,
            "Удалить сессию",
            f"Удалить сессию для {session.origin}?",
            BTN_YES | BTN_NO,
        )
        if answer != BTN_YES:
            return
        remove_saved_session(session.origin, self._project_root())
        self._reload_list()

    def _export_selected(self) -> None:
        session = self._selected_session()
        if session is None:
            return
        target = pick_save_file(
            self,
            title="Экспорт сессии",
            filter_spec=JSON_FILTER,
            default_name=f"session-{session.origin.replace('://', '-')}.json",
        )
        if target is None:
            return
        if target.suffix.lower() != ".json":
            target = target.with_suffix(".json")
        export_session(session.origin, target, self._project_root())
        alert(self, "Сессии", f"Экспортировано: {target}")

    def _import_session(self) -> None:
        source = pick_open_file(self, title="Импорт сессии", filter_spec=JSON_FILTER)
        if source is None:
            return
        try:
            path = import_session(source, self._project_root())
        except (OSError, ValueError) as exc:
            alert(self, "Сессии", f"Не удалось импортировать:\n{exc}")
            return
        self._reload_list()
        alert(self, "Сессии", f"Импортировано: {path.name}")

    def on_session_saved(self, path: str) -> None:
        self._reload_list()
        alert(self, "Сессии", f"Сессия сохранена:\n{path}")
