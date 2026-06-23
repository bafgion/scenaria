"""Keyboard shortcuts reference."""

from __future__ import annotations

from PySide6.QtWidgets import QPlainTextEdit

from app.qt.widgets.base_dialog import BaseAppDialog

HOTKEYS_TEXT = """Горячие клавиши

Сценарий
  Ctrl+N          Новый сценарий
  Ctrl+O          Открыть файл
  Ctrl+S          Сохранить

Редактор
  Ctrl+Shift+S    Обновить сценарий
  Ctrl+Space      Автодополнение шагов
  Ctrl+Shift+Space  Палитра сниппетов
  F1              Справка по шагу (в редакторе)
  Ctrl+H          Найти и заменить

Запись и тест
  Ctrl+B          Открыть браузер
  Ctrl+R          Запись
  Ctrl+Enter      Запустить сценарий
  Escape          Стоп / закрыть браузер

Панели
  Ctrl+`          Журнал / результаты

Справка
  Shift+F1        Эта шпаргалка
  F1              Справка (шаги, таблицы данных, .params.json)
"""


class HotkeysDialog(BaseAppDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent, title="Горячие клавиши", min_size=(420, 360))

        editor = QPlainTextEdit()
        editor.setProperty("role", "mono-panel")
        editor.setReadOnly(True)
        editor.setPlainText(HOTKEYS_TEXT)
        self.content_layout.addWidget(editor)

        buttons = self.add_close_box()
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)
