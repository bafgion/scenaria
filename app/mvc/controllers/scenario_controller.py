"""Scenario editing controller."""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

from PySide6.QtWidgets import QWidget

from app.feature_store import (
    clear_draft,
    delete_feature,
    duplicate_feature,
    get_root,
    load_feature,
    save_feature,
    save_feature_text,
)
from app.gherkin_ru import GherkinParseError, gherkin_to_steps, steps_to_gherkin
from app.mvc.models.catalog_model import CatalogModel
from app.mvc.models.scenario_model import ScenarioModel
from app.qt.dialogs import alert, confirm, prompt_text
from app.qt.file_dialogs import (
    FEATURE_FILTER,
    JSON_FILTER,
    PLAYWRIGHT_PY_FILTER,
    PLAYWRIGHT_TS_FILTER,
    ZIP_FILTER,
    pick_open_file,
    pick_save_file,
)
from app.playwright_export import ExportFormat, export_scenario_playwright
from app.scenario_io import (
    export_scenario_feature,
    export_scenario_json,
    export_scenario_zip,
    import_scenario_feature,
    import_scenario_json,
)
from app.settings import load_settings
from app.steps import normalize_steps
from app.scenario_utils import ScenarioNotFoundError, suggest_scenario_name
from app.brand import BRAND_NAME


class ScenarioController:
    def __init__(self, model: ScenarioModel, catalog: CatalogModel) -> None:
        self._model = model
        self._catalog = catalog
        self._parent: QWidget | None = None

    def set_parent_widget(self, widget: QWidget | None) -> None:
        self._parent = widget

    @property
    def model(self) -> ScenarioModel:
        return self._model

    def initialize(self) -> None:
        settings = load_settings()
        if settings.get("autosave_enabled", True):
            self._model.restore_draft_if_any()

    def load_feature(self, path: Path) -> None:
        self._model.load_from_path(path)

    def bind_feature_path(self, path: Path | None) -> None:
        self._model.bind_feature_path(path)

    def new_scenario(self) -> None:
        self._model.new_scenario()

    def set_steps(self, steps: list[dict[str, Any]]) -> None:
        self._model.set_steps(steps)

    def save_to_path(self, target: Path) -> Path:
        saved = save_feature(target, self._model.steps, scenario_name=self._model.name or target.stem)
        self._model.mark_saved(saved)
        self._model.status_message.emit(f"Сохранено: {saved.stem}", "success")
        return saved

    def commit_steps_to_gherkin(self) -> str:
        scenario_name = self._model.name.strip() or "Сценарий"
        if self._model.feature_path is not None:
            scenario_name = self._model.feature_path.stem
        text = steps_to_gherkin(self._model.steps, scenario_name=scenario_name)
        self._model.set_source_text(text)
        return text

    def collapse_duplicate_gotos(self) -> int:
        before = len(self._model.steps)
        normalized = normalize_steps(self._model.steps)
        self._model.set_steps(normalized)
        removed = before - len(normalized)
        if removed:
            self.commit_steps_to_gherkin()
        return removed

    def delete_steps(self, indices: set[int]) -> list[dict[str, Any]]:
        steps = self._model.steps
        for index in sorted(indices, reverse=True):
            if 0 <= index < len(steps):
                steps.pop(index)
        self._model.set_steps(steps)
        self.commit_steps_to_gherkin()
        return self._model.steps

    def delete_step(self, index: int) -> list[dict[str, Any]]:
        steps = self._model.steps
        if 0 <= index < len(steps):
            removed = steps.pop(index)
            self._model.set_steps(steps)
            self._model.status_message.emit(
                f"Удалён шаг {index + 1}: {removed.get('action', '')}",
                "info",
            )
            self.commit_steps_to_gherkin()
        return self._model.steps

    def move_step_up(self, index: int) -> tuple[list[dict[str, Any]], int]:
        steps = self._model.steps
        if index <= 0 or index >= len(steps):
            return steps, index
        steps[index - 1], steps[index] = steps[index], steps[index - 1]
        self._model.set_steps(steps)
        self.commit_steps_to_gherkin()
        return self._model.steps, index - 1

    def move_step_down(self, index: int) -> tuple[list[dict[str, Any]], int]:
        steps = self._model.steps
        if index < 0 or index >= len(steps) - 1:
            return steps, index
        steps[index + 1], steps[index] = steps[index], steps[index + 1]
        self._model.set_steps(steps)
        self.commit_steps_to_gherkin()
        return self._model.steps, index + 1

    def edit_step(self, parent: QWidget, index: int) -> list[dict[str, Any]] | None:
        from app.qt.widgets.step_editor_dialog import edit_step_dialog

        steps = copy.deepcopy(self._model.steps)
        if index < 0 or index >= len(steps):
            return None
        step = steps[index]
        action = step.get("action", "")
        if action in {"reload", "go_back", "close_browser"}:
            return None

        dialog_step = dict(step)
        if action == "wait":
            dialog_step["ms"] = str(step.get("ms", 1000))

        edited = edit_step_dialog(parent, dialog_step, index=index)
        if edited is None:
            return None

        if action == "wait":
            try:
                edited["ms"] = max(0, int(str(edited.get("ms", "1000")).strip()))
            except ValueError:
                return None

        steps[index] = edited
        self._model.set_steps(steps)
        self.commit_steps_to_gherkin()
        return self._model.steps

    def split_click_into_hover(self, parent: QWidget, index: int) -> list[dict[str, Any]] | None:
        steps = copy.deepcopy(self._model.steps)
        if index < 0 or index >= len(steps):
            return None
        step = steps[index]
        if step.get("action") != "click":
            return None

        guide = (
            "Укажите селектор пункта меню, на который нужно навести курсор,\n"
            "затем — селектор подпункта для клика."
        )
        hover_selector = prompt_text(
            parent,
            "Починить меню",
            f"{guide}\n\nСелектор наведения:",
            initial=str(step.get("hoverSelector", "")),
        )
        if hover_selector is None:
            return None
        hover_selector = hover_selector.strip()
        if not hover_selector:
            return None

        click_selector = prompt_text(
            parent,
            "Починить меню",
            "Селектор клика (подпункт):",
            initial=str(step.get("selector", "")),
        )
        if click_selector is None:
            return None
        click_selector = click_selector.strip()
        if not click_selector:
            return None

        hover_text = prompt_text(
            parent,
            "Починить меню",
            "Текст пункта меню (необязательно):",
            initial=str(step.get("hoverText", step.get("text", ""))),
        )

        hover_step: dict[str, Any] = {"action": "hover", "selector": hover_selector}
        if hover_text:
            hover_step["text"] = hover_text.strip()

        click_step = dict(step)
        click_step["action"] = "click"
        click_step["selector"] = click_selector
        click_step["hoverSelector"] = hover_selector
        if hover_text:
            click_step["hoverText"] = hover_text.strip()

        steps[index] = hover_step
        steps.insert(index + 1, click_step)
        self._model.set_steps(steps)
        self.commit_steps_to_gherkin()
        return self._model.steps

    def save_current_scenario(
        self,
        *,
        editor_text: str,
        target_path: Path | None = None,
    ) -> tuple[bool, str | None]:
        """Parse editor steps, save editor text as-is (comments and spacing preserved)."""
        raw = editor_text
        stripped = raw.strip()
        steps: list[dict[str, Any]] = []
        if stripped:
            try:
                steps = gherkin_to_steps(raw)
            except GherkinParseError as exc:
                if self._parent:
                    alert(self._parent, BRAND_NAME, f"Не удалось разобрать Gherkin:\n{exc}")
                else:
                    self._model.status_message.emit(str(exc), "error")
                return False, None

        target = self._resolve_save_target(target_path)
        if target is None:
            return False, None

        save_feature_text(target, raw)
        self._model.set_steps(steps)
        self._model.set_source_text(raw)
        self._model.set_name(target.stem)
        self._model.mark_saved(target)
        self._model.status_message.emit(f"Сохранено: {target}", "success")
        return True, raw

    def _resolve_save_target(self, preferred: Path | None = None) -> Path | None:
        path = preferred.resolve() if preferred is not None else self._model.feature_path
        if path is not None and path.parent.exists():
            return path

        default_name = self._model.name.strip() or suggest_scenario_name(self._model.start_url)
        if not default_name or default_name == "Сценарий":
            default_name = "Сценарий"
        initial = self._initial_export_dir() or Path.home()
        target = pick_save_file(
            self._parent,
            title="Сохранить feature файл",
            filter_spec=FEATURE_FILTER,
            default_name=f"{default_name}.feature",
            initial_dir=initial,
        )
        if target is None:
            return None
        if target.suffix.lower() != ".feature":
            target = target.with_suffix(".feature")
        if target.exists() and self._parent and not confirm(
            self._parent,
            BRAND_NAME,
            f"Файл «{target.name}» уже существует.\nПерезаписать?",
        ):
            return None
        return target

    def current_scenario_dict(self) -> dict[str, Any]:
        steps = self._model.steps
        start_url = self._model.start_url
        name = self._model.name or "без имени"
        if not steps:
            path = self._model.feature_path
            if path and path.exists():
                loaded = load_feature(path)
                steps = list(loaded.get("steps", []) or [])
                if not name or name == "без имени":
                    name = str(loaded.get("name", "") or path.stem)
                if not start_url:
                    start_url = str(loaded.get("startUrl", "") or "")
        if not steps:
            raise ScenarioNotFoundError("Нет сценария")
        return {
            "name": name,
            "startUrl": start_url,
            "steps": steps,
        }

    def _initial_export_dir(self) -> Path | None:
        if self._model.feature_path:
            return self._model.feature_path.parent
        target = self._catalog.target_directory_for_new_file()
        if target:
            return target
        return get_root()

    def export_feature_file(self) -> bool:
        try:
            scenario = self.current_scenario_dict()
        except ScenarioNotFoundError:
            self._model.status_message.emit("Нет сценария для экспорта", "error")
            return False
        name = str(scenario.get("name", "") or "scenario")
        path = pick_save_file(
            self._parent,
            title="Экспорт Gherkin (.feature)",
            filter_spec=FEATURE_FILTER,
            default_name=f"{name}.feature",
            initial_dir=self._initial_export_dir(),
        )
        if path is None:
            return False
        if path.suffix.lower() != ".feature":
            path = path.with_suffix(".feature")
        export_scenario_feature(path, scenario)
        self._model.status_message.emit(f"Экспорт Gherkin: {path}", "success")
        return True

    def export_zip_file(self) -> bool:
        try:
            scenario = self.current_scenario_dict()
        except ScenarioNotFoundError:
            self._model.status_message.emit("Нет сценария для экспорта", "error")
            return False
        name = str(scenario.get("name", "") or "scenario")
        path = pick_save_file(
            self._parent,
            title="Экспорт ZIP",
            filter_spec=ZIP_FILTER,
            default_name=f"{name}.zip",
            initial_dir=self._initial_export_dir(),
        )
        if path is None:
            return False
        if path.suffix.lower() != ".zip":
            path = path.with_suffix(".zip")
        export_scenario_zip(path, scenario)
        self._model.status_message.emit(f"Экспорт ZIP: {path}", "success")
        return True

    def export_json_file(self) -> bool:
        try:
            scenario = self.current_scenario_dict()
        except ScenarioNotFoundError:
            self._model.status_message.emit("Нет сценария для экспорта", "error")
            return False
        name = str(scenario.get("name", "") or "scenario")
        path = pick_save_file(
            self._parent,
            title="Экспорт JSON",
            filter_spec=JSON_FILTER,
            default_name=f"{name}.json",
            initial_dir=self._initial_export_dir(),
        )
        if path is None:
            return False
        if path.suffix.lower() != ".json":
            path = path.with_suffix(".json")
        export_scenario_json(path, scenario)
        self._model.status_message.emit(f"Экспорт JSON: {path}", "success")
        return True

    def import_json_file(self) -> bool:
        path = pick_open_file(
            self._parent,
            title="Импорт JSON",
            filter_spec=JSON_FILTER,
            initial_dir=self._initial_export_dir(),
        )
        if path is None:
            return False
        try:
            scenario = import_scenario_json(path)
        except Exception as exc:  # noqa: BLE001
            self._model.status_message.emit(f"Ошибка импорта JSON: {exc}", "error")
            return False

        dest_dir = self._catalog.target_directory_for_new_file() or get_root()
        if not dest_dir:
            if self._parent:
                alert(self._parent, BRAND_NAME, "Сначала выберите каталог .feature файлов слева.")
            return False

        name = str(scenario.get("name", path.stem) or path.stem)
        target = dest_dir / f"{name}.feature"
        if target.exists() and self._parent and not confirm(
            self._parent,
            BRAND_NAME,
            f"Файл «{target.name}» уже существует.\nПерезаписать?",
        ):
            return False

        save_feature(target, list(scenario.get("steps", [])), scenario_name=target.stem)
        self._model.load_from_path(target)
        self._catalog.select_feature(target)
        self._catalog.refresh_tree()
        self._model.status_message.emit(f"Импортирован сценарий «{target.stem}» из JSON", "success")
        return True

    def export_playwright_file(self, *, python: bool = False) -> bool:
        try:
            scenario = self.current_scenario_dict()
        except ScenarioNotFoundError:
            self._model.status_message.emit("Нет сценария для экспорта", "error")
            return False
        name = str(scenario.get("name", "") or "scenario")
        fmt = ExportFormat.PYTHON if python else ExportFormat.TYPESCRIPT
        if python:
            default_name = f"test_{name}.py"
            filter_spec = PLAYWRIGHT_PY_FILTER
            title = "Экспорт Playwright (Python)"
        else:
            default_name = f"{name}.spec.ts"
            filter_spec = PLAYWRIGHT_TS_FILTER
            title = "Экспорт Playwright (TypeScript)"
        path = pick_save_file(
            self._parent,
            title=title,
            filter_spec=filter_spec,
            default_name=default_name,
            initial_dir=self._initial_export_dir(),
        )
        if path is None:
            return False
        if not python and path.suffix.lower() not in {".ts", ".spec.ts"}:
            path = path.with_suffix(".spec.ts")
        if python and path.suffix.lower() != ".py":
            path = path.with_suffix(".py")
        text = export_scenario_playwright(scenario, fmt=fmt)
        path.write_text(text, encoding="utf-8")
        self._model.status_message.emit(f"Экспорт Playwright: {path}", "success")
        return True

    def import_feature_file(self) -> bool:
        path = pick_open_file(
            self._parent,
            title="Импорт Gherkin (.feature)",
            filter_spec=FEATURE_FILTER,
            initial_dir=self._initial_export_dir(),
        )
        if path is None:
            return False
        try:
            feature = import_scenario_feature(path)
        except Exception as exc:  # noqa: BLE001
            self._model.status_message.emit(f"Ошибка импорта: {exc}", "error")
            return False

        dest_dir = self._catalog.target_directory_for_new_file() or get_root()
        if not dest_dir:
            if self._parent:
                alert(self._parent, BRAND_NAME, "Сначала выберите каталог .feature файлов слева.")
            return False

        target = dest_dir / f"{feature.get('name', path.stem)}.feature"
        if target.suffix.lower() != ".feature":
            target = target.with_suffix(".feature")
        if target.exists() and self._parent and not confirm(
            self._parent,
            BRAND_NAME,
            f"Файл «{target.name}» уже существует.\nПерезаписать?",
        ):
            return False

        save_feature(target, list(feature.get("steps", [])), scenario_name=target.stem)
        self._model.load_from_path(target)
        self._catalog.select_feature(target)
        self._catalog.refresh_tree()
        self._model.status_message.emit(f"Импортирован сценарий «{target.stem}»", "success")
        return True

    def delete_selected_feature(self) -> bool:
        path = self._model.feature_path
        if not path:
            self._model.status_message.emit("Выберите .feature файл в левом дереве", "error")
            if self._parent:
                alert(self._parent, BRAND_NAME, "Выберите .feature файл в левом дереве")
            return False
        if self._parent and not confirm(self._parent, BRAND_NAME, f"Удалить файл «{path.name}»?"):
            return False

        parent_dir = path.parent
        delete_feature(path)
        clear_draft()
        self._catalog.select_directory(parent_dir)
        self._model.new_scenario()
        self._catalog.refresh_tree()
        self._model.status_message.emit(f"Удалён сценарий «{path.stem}»", "success")
        return True

    def duplicate_selected_feature(self) -> bool:
        src = self._model.feature_path
        if not src:
            self._model.status_message.emit("Выберите .feature файл в левом дереве для дубликата", "error")
            return False

        name = self._model.name.strip() or src.stem
        if not self._parent:
            return False
        new_name = prompt_text(self._parent, "Дублировать", "Имя копии:", initial=f"{name}-copy")
        if not new_name:
            return False

        dst = src.parent / f"{new_name.strip()}.feature"
        if dst.exists() and not confirm(
            self._parent,
            BRAND_NAME,
            f"Файл «{dst.name}» уже есть.\nПерезаписать?",
        ):
            return False

        duplicate_feature(src, dst, steps=None)
        self._model.load_from_path(dst)
        self._catalog.select_feature(dst)
        self._catalog.refresh_tree()
        self._model.status_message.emit(f"Создана копия «{new_name}»", "success")
        return True

    def refresh_catalog(self) -> None:
        self._catalog.refresh_tree()

    def on_close(self, *, editor_text: str | None = None) -> None:
        if editor_text is not None:
            self.flush_editor_to_disk(editor_text)
        settings = load_settings()
        if self._model.feature_path is None:
            self._model.save_draft_if_needed(
                enabled=bool(settings.get("autosave_enabled", True)),
                editor_text=editor_text,
            )

    def flush_editor_to_disk(self, editor_text: str, *, path: Path | None = None) -> bool:
        """Persist editor text to a `.feature` file when it differs from disk."""
        target = path or self._model.feature_path
        stripped = editor_text.strip()
        if target is None or not stripped:
            return False
        try:
            steps = gherkin_to_steps(editor_text)
        except GherkinParseError:
            return False
        try:
            on_disk = load_feature(target).get("steps", [])
        except (OSError, GherkinParseError, ValueError):
            on_disk = []
        if list(steps) == list(on_disk):
            return False
        save_feature_text(target, editor_text)
        if self._model.feature_path is not None and self._model.feature_path.resolve() == target.resolve():
            self._model.set_steps(steps)
            self._model.set_source_text(editor_text)
            self._model.set_name(target.stem)
            self._model.mark_saved(target)
        return True
