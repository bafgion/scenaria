"""Replace text across multiple `.feature` files."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QRadioButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.project_replace import (
    FileReplacePreview,
    apply_files_replace,
    collect_replaceable_paths,
    preview_files_replace,
)
from app.qt.dialogs import BTN_CLOSE
from app.qt.labels import muted_label
from app.qt.widgets.base_dialog import BaseAppDialog, dialog_action_button


class ProjectReplaceDialog(BaseAppDialog):
    _SCOPE_CURRENT = 0
    _SCOPE_OPEN = 1
    _SCOPE_PROJECT = 2

    def __init__(
        self,
        parent: QWidget | None,
        *,
        current_path: Path | None,
        open_paths: list[Path],
        project_root: Path | None,
        dirty_paths: set[Path] | None = None,
        on_applied=None,
    ) -> None:
        super().__init__(parent, title="Замена по проекту", min_size=(560, 420))
        self._current_path = current_path.resolve() if current_path else None
        self._open_paths = [path.resolve() for path in open_paths if path is not None]
        self._project_root = project_root.resolve() if project_root else None
        self._dirty_paths = {path.resolve() for path in (dirty_paths or set())}
        self._on_applied = on_applied
        self._previews: list[FileReplacePreview] = []

        form = QFormLayout()
        self._find = QLineEdit()
        self._find.setClearButtonEnabled(True)
        self._find.textChanged.connect(self._refresh_preview)
        form.addRow("Найти:", self._find)

        self._replace = QLineEdit()
        self._replace.setClearButtonEnabled(True)
        form.addRow("Заменить на:", self._replace)
        self.content_layout.addLayout(form)

        self._case = QCheckBox("Учитывать регистр")
        self._case.toggled.connect(self._refresh_preview)
        self._steps_only = QCheckBox("Только в шагах")
        self._steps_only.setChecked(True)
        self._steps_only.toggled.connect(self._refresh_preview)
        self.content_layout.addWidget(self._case)
        self.content_layout.addWidget(self._steps_only)

        scope_box = QVBoxLayout()
        scope_label = QLabel("Область:")
        scope_box.addWidget(scope_label)
        self._scope_group = QButtonGroup(self)
        self._scope_current = QRadioButton("Текущий файл")
        self._scope_open = QRadioButton("Все открытые вкладки")
        self._scope_project = QRadioButton("Весь проект")
        self._scope_group.addButton(self._scope_current, self._SCOPE_CURRENT)
        self._scope_group.addButton(self._scope_open, self._SCOPE_OPEN)
        self._scope_group.addButton(self._scope_project, self._SCOPE_PROJECT)
        scope_box.addWidget(self._scope_current)
        scope_box.addWidget(self._scope_open)
        scope_box.addWidget(self._scope_project)
        self.content_layout.addLayout(scope_box)

        if self._project_root is None:
            self._scope_project.setEnabled(False)
            if not self._scope_open.isChecked() and not self._scope_current.isChecked():
                self._scope_current.setChecked(True)
        self._scope_current.toggled.connect(self._refresh_preview)
        self._scope_open.toggled.connect(self._refresh_preview)
        self._scope_project.toggled.connect(self._refresh_preview)

        self._summary = muted_label("")
        self.content_layout.addWidget(self._summary)

        self._table = QTableWidget(0, 3, self)
        self._table.setHorizontalHeaderLabels(["Файл", "Вхождений", "Статус"])
        self._table.verticalHeader().setVisible(False)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.content_layout.addWidget(self._table)

        preview_btn = dialog_action_button("Обновить preview")
        preview_btn.clicked.connect(self._refresh_preview)
        self._apply_btn = dialog_action_button("Заменить", primary=True)
        self._apply_btn.clicked.connect(self._apply)
        close_btn = dialog_action_button(BTN_CLOSE)
        close_btn.clicked.connect(self.reject)
        self.add_button_row(preview_btn, self._apply_btn, close_btn)
        self._refresh_preview()

    def _scope_paths(self) -> list[Path]:
        scope = self._scope_group.checkedId()
        if scope == self._SCOPE_CURRENT and self._current_path is not None:
            return [self._current_path]
        if scope == self._SCOPE_OPEN:
            return list(self._open_paths)
        return collect_replaceable_paths(
            current_path=None,
            open_paths=[],
            project_root=self._project_root,
        )

    def _refresh_preview(self) -> None:
        needle = self._find.text()
        paths = self._scope_paths()
        self._previews = preview_files_replace(
            paths,
            needle,
            self._replace.text(),
            case_sensitive=self._case.isChecked(),
            steps_only=self._steps_only.isChecked(),
            skip_paths=self._dirty_paths,
        )
        applicable = [item for item in self._previews if not item.skipped and item.match_count]
        skipped = [item for item in self._previews if item.skipped]
        total_matches = sum(item.match_count for item in applicable)
        self._summary.setText(
            f"Файлов: {len(applicable)}, вхождений: {total_matches}"
            + (f", пропущено: {len(skipped)}" if skipped else "")
        )
        rows = applicable + skipped
        self._table.setRowCount(len(rows))
        for index, item in enumerate(rows):
            self._table.setItem(index, 0, QTableWidgetItem(item.path.name))
            self._table.setItem(
                index,
                1,
                QTableWidgetItem(str(item.match_count) if not item.skipped else "—"),
            )
            status = "готов" if not item.skipped else item.skip_reason
            self._table.setItem(index, 2, QTableWidgetItem(status))
        self._apply_btn.setEnabled(bool(applicable) and bool(needle))

    def _apply(self) -> None:
        applicable = [item for item in self._previews if not item.skipped and item.match_count]
        if not applicable:
            return
        answer = QMessageBox.question(
            self,
            "Подтверждение",
            f"Заменить {sum(item.match_count for item in applicable)} вхождений "
            f"в {len(applicable)} файлах?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        changed = apply_files_replace(
            [item.path for item in applicable],
            self._find.text(),
            self._replace.text(),
            case_sensitive=self._case.isChecked(),
            steps_only=self._steps_only.isChecked(),
            skip_paths=self._dirty_paths,
        )
        if self._on_applied:
            self._on_applied(changed)
        self.accept()


def open_project_replace_dialog(
    parent: QWidget | None,
    *,
    current_path: Path | None,
    open_paths: list[Path],
    project_root: Path | None,
    dirty_paths: set[Path] | None = None,
    on_applied=None,
) -> None:
    dialog = ProjectReplaceDialog(
        parent,
        current_path=current_path,
        open_paths=open_paths,
        project_root=project_root,
        dirty_paths=dirty_paths,
        on_applied=on_applied,
    )
    dialog.setWindowModality(Qt.WindowModality.WindowModal)
    dialog.exec()
