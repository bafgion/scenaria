"""Run context, variables, generators, and playback condition helpers."""

from __future__ import annotations

import os
import random
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from playwright.sync_api import Page

_PLACEHOLDER_RE = re.compile(r"\{\{\s*([a-zA-Z0-9_:]+)\s*\}\}")

GENERATOR_ALIASES: dict[str, str] = {
    "phone": "phone",
    "tel": "phone",
    "телефон": "phone",
    "first_name": "first_name",
    "firstname": "first_name",
    "имя": "first_name",
    "name": "first_name",
    "last_name": "last_name",
    "lastname": "last_name",
    "surname": "last_name",
    "фамилия": "last_name",
    "patronymic": "patronymic",
    "middlename": "patronymic",
    "middle_name": "patronymic",
    "отчество": "patronymic",
    "address": "address",
    "адрес": "address",
    "inn": "inn",
    "инн": "inn",
    "bank_account": "bank_account",
    "account": "bank_account",
    "rs": "bank_account",
    "р/с": "bank_account",
    "расчетный счет": "bank_account",
    "расчётный счёт": "bank_account",
    "расчетныйсчет": "bank_account",
    "огрнип": "ogrnip",
    "ogrnip": "ogrnip",
}

GENERATOR_GHERKIN_PHRASES: dict[str, str] = {
    "phone": "случайный телефон",
    "first_name": "случайное имя",
    "last_name": "случайную фамилию",
    "patronymic": "случайное отчество",
    "address": "случайный адрес",
    "inn": "случайный инн",
    "bank_account": "случайный расчётный счёт",
    "ogrnip": "случайный огрнип",
}

GENERATOR_PLAY_LABELS: dict[str, str] = {
    "phone": "Телефон",
    "first_name": "Имя",
    "last_name": "Фамилия",
    "patronymic": "Отчество",
    "address": "Адрес",
    "inn": "ИНН",
    "bank_account": "Расчётный счёт",
    "ogrnip": "ОГРНИП",
}


def generator_play_log_label(generator: str, value: str) -> str:
    name = GENERATOR_PLAY_LABELS.get(generator, generator)
    return f"{name}: {value}"

_MALE_FIRST_NAMES = ("Иван", "Алексей", "Дмитрий", "Сергей", "Андрей", "Михаил", "Павел")
_FEMALE_FIRST_NAMES = ("Анна", "Мария", "Елена", "Ольга", "Наталья", "Татьяна", "Ирина")
_MALE_LAST_NAMES = ("Иванов", "Петров", "Смирнов", "Кузнецов", "Попов", "Соколов", "Лебедев")
_FEMALE_LAST_NAMES = ("Иванова", "Петрова", "Смирнова", "Кузнецова", "Попова", "Соколова", "Лебедева")
_MALE_PATRONYMICS = ("Иванович", "Петрович", "Сергеевич", "Алексеевич", "Дмитриевич", "Андреевич")
_FEMALE_PATRONYMICS = ("Ивановна", "Петровна", "Сергеевна", "Алексеевна", "Дмитриевна", "Андреевна")
_STREETS = (
    "Ленина",
    "Пушкина",
    "Гагарина",
    "Советская",
    "Мира",
    "Тверская",
    "Садовая",
)
_CITIES = ("Москва", "Санкт-Петербург", "Казань", "Новосибирск", "Екатеринбург")

_PERSON_GENERATORS = frozenset({"first_name", "last_name", "patronymic"})


def normalize_generator_name(raw: str) -> str | None:
    key = str(raw or "").strip().lower().replace("ё", "е")
    key = re.sub(r"\s+", " ", key)
    compact = key.replace(" ", "")
    return GENERATOR_ALIASES.get(key) or GENERATOR_ALIASES.get(compact)


def generator_gherkin_phrase(generator: str) -> str:
    return GENERATOR_GHERKIN_PHRASES.get(generator, f"случайный {generator}")


def _checksum_digit(digits: list[int], weights: list[int]) -> int:
    total = sum(d * w for d, w in zip(digits, weights, strict=True))
    return total % 11 % 10


def _generate_person(rng: random.Random) -> tuple[str, str, str]:
    female = rng.choice((True, False))
    if female:
        first = rng.choice(_FEMALE_FIRST_NAMES)
        last = rng.choice(_FEMALE_LAST_NAMES)
        patronymic = rng.choice(_FEMALE_PATRONYMICS)
    else:
        first = rng.choice(_MALE_FIRST_NAMES)
        last = rng.choice(_MALE_LAST_NAMES)
        patronymic = rng.choice(_MALE_PATRONYMICS)
    return first, last, patronymic


def generate_phone(rng: random.Random) -> str:
    prefix = "9"
    tail = "".join(str(rng.randint(0, 9)) for _ in range(9))
    return f"+7{prefix}{tail}"


def generate_address(rng: random.Random) -> str:
    city = rng.choice(_CITIES)
    street = rng.choice(_STREETS)
    house = rng.randint(1, 120)
    flat = rng.randint(1, 200)
    return f"г. {city}, ул. {street}, д. {house}, кв. {flat}"


def generate_inn(rng: random.Random) -> str:
    digits = [rng.randint(0, 9) for _ in range(10)]
    digits.append(_checksum_digit(digits, [7, 2, 4, 10, 3, 5, 9, 4, 6, 8]))
    digits.append(_checksum_digit(digits, [3, 7, 2, 4, 10, 3, 5, 9, 4, 6, 8]))
    return "".join(str(d) for d in digits)


def generate_bank_account(rng: random.Random) -> str:
    prefix = "40817810"
    tail = "".join(str(rng.randint(0, 9)) for _ in range(12))
    return f"{prefix}{tail}"


def generate_ogrnip(rng: random.Random) -> str:
    digits = [3, *([rng.randint(0, 9) for _ in range(13)])]
    number = int("".join(str(d) for d in digits))
    digits.append(number % 13 % 10)
    return "".join(str(d) for d in digits)


_GENERATORS: dict[str, Callable[[random.Random], str]] = {
    "phone": generate_phone,
    "address": generate_address,
    "inn": generate_inn,
    "bank_account": generate_bank_account,
    "ogrnip": generate_ogrnip,
}


@dataclass
class RunContext:
    """Stores generators, user variables, and download state for one scenario run."""

    seed: int | None = None
    project_root: Path | None = None
    _values: dict[str, str] = field(default_factory=dict)
    _variables: dict[str, str] = field(default_factory=dict)
    _download_dir: Path | None = field(default=None, repr=False)
    _last_download: Path | None = field(default=None, repr=False)
    _rng: random.Random = field(init=False)
    _person: tuple[str, str, str] | None = field(default=None, repr=False)
    _page: Any = field(default=None, repr=False, compare=False)

    def __post_init__(self) -> None:
        self._rng = random.Random(self.seed)

    def bind_page(self, page: Any) -> None:
        self._page = page

    def current_page(self, fallback: Any) -> Any:
        return self._page or fallback

    def set_current_page(self, page: Any) -> None:
        self._page = page

    def set_initial_variables(self, values: dict[str, str] | None) -> None:
        if not values:
            return
        for key, value in values.items():
            name = str(key).strip()
            if name:
                self._variables[name] = str(value)

    def remember(self, name: str, value: str) -> None:
        key = str(name).strip()
        if not key:
            raise ValueError("Имя переменной не может быть пустым")
        self._variables[key] = str(value)

    def get_variable(self, name: str) -> str | None:
        return self._variables.get(str(name).strip())

    def set_download_dir(self, directory: Path) -> None:
        self._download_dir = directory

    def download_dir(self) -> Path:
        if self._download_dir is None:
            from app.download_helpers import new_download_run_dir

            _, directory = new_download_run_dir()
            self._download_dir = directory
        return self._download_dir

    def set_last_download(self, path: Path) -> None:
        self._last_download = path

    @property
    def last_download(self) -> Path | None:
        return self._last_download

    def _person_parts(self) -> tuple[str, str, str]:
        if self._person is None:
            self._person = _generate_person(self._rng)
        return self._person

    def _generate_person_field(self, canonical: str) -> str:
        first, last, patronymic = self._person_parts()
        mapping = {
            "first_name": first,
            "last_name": last,
            "patronymic": patronymic,
        }
        value = mapping[canonical]
        self._values[canonical] = value
        return value

    def get(self, generator: str) -> str | None:
        canonical = normalize_generator_name(generator)
        if canonical is None:
            return None
        return self._values.get(canonical)

    def generate(self, generator: str) -> str:
        canonical = normalize_generator_name(generator)
        if canonical is None:
            raise ValueError(f"Неизвестный генератор: {generator}")
        if canonical in self._values:
            return self._values[canonical]
        if canonical in _PERSON_GENERATORS:
            return self._generate_person_field(canonical)
        factory = _GENERATORS.get(canonical)
        if factory is None:
            raise ValueError(f"Неизвестный генератор: {generator}")
        value = factory(self._rng)
        self._values[canonical] = value
        return value

    def resolve_text(self, text: str) -> str:
        if not text or "{{" not in text:
            return text

        def replace(match: re.Match[str]) -> str:
            key = match.group(1).strip()
            lower = key.lower()
            if lower.startswith("env:"):
                env_name = key[4:].strip()
                value = os.environ.get(env_name, "")
                if not value:
                    raise ValueError(f"Переменная окружения не задана: {env_name}")
                return value
            if key in self._variables:
                return self._variables[key]
            canonical = normalize_generator_name(key)
            if canonical is not None:
                return self.generate(key)
            raise ValueError(f"Неизвестная переменная: {key}")

        return _PLACEHOLDER_RE.sub(replace, text)

    def generator_label(self, generator: str) -> str:
        canonical = normalize_generator_name(generator) or generator
        return GENERATOR_GHERKIN_PHRASES.get(canonical, canonical)


def resolve_email_for_code_prompt(
    page: Page,
    step: dict,
    prior_steps: list[dict],
    run_context: RunContext | None = None,
) -> str:
    from app.player_step_helpers import (
        _EMAIL_FIELD_SELECTORS,
        _extract_email_from_page_text,
        _looks_like_email,
        _selector_suggests_email,
    )

    explicit = str(step.get("email", "") or "").strip()
    if explicit:
        if run_context is not None and "{{" in explicit:
            return run_context.resolve_text(explicit)
        return explicit

    if run_context is not None:
        for key in ("email", "почта", "mail"):
            value = run_context.get(key)
            if value and _looks_like_email(value):
                return value

    for prev in reversed(prior_steps):
        if prev.get("action") not in {"fill", "fill_generated"}:
            continue
        if prev.get("action") == "fill_generated" and prev.get("generator") == "email":
            if run_context is not None:
                try:
                    return run_context.generate("email")
                except ValueError:
                    pass
            continue
        value = str(prev.get("value", "") or "").strip()
        selector = str(prev.get("selector", "") or "")
        if _looks_like_email(value):
            return value
        if value and _selector_suggests_email(selector):
            return value

    page_text_email = _extract_email_from_page_text(page)
    if page_text_email:
        return page_text_email

    for selector in _EMAIL_FIELD_SELECTORS:
        try:
            locator = page.locator(selector).first
            if locator.count() == 0:
                continue
            value = str(locator.input_value(timeout=2000) or "").strip()
            if _looks_like_email(value):
                return value
        except Exception:  # noqa: BLE001
            continue

    return ""
def _evaluate_condition(page: Page, condition: dict, ctx: RunContext) -> bool:
    kind = str(condition.get("type", "") or "")
    try:
        if kind == "visible":
            selector = ctx.resolve_text(str(condition.get("selector", "") or ""))
            return page.locator(selector).first.is_visible()
        if kind == "hidden":
            selector = ctx.resolve_text(str(condition.get("selector", "") or ""))
            locator = page.locator(selector).first
            return not locator.is_visible()
        if kind == "url_contains":
            needle = ctx.resolve_text(str(condition.get("value", "") or ""))
            return needle in page.url
        if kind == "page_text":
            needle = ctx.resolve_text(str(condition.get("value", "") or ""))
            return needle in page.content()
    except Exception:  # noqa: BLE001
        return False
    return False


def prepare_run_context(
    scenario: dict,
    page: Page,
    *,
    project_root: Path | None = None,
) -> RunContext:
    from app.download_helpers import new_download_run_dir

    ctx = RunContext(seed=scenario.get("runSeed"), project_root=project_root)
    ctx.set_initial_variables(dict(scenario.get("variables") or {}))
    ctx.bind_page(page)
    _, download_dir = new_download_run_dir()
    ctx.set_download_dir(download_dir)
    return ctx
