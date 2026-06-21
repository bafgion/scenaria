"""Keyboard shortcuts reference."""

from __future__ import annotations

from PySide6.QtWidgets import QDialog, QPlainTextEdit, QVBoxLayout

from app.qt.dialogs import close_button_box

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
  F1              Каталог шагов (Справка → Шаги…)
"""


class HotkeysDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Горячие клавиши")
        self.resize(420, 360)

        layout = QVBoxLayout(self)
        editor = QPlainTextEdit()
        editor.setReadOnly(True)
        editor.setPlainText(HOTKEYS_TEXT)
        layout.addWidget(editor)

        buttons = close_button_box()
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)
