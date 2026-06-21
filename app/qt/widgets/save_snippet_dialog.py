"""Dialog to save Gherkin selection as a user snippet (A4-3)."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.feature_store import get_root
from app.snippet_store import UserSnippet, append_user_snippet, extract_placeholders, slugify_snippet_id


class SaveSnippetDialog(QDialog):
    def __init__(
        self,
        parent: QWidget | None,
        *,
        text: str,
        default_label: str = "",
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Сохранить как сниппет")
        self.resize(520, 360)
        self._saved_path: str | None = None

        intro = QLabel("Выделенный текст будет добавлен в библиотеку сниппетов проекта (или глобально).")
        intro.setWordWrap(True)

        self._label = QLineEdit(default_label)
        self._description = QLineEdit()
        self._preview = QPlainTextEdit(text)
        self._preview.setReadOnly(True)
        self._preview.setMaximumHeight(140)

        form = QFormLayout()
        form.addRow("Название:", self._label)
        form.addRow("Описание:", self._description)
        form.addRow("Текст:", self._preview)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_save)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(intro)
        layout.addLayout(form)
        layout.addWidget(buttons)

    @property
    def saved_path(self) -> str | None:
        return self._saved_path

    def _on_save(self) -> None:
        label = self._label.text().strip()
        text = self._preview.toPlainText().strip()
        if not label or not text:
            return
        snippet = UserSnippet(
            id=slugify_snippet_id(label),
            label=label,
            description=self._description.text().strip(),
            text=text,
            placeholders=extract_placeholders(text),
            source="project" if get_root() is not None else "global",
        )
        path = append_user_snippet(snippet, prefer_project=True)
        self._saved_path = str(path)
        self.accept()


def open_save_snippet_dialog(
    parent: QWidget | None,
    *,
    text: str,
    default_label: str = "",
) -> str | None:
    dialog = SaveSnippetDialog(parent, text=text, default_label=default_label)
    if dialog.exec() != QDialog.DialogCode.Accepted:
        return None
    return dialog.saved_path
