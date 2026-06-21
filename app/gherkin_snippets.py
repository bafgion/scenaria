"""Gherkin step snippets and completion helpers."""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.gherkin_ru import is_step_indented

_KEYWORD_RE = re.compile(r"^(?:(Допустим|Когда|Тогда|И|Но)\s+)?(.*)$", re.IGNORECASE)
_HEADER_RE = re.compile(r"^\s*(функционал|сценарий|функция)\s*:?", re.IGNORECASE)


@dataclass(frozen=True)
class GherkinSnippet:
    label: str
    insert: str
    description: str


KEYWORDS: tuple[str, ...] = ("Допустим", "Когда", "Тогда", "И", "Но")

HEADER_SNIPPETS: tuple[GherkinSnippet, ...] = (
    GherkinSnippet("Функционал:", "Функционал: UI сценарий", "Заголовок feature-файла"),
    GherkinSnippet("Сценарий:", "Сценарий: Имя сценария", "Название сценария"),
)

STEP_SNIPPETS: tuple[GherkinSnippet, ...] = (
    GherkinSnippet(
        "открыт",
        'открыт "https://site.com"',
        "Переход на страницу (action: goto)",
    ),
    GherkinSnippet(
        "нажимаю",
        'нажимаю "button.submit"',
        "Клик по элементу (action: click)",
    ),
    GherkinSnippet(
        "дважды нажимаю",
        'дважды нажимаю ".file-item"',
        "Двойной клик (action: double_click)",
    ),
    GherkinSnippet(
        "навожу",
        'навожу "nav a:has-text(\\"Услуги\\")"',
        "Наведение перед кликом по подменю или тултипу",
    ),
    GherkinSnippet(
        "ввожу",
        'ввожу "текст" в "input[name=email]"',
        "Ввод текста в поле (action: fill)",
    ),
    GherkinSnippet(
        "случайный телефон",
        'ввожу случайный телефон в "input[type=tel]"',
        "Случайный телефон на каждый прогон (action: fill_generated)",
    ),
    GherkinSnippet(
        "случайное имя",
        'ввожу случайное имя в "input[name=firstName]"',
        "Имя (отдельное поле)",
    ),
    GherkinSnippet(
        "случайная фамилия",
        'ввожу случайную фамилию в "input[name=lastName]"',
        "Фамилия (отдельное поле)",
    ),
    GherkinSnippet(
        "случайное отчество",
        'ввожу случайное отчество в "input[name=middleName]"',
        "Отчество (отдельное поле)",
    ),
    GherkinSnippet(
        "случайный адрес",
        'ввожу случайный адрес в "textarea[name=address]"',
        "Случайный адрес на каждый прогон",
    ),
    GherkinSnippet(
        "случайный инн",
        'ввожу случайный инн в "input[name=inn]"',
        "ИНН физлица (12 цифр) с контрольной суммой",
    ),
    GherkinSnippet(
        "расчётный счёт",
        'ввожу случайный расчётный счёт в "input[name=account]"',
        "20-значный расчётный счёт",
    ),
    GherkinSnippet(
        "огрнип",
        'ввожу случайный огрнип в "input[name=ogrnip]"',
        "ОГРНИП (15 цифр) с контрольной суммой",
    ),
    GherkinSnippet(
        "плейсхолдер",
        'ввожу "{{first_name}}" в "input[name=firstName]"',
        "Плейсхолдеры: {{first_name}}, {{last_name}}, {{patronymic}}, {{phone}}…",
    ),
    GherkinSnippet(
        "ввожу код из почты",
        'ввожу код из почты с клавиатуры в 6 полей "input.pin-digit"',
        "OTP через keyboard.type (Svelte); по умолчанию для нескольких ячеек — клавиатура",
    ),
    GherkinSnippet(
        "очищаю",
        'очищаю "input#search"',
        "Очистка поля ввода (action: clear)",
    ),
    GherkinSnippet(
        "выбираю",
        'выбираю "Значение" в "select#country"',
        "Выбор значения в списке (action: select)",
    ),
    GherkinSnippet(
        "отмечаю",
        'отмечаю "input#agree"',
        "Установка галочки (action: check)",
    ),
    GherkinSnippet(
        "снимаю отметку",
        'снимаю отметку с "input#newsletter"',
        "Снятие галочки (action: uncheck)",
    ),
    GherkinSnippet(
        "нажимаю клавишу",
        'нажимаю клавишу "Enter"',
        "Клавиша на странице — Enter, Escape, Tab… (action: press)",
    ),
    GherkinSnippet(
        "загружаю файл",
        'загружаю файл "C:\\\\data\\\\doc.pdf" в "input[type=file]"',
        "Загрузка файла в поле (action: upload)",
    ),
    GherkinSnippet(
        "скачиваю",
        'скачиваю по клику на "a.export"',
        "Скачивание файла по клику (action: download_click)",
    ),
    GherkinSnippet(
        "скачанный файл",
        'проверяю что скачанный файл содержит "Invoice"',
        "Проверка содержимого скачанного файла (action: assert_download_contains)",
    ),
    GherkinSnippet(
        "запоминаю текст",
        'запоминаю текст "{{login}}" как "user_login"',
        "Сохранить литерал в переменную (action: remember_text)",
    ),
    GherkinSnippet(
        "запоминаю url",
        'запоминаю url как "current_url"',
        "Сохранить текущий URL (action: remember_url)",
    ),
    GherkinSnippet(
        "рисую подпись",
        'рисую подпись в "canvas"',
        "Рисование подписи на canvas (ПЭП, action: draw_signature)",
    ),
    GherkinSnippet(
        "скроллю к",
        'скроллю к "section#contacts"',
        "Прокрутка к элементу (action: scroll_to)",
    ),
    GherkinSnippet(
        "обновляю страницу",
        "обновляю страницу",
        "Перезагрузка страницы (action: reload)",
    ),
    GherkinSnippet(
        "возвращаюсь назад",
        "возвращаюсь назад",
        "Кнопка «Назад» браузера (action: go_back)",
    ),
    GherkinSnippet(
        "закрываю браузер",
        "закрываю браузер",
        "Закрыть окно браузера (action: close_browser)",
    ),
    GherkinSnippet(
        "вижу",
        'вижу "h1.title"',
        "Проверка видимости элемента (action: assert_visible)",
    ),
    GherkinSnippet(
        "не вижу",
        'не вижу ".modal-overlay"',
        "Элемент скрыт или отсутствует (action: assert_hidden)",
    ),
    GherkinSnippet(
        "проверяю текст",
        'проверяю текст "Успех" в ".message"',
        "Проверка текста в элементе (action: assert_text)",
    ),
    GherkinSnippet(
        "проверяю url",
        'проверяю url "https://site.com/profile"',
        "Проверка текущего URL (action: assert_url)",
    ),
    GherkinSnippet(
        "жду",
        "жду 2 сек",
        "Пауза перед следующим шагом (action: wait)",
    ),
    GherkinSnippet(
        "жду появления",
        'жду появления "button.ready"',
        "Ожидание появления элемента (action: wait_for)",
    ),
    GherkinSnippet(
        "жду исчезновения",
        'жду исчезновения ".spinner"',
        "Ожидание скрытия лоадера или модалки (action: wait_for_hidden)",
    ),
)

HINTS_LINE = "Ctrl+Space — подсказки при вводе шагов"


def _match_prefix(value: str, prefix: str) -> bool:
    return value.lower().startswith(prefix.lower())


def _keyword_candidates(prefix: str) -> list[GherkinSnippet]:
    result: list[GherkinSnippet] = []
    for word in KEYWORDS:
        if _match_prefix(word, prefix):
            result.append(GherkinSnippet(word, word, f"Ключевое слово «{word}»"))
    return result


def _header_candidates(prefix: str) -> list[GherkinSnippet]:
    stripped = prefix.lstrip()
    return [s for s in HEADER_SNIPPETS if _match_prefix(s.label, stripped) or _match_prefix(s.insert, stripped)]


def _step_candidates(prefix: str) -> list[GherkinSnippet]:
    return [s for s in STEP_SNIPPETS if _match_prefix(s.label, prefix) or _match_prefix(s.insert, prefix)]


def _keyword_end_column(line: str, indent_len: int, keyword: str) -> int:
    """Column right after the step keyword (before the step body)."""
    return indent_len + len(keyword)


def completions_for_line(line: str, column: int) -> tuple[int, int, list[GherkinSnippet]]:
    """Return replace start/end columns in line and matching snippets."""
    if column < 0:
        column = len(line)
    column = min(column, len(line))

    stripped = line.lstrip()
    indent_len = len(line) - len(stripped)
    is_step_line = is_step_indented(line) or any(
        stripped.lower().startswith(f"{kw.lower()} ") or stripped.lower() == kw.lower()
        for kw in KEYWORDS
    )

    if not stripped or stripped.startswith("#"):
        if line.strip() == "" and column >= indent_len:
            if is_step_line or indent_len == 0:
                return indent_len, column, list(STEP_SNIPPETS) + _keyword_candidates("")
            return indent_len, column, _keyword_candidates("")
        return column, column, []

    if _HEADER_RE.match(stripped) and not is_step_indented(line):
        prefix = stripped
        matches = _header_candidates(prefix)
        return indent_len, column, matches

    if not is_step_line:
        return column, column, []

    match = _KEYWORD_RE.match(stripped)
    if not match:
        return column, column, []

    keyword = match.group(1) or ""
    body = match.group(2) or ""
    body_offset = indent_len + len(stripped) - len(body)

    if keyword:
        keyword_end = _keyword_end_column(line, indent_len, keyword)
        if column <= keyword_end:
            prefix = stripped[: max(0, column - indent_len)]
            return indent_len, column, _keyword_candidates(prefix.strip())
        body_prefix = line[body_offset:column]
    else:
        line_prefix = stripped[: column - indent_len]
        if " " not in line_prefix.rstrip():
            matches = _keyword_candidates(line_prefix.strip())
            if matches:
                return indent_len, column, matches
        body_prefix = line[body_offset:column]

    body_prefix = body_prefix.lstrip()
    if not body_prefix:
        if keyword:
            return body_offset, column, list(STEP_SNIPPETS)
        return indent_len, column, _keyword_candidates("")

    matches = _step_candidates(body_prefix)
    start = body_offset + (len(body[: column - body_offset]) - len(body_prefix))
    return start, column, matches
