"""Keyboard shortcuts reference."""

from __future__ import annotations

from PySide6.QtWidgets import QDialog, QPlainTextEdit, QVBoxLayout

from app.qt.dialogs import close_button_box

HOTKEYS_TEXT = """Горячие клавиши

Файл
  Ctrl+N          Новый сценарий
  Ctrl+O          Открыть файл
  Ctrl+S          Сохранить

Редактор
  Ctrl+Shift+S    Обновить сценарий
  Ctrl+Space      Автодополнение шагов

Запуск
  Ctrl+B          Открыть браузер
  Ctrl+R          Запись
  Ctrl+Enter      Запустить сценарий
  Escape          Стоп / закрыть браузер

Панели
  Ctrl+`          Журнал / результаты

Справка
  F1              Эта шпаргалка
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
