"""Dialog to configure a Vanessa batch run."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from PySide6.QtWidgets import QCheckBox, QDialog, QFormLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QVBoxLayout, QWidget

from app.qt.dialogs import BTN_CANCEL, BTN_OK


@dataclass
class VanessaRunOptions:
    paths: list[Path] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    exclude_tags: list[str] = field(default_factory=list)
    report_junit: bool = True
    report_allure: bool = False


class VanessaRunDialog(QDialog):
    def __init__(
        self,
        parent: QWidget | None,
        *,
        project_root: Path | None,
        selected_paths: list[Path] | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Прогон Vanessa")
        self.setMinimumWidth(480)
        self._project_root = project_root
        self._selected_paths = list(selected_paths or [])
        self._tags = QLineEdit()
        self._exclude = QLineEdit()
        self._report_junit = QCheckBox("JUnit")
        self._report_junit.setChecked(True)
        self._report_allure = QCheckBox("Allure")
        from scenaria_vanessa.settings import load_vanessa_settings

        settings = load_vanessa_settings()
        self._report_allure.setChecked(bool(settings.get("report_allure", False)))
        self._preview = QLabel("")
        self._preview.setWordWrap(True)

        root = QVBoxLayout(self)
        form = QFormLayout()
        scope = "выбранные сценарии" if self._selected_paths else "весь проект"
        form.addRow("Область", QLabel(scope))
        form.addRow("Теги (include)", self._tags)
        form.addRow("Теги (exclude)", self._exclude)
        form.addRow("Отчёты", self._report_row())
        root.addLayout(form)
        root.addWidget(self._preview)
        self._update_preview()

        buttons = QHBoxLayout()
        preview_btn = QPushButton("Preview VAParams")
        preview_btn.clicked.connect(self._update_preview)
        buttons.addWidget(preview_btn)
        buttons.addStretch()
        ok_btn = QPushButton(BTN_OK)
        ok_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton(BTN_CANCEL)
        cancel_btn.clicked.connect(self.reject)
        buttons.addWidget(ok_btn)
        buttons.addWidget(cancel_btn)
        root.addLayout(buttons)

    def options(self) -> VanessaRunOptions:
        tags = [part.strip().lstrip("@") for part in self._tags.text().split(",") if part.strip()]
        exclude = [part.strip().lstrip("@") for part in self._exclude.text().split(",") if part.strip()]
        if self._selected_paths:
            paths = self._selected_paths
        elif self._project_root is not None:
            paths = [self._project_root]
        else:
            paths = []
        return VanessaRunOptions(
            paths=paths,
            tags=tags,
            exclude_tags=exclude,
            report_junit=self._report_junit.isChecked(),
            report_allure=self._report_allure.isChecked(),
        )

    def _report_row(self) -> QWidget:
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._report_junit)
        layout.addWidget(self._report_allure)
        layout.addStretch()
        return row

    def _update_preview(self) -> None:
        from app.plugins.models import RunMode, RunRequest

        from scenaria_vanessa.params_merger import VAParamsMerger

        options = self.options()
        if not options.paths:
            self._preview.setText("Откройте проект или выберите сценарии.")
            return
        request = RunRequest(
            mode=RunMode.FILES,
            paths=options.paths,
            project_root=self._project_root,
            tags=options.tags,
            exclude_tags=options.exclude_tags,
            runner_options={
                "report_junit": options.report_junit,
                "report_allure": options.report_allure,
            },
        )
        try:
            _, merged, run_dir = VAParamsMerger().merge_for_request(request)
        except Exception as exc:  # noqa: BLE001
            self._preview.setText(str(exc))
            return
        keys = ", ".join(sorted(merged.keys())[:12])
        self._preview.setText(f"Каталог: {run_dir}\nКлючи overlay: {keys}")
