"""Gherkin text editor panel."""

from __future__ import annotations

import re
from typing import Any

from PySide6.QtCore import QTimer, Signal
from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import QVBoxLayout, QWidget

from app.gherkin_ru import GherkinParseError, STEP_INDENT, gherkin_to_steps, is_gherkin_step_line, parse_gherkin_steps, steps_to_gherkin
from app.mvc.controllers.scenario_controller import ScenarioController
from app.mvc.models.scenario_model import ScenarioModel
from app.qt.dialogs import prompt_text
from app.qt.widgets.picker_step_dialog import pick_picker_step
from app.qt.theme import COLOR_ERROR, COLOR_SUCCESS, COLOR_WARNING
from app.qt.widgets.gherkin_editor import GherkinEditor
from app.qt.widgets.gherkin_hints import GherkinHintsBar
from app.brand import BRAND_NAME


class GherkinPanel(QWidget):
    status_message = Signal(str)
    dirty_changed = Signal(bool)
    applied = Signal()

    def __init__(
        self,
        model: ScenarioModel,
        controller: ScenarioController,
        parent: QWidget | None = None,
        *,
        compact: bool = False,
    ) -> None:
        super().__init__(parent)
        self._model = model
        self._controller = controller
        self._parse_error = False
        self._unapplied = False
        self._block = False
        self._sync_from_model = True
        self._last_seen_text = ""

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.hints_bar = GherkinHintsBar(self)
        self.hints_bar.insert_template_clicked.connect(self._insert_template)
        layout.addWidget(self.hints_bar)

        self.editor = GherkinEditor(self)
        self.editor.setPlaceholderText(
            "Функционал: …\n"
            "Сценарий: …\n"
            f"{STEP_INDENT}Допустим открыт \"https://site.com\""
        )
        self.editor.textChanged.connect(self._on_text_changed)
        layout.addWidget(self.editor)

        self._auto_apply_timer = QTimer(self)
        self._auto_apply_timer.setSingleShot(True)
        self._auto_apply_timer.setInterval(400)
        self._auto_apply_timer.timeout.connect(self._auto_apply_if_valid)

        self._model.changed.connect(self._on_model_changed)

    @property
    def has_parse_error(self) -> bool:
        return self._parse_error

    @property
    def is_unapplied(self) -> bool:
        return self._unapplied

    @property
    def is_dirty(self) -> bool:
        """True when editor text has a syntax error (blocks run/save)."""
        return self._parse_error

    def set_sync_from_model(self, enabled: bool) -> None:
        self._sync_from_model = enabled

    def get_text(self) -> str:
        return self.editor.toPlainText()

    def set_text(self, text: str, *, clean: bool = True) -> None:
        current = self.editor.toPlainText()
        if self._texts_equivalent(current, text):
            self.editor.clear_step_line_highlights()
            self._last_seen_text = current
            self._set_editor_state(parse_error=False, unapplied=not clean)
            if not clean:
                self._auto_apply_timer.start()
            return
        self.editor.clear_char_formats()
        self.editor.clear_step_line_highlights()
        self._block = True
        self.editor.replace_plain_text_preserve_caret(text)
        self._block = False
        self._last_seen_text = self.editor.toPlainText()
        self._set_editor_state(parse_error=False, unapplied=not clean)
        if not clean:
            self._auto_apply_timer.start()

    def mark_clean(self) -> None:
        self._set_editor_state(parse_error=False, unapplied=False)

    @staticmethod
    def _texts_equivalent(left: str, right: str) -> bool:
        from app.feature_store import feature_texts_equivalent

        return feature_texts_equivalent(left, right)

    def sync_from_model(self, *, force: bool = False) -> None:
        self._do_sync(force=force)

    def _on_model_changed(self) -> None:
        if self._sync_from_model:
            self._do_sync(force=False)

    def _on_text_changed(self) -> None:
        if self._block:
            return
        raw = self.editor.toPlainText()
        if raw == self._last_seen_text:
            return
        self._last_seen_text = raw
        source = self._model.source_text
        if source is not None and self._texts_equivalent(raw, source):
            if self._parse_error:
                self.editor.clear_step_line_highlights()
            self._set_editor_state(parse_error=False, unapplied=False)
            self._auto_apply_timer.stop()
            return
        if self._parse_error:
            self.editor.clear_step_line_highlights()
        self._set_editor_state(parse_error=False, unapplied=True)
        self._auto_apply_timer.start()

    def _parse_editor_text(self, raw: str) -> tuple[list[dict[str, Any]] | None, GherkinParseError | None, str]:
        stripped = raw.strip()
        if not stripped:
            return [], None, raw
        try:
            steps, canonical = parse_gherkin_steps(raw)
            return steps, None, canonical
        except GherkinParseError as exc:
            return None, exc, raw

    def _sync_editor_text_if_needed(self, raw: str, canonical: str) -> str:
        if self._texts_equivalent(raw, canonical):
            return raw
        self._block = True
        self.editor.replace_plain_text_preserve_caret(canonical)
        self._block = False
        return canonical

    def _report_parse_error(self, exc: GherkinParseError) -> None:
        self._set_editor_state(parse_error=True, unapplied=True)
        self._emit_status(str(exc), COLOR_ERROR)
        line_no = max(1, int(exc.line_no))
        self.editor.set_syntax_error_line(line_no)
        self.editor.set_step_line_highlights([line_no], failed=True)

    def _apply_parsed_steps(self, raw: str, steps: list[dict[str, Any]]) -> None:
        self._block = True
        try:
            self._model.sync_tags_from_text(raw)
            self._controller.apply_parsed_editor(steps, raw)
        finally:
            self._block = False
        self._set_editor_state(parse_error=False, unapplied=False)
        self.editor.set_syntax_error_line(None)
        self.editor.clear_step_line_highlights()
        self.applied.emit()

    def _auto_apply_if_valid(self) -> None:
        if self._block:
            return
        raw = self.editor.toPlainText()
        steps, error, canonical = self._parse_editor_text(raw)
        if error is not None:
            self._report_parse_error(error)
            return
        assert steps is not None
        raw = self._sync_editor_text_if_needed(raw, canonical)
        if not raw.strip():
            if self._parse_error or self._unapplied or self._model.steps:
                self._apply_parsed_steps(raw, steps)
            return
        source = self._model.source_text
        if (
            not self._parse_error
            and not self._unapplied
            and source is not None
            and self._texts_equivalent(raw, source)
            and len(steps) == len(self._model.steps)
        ):
            return
        self._apply_parsed_steps(raw, steps)

    def _set_editor_state(self, *, parse_error: bool, unapplied: bool) -> None:
        parse_cleared = self._parse_error and not parse_error
        changed = parse_error != self._parse_error or unapplied != self._unapplied
        self._parse_error = parse_error
        self._unapplied = unapplied
        if parse_cleared:
            self.editor.set_syntax_error_line(None)
            self.editor.clear_step_line_highlights()
        if not changed:
            return
        self.dirty_changed.emit(self._parse_error or self._unapplied)
        if parse_error:
            self._emit_status("Исправьте ошибки в тексте сценария", COLOR_WARNING)
        elif parse_cleared:
            self._emit_status("")

    def _set_dirty(self, dirty: bool) -> None:
        """Backward-compatible helper: dirty=True means syntax error."""
        self._set_editor_state(parse_error=dirty, unapplied=dirty if dirty else self._unapplied)

    def _emit_status(self, text: str, color: str = "") -> None:
        self.status_message.emit(text)

    def _step_line_numbers(self) -> list[int]:
        lines = self.editor.toPlainText().splitlines()
        result: list[int] = []
        for index, line in enumerate(lines, start=1):
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            if stripped.lower().startswith(("сценарий:", "функционал:", "функция:")):
                continue
            if is_gherkin_step_line(line):
                result.append(index)
        return result

    def focus_step(self, step_index: int) -> None:
        lines = self._step_line_numbers()
        if 1 <= step_index <= len(lines):
            line_no = lines[step_index - 1]
            self.editor.set_step_line_highlights([line_no], failed=True)
            self._scroll_to_line(line_no)

    def highlight_step(self, step_index: int, *, failed: bool = False) -> None:
        lines = self._step_line_numbers()
        if 1 <= step_index <= len(lines):
            line_no = lines[step_index - 1]
            self.editor.set_step_line_highlights([line_no], failed=failed)
            self._scroll_to_line(line_no)

    def clear_step_highlight(self) -> None:
        self.editor.clear_step_line_highlights()

    def _scroll_to_line(self, line_no: int) -> None:
        block = self.editor.document().findBlockByNumber(max(0, line_no - 1))
        if block.isValid():
            cursor = self.editor.textCursor()
            cursor.setPosition(block.position())
            self.editor.setTextCursor(cursor)
            self.editor.centerCursor()

    def _editor_text_from_model(self) -> str:
        source = self._model.source_text
        if source is not None:
            return source
        if self._model.steps:
            scenario_name = self._model.name.strip() or "Сценарий"
            return steps_to_gherkin(
                self._model.steps,
                scenario_name=scenario_name,
                tags=self._model.tags,
            )
        return ""

    def _do_sync(self, *, force: bool = False) -> None:
        if self._unapplied and not force:
            return
        text = self._editor_text_from_model()
        self._block = True
        if not self._texts_equivalent(self.editor.toPlainText(), text):
            self.editor.clear_char_formats()
            self.editor.clear_step_line_highlights()
            self.editor.replace_plain_text_preserve_caret(text)
        else:
            self.editor.clear_step_line_highlights()
        self._block = False

        raw = self.editor.toPlainText()
        steps, error, canonical = self._parse_editor_text(raw)
        if error is not None:
            self._report_parse_error(error)
            return
        assert steps is not None
        raw = self._sync_editor_text_if_needed(raw, canonical)
        self._set_editor_state(parse_error=False, unapplied=False)

    def _validate(self) -> None:
        self.editor.clear_char_formats()
        self.editor.clear_step_line_highlights()
        raw = self.editor.toPlainText().strip()
        if not raw:
            self._emit_status("Файл пуст", COLOR_SUCCESS)
            return
        try:
            gherkin_to_steps(raw)
            self._emit_status("Синтаксис OK", COLOR_SUCCESS)
        except GherkinParseError as exc:
            self._emit_status(str(exc), COLOR_ERROR)
            self.editor.set_step_line_highlights([max(1, int(exc.line_no))], failed=True)
        except Exception as exc:  # noqa: BLE001
            self._emit_status(f"Ошибка: {exc}", COLOR_ERROR)

    def _reset(self) -> None:
        self._do_sync(force=True)

    def _apply(self) -> None:
        self._auto_apply_timer.stop()
        self.editor.clear_char_formats()
        self.editor.clear_step_line_highlights()
        raw = self.editor.toPlainText()
        steps, error, canonical = self._parse_editor_text(raw)
        if error is not None:
            self._report_parse_error(error)
            return
        assert steps is not None
        raw = self._sync_editor_text_if_needed(raw, canonical)
        if not raw.strip():
            self._apply_parsed_steps(raw, steps)
            self._emit_status("Сценарий очищен", COLOR_SUCCESS)
            return
        try:
            self._apply_parsed_steps(raw, steps)
        except Exception as exc:  # noqa: BLE001
            self._set_editor_state(parse_error=True, unapplied=True)
            self._emit_status(f"Ошибка: {exc}", COLOR_ERROR)
            return
        self._emit_status(f"Сценарий обновлён: {len(steps)} шагов", COLOR_SUCCESS)

    def discard_changes(self) -> None:
        self._do_sync(force=True)
        self._emit_status("Изменения сброшены", COLOR_SUCCESS)

    def prepare_open(self, *, unsaved_to_disk: bool = False) -> bool:
        if self._parse_error or self._unapplied or unsaved_to_disk:
            from app.qt.dialogs import confirm

            if unsaved_to_disk and not self._parse_error and not self._unapplied:
                message = "Есть несохранённые изменения на диске.\nСбросить и открыть другой файл?"
            elif self._parse_error:
                message = "В тексте сценария есть ошибки.\nСбросить и открыть другой файл?"
            else:
                message = "Есть несохранённые правки в редакторе.\nСбросить и открыть другой файл?"
            if not confirm(
                self,
                BRAND_NAME,
                message,
            ):
                return False
        return True

    def apply_if_dirty(self) -> bool:
        if not self._unapplied and not self._parse_error:
            return True
        self._apply()
        return not self._parse_error

    def apply_to_model(self) -> bool:
        """Always parse editor text into the scenario model (play/save/validate)."""
        self._apply()
        return not self._parse_error

    def _insert_template(self) -> None:
        from app.scenario_hints import gherkin_template_text

        text = gherkin_template_text(
            url=self._model.start_url,
            scenario_name=self._model.name.strip() or "Сценарий",
        )
        self.set_text(text, clean=False)

    def insert_picked_selector(self, selector: str) -> None:
        """Insert selector from the in-browser picker as a Gherkin step."""
        selector = selector.strip()
        if not selector:
            return

        choice = pick_picker_step(self, selector, keyword=self.editor.suggested_step_keyword())
        if choice is None:
            return

        if choice.label == "Только селектор":
            self.editor.insert_quoted_text(selector)
            self._set_editor_state(parse_error=False, unapplied=True)
            self._auto_apply_timer.start()
            self._emit_status("Селектор вставлен — допишите шаг сценария", COLOR_SUCCESS)
            return

        self.editor.insert_step_line(choice.step_body)
        self._set_editor_state(parse_error=False, unapplied=True)
        self._auto_apply_timer.start()
        self._emit_status(f"Добавлен шаг «{choice.label}»", COLOR_SUCCESS)

    def _step_index_at_cursor(self) -> int | None:
        line_no = self.editor.textCursor().blockNumber() + 1
        line_numbers = self._step_line_numbers()
        if line_no not in line_numbers:
            return None
        return line_numbers.index(line_no)

    def fix_menu_click_at_cursor(self) -> bool:
        """Split hover-menu click at cursor into «навожу» + «нажимаю»."""
        index = self._step_index_at_cursor()
        if index is None:
            block = self.editor.textCursor().block()
            line = block.text()
            if not re.search(r"нажимаю\s+\"", line, flags=re.IGNORECASE):
                self._emit_status("Поставьте курсор на строку «нажимаю ...»", COLOR_WARNING)
                return False
            match = re.search(r'нажимаю\s+"((?:\\.|[^"])*)"', line, flags=re.IGNORECASE)
            if not match:
                self._emit_status("Не удалось прочитать селектор клика", COLOR_WARNING)
                return False
            click_selector = match.group(1).replace(r"\"", '"').replace(r"\\", "\\")
            from app.scenario_hints import propose_menu_hover_fix

            proposal = propose_menu_hover_fix({"action": "click", "selector": click_selector})
            if proposal is None:
                self._emit_status("Не удалось определить селектор наведения", COLOR_WARNING)
                return False
            return self._insert_menu_hover_lines(block, proposal[0], proposal[1], line)

        if self._controller.try_fix_menu_hover(index):
            self.sync_from_model(force=True)
            self._set_editor_state(parse_error=False, unapplied=False)
            self._emit_status("Шаг разбит: наведение + клик", COLOR_SUCCESS)
            return True

        if 0 <= index < len(self._model.steps) and self._controller.split_click_into_hover(self, index) is not None:
            self.sync_from_model(force=True)
            self._set_editor_state(parse_error=False, unapplied=False)
            self._emit_status("Добавлено наведение перед кликом", COLOR_SUCCESS)
            return True
        return False

    def _insert_menu_hover_lines(
        self,
        block,
        hover_selector: str,
        click_selector: str,
        click_line: str,
    ) -> bool:
        from app.gherkin_ru import leading_indent

        indent = leading_indent(click_line) or STEP_INDENT
        keyword_match = re.match(r"^(Допустим|Когда|Тогда|И|Но)\s+", click_line.strip(), flags=re.IGNORECASE)
        click_keyword = keyword_match.group(1) if keyword_match else "И"

        self.editor.insert_step_line(f'навожу "{hover_selector}"', before_block=block)
        cursor = self.editor.textCursor()
        cursor.setPosition(block.position())
        cursor.movePosition(QTextCursor.MoveOperation.EndOfBlock, QTextCursor.MoveMode.KeepAnchor)
        cursor.insertText(f'{indent}{click_keyword} нажимаю "{click_selector}"')
        self._set_editor_state(parse_error=False, unapplied=True)
        self._auto_apply_timer.start()
        self._emit_status("Добавлено наведение перед кликом", COLOR_SUCCESS)
        return True

    def insert_hover_step(self) -> None:
        """Insert a hover step at the cursor (for dropdown menus)."""
        selector = prompt_text(
            self,
            "Наведение для меню",
            "Селектор пункта меню, на который нужно навести курсор\n"
            '(например: a:has-text("Одежда")):',
            initial="",
        )
        if selector is None:
            return
        selector = selector.strip()
        if not selector:
            self._emit_status("Селектор наведения не указан", COLOR_WARNING)
            return
        self.editor.insert_step_line(f'навожу "{selector}"')
        self._set_editor_state(parse_error=False, unapplied=True)
        self._auto_apply_timer.start()
        self._emit_status("Добавлен шаг наведения", COLOR_SUCCESS)
