"""Per-run generated values for scenario playback."""

from __future__ import annotations

import random
import re
from collections.abc import Callable
from dataclasses import dataclass, field

_PLACEHOLDER_RE = re.compile(r"\{\{\s*([a-zA-Z0-9_]+)\s*\}\}")

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
    """Stores generated values for one scenario run."""

    seed: int | None = None
    _values: dict[str, str] = field(default_factory=dict)
    _rng: random.Random = field(init=False)
    _person: tuple[str, str, str] | None = field(default=None, repr=False)

    def __post_init__(self) -> None:
        self._rng = random.Random(self.seed)

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
            key = match.group(1)
            return self.generate(key)

        return _PLACEHOLDER_RE.sub(replace, text)

    def generator_label(self, generator: str) -> str:
        canonical = normalize_generator_name(generator) or generator
        return GENERATOR_GHERKIN_PHRASES.get(canonical, canonical)
