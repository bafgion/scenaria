"""Generated run variables."""

from __future__ import annotations

import re

import pytest

from app.run_variables import (
    RunContext,
    generate_bank_account,
    generate_inn,
    generate_ogrnip,
    generate_phone,
    normalize_generator_name,
)


def test_normalize_generator_aliases() -> None:
    assert normalize_generator_name("телефон") == "phone"
    assert normalize_generator_name("имя") == "first_name"
    assert normalize_generator_name("фамилия") == "last_name"
    assert normalize_generator_name("отчество") == "patronymic"
    assert normalize_generator_name("ИНН") == "inn"
    assert normalize_generator_name("расчётный счёт") == "bank_account"
    assert normalize_generator_name("огрнип") == "ogrnip"


def test_run_context_reuses_values_within_run() -> None:
    ctx = RunContext(seed=1)
    first = ctx.generate("phone")
    second = ctx.generate("phone")
    assert first == second
    assert ctx.resolve_text("{{phone}}") == first


def test_run_context_new_value_each_generator() -> None:
    ctx = RunContext(seed=2)
    phone = ctx.generate("phone")
    first = ctx.generate("first_name")
    assert phone != first


def test_person_fields_are_gender_consistent() -> None:
    ctx = RunContext(seed=3)
    first = ctx.generate("first_name")
    last = ctx.generate("last_name")
    patronymic = ctx.generate("patronymic")
    female_last = last.endswith("а")
    female_pat = patronymic.endswith("на")
    male_pat = patronymic.endswith("ич")
    assert female_last == female_pat or (not female_last and male_pat)
    assert first
    assert last
    assert patronymic


def test_generated_formats() -> None:
    import random

    rng = random.Random(42)
    phone = generate_phone(rng)
    inn = generate_inn(rng)
    account = generate_bank_account(rng)
    ogrnip = generate_ogrnip(rng)

    assert re.fullmatch(r"\+79\d{9}", phone)
    assert len(inn) == 12 and inn.isdigit()
    assert len(account) == 20 and account.isdigit()
    assert len(ogrnip) == 15 and ogrnip.startswith("3")


def test_inn_checksum_valid() -> None:
    import random

    from app.run_variables import _checksum_digit

    rng = random.Random(7)
    for _ in range(20):
        digits = [rng.randint(0, 9) for _ in range(10)]
        digits.append(_checksum_digit(digits, [7, 2, 4, 10, 3, 5, 9, 4, 6, 8]))
        digits.append(_checksum_digit(digits, [3, 7, 2, 4, 10, 3, 5, 9, 4, 6, 8]))
        inn = "".join(str(d) for d in digits)
        assert len(inn) == 12


def test_unknown_generator_raises() -> None:
    ctx = RunContext()
    with pytest.raises(ValueError, match="Неизвестный генератор"):
        ctx.generate("unknown")
