"""Step templates for in-browser element picker."""

from __future__ import annotations

from dataclasses import dataclass

from app.gherkin_ru import _quote, format_step_line


@dataclass(frozen=True)
class PickerStepChoice:
    label: str
    step_body: str
    description: str
    preview: str


def picker_step_choices(selector: str, *, keyword: str = "Допустим") -> list[PickerStepChoice]:
    quoted = _quote(selector.strip())
    templates: tuple[tuple[str, str, str], ...] = (
        ("Клик", f'нажимаю "{quoted}"', "Клик по элементу (action: click)"),
        ("Двойной клик", f'дважды нажимаю "{quoted}"', "Двойной клик (action: double_click)"),
        ("Наведение", f'навожу "{quoted}"', "Наведение курсора (action: hover)"),
        ("Видимость", f'вижу "{quoted}"', "Элемент виден (action: assert_visible)"),
        ("Скрыт", f'не вижу "{quoted}"', "Элемент скрыт (action: assert_hidden)"),
        ("Очистка поля", f'очищаю "{quoted}"', "Очистить ввод (action: clear)"),
        ("Галочка", f'отмечаю "{quoted}"', "Установить галочку (action: check)"),
        ("Снять галочку", f'снимаю отметку с "{quoted}"', "Снять галочку (action: uncheck)"),
        ("Скролл", f'скроллю к "{quoted}"', "Прокрутка к элементу (action: scroll_to)"),
        ("Жду появления", f'жду появления "{quoted}"', "Ожидание элемента (action: wait_for)"),
        ("Жду исчезновения", f'жду исчезновения "{quoted}"', "Ожидание скрытия (action: wait_for_hidden)"),
        ("Только селектор", quoted, "Вставить селектор без шага Gherkin"),
    )
    choices: list[PickerStepChoice] = []
    for label, body, description in templates:
        if label == "Только селектор":
            preview = quoted
        else:
            preview = format_step_line(keyword, body)
        choices.append(
            PickerStepChoice(
                label=label,
                step_body=body,
                description=description,
                preview=preview,
            )
        )
    return choices
