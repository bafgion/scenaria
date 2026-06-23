"""Tests for Russian Gherkin parser/serializer."""

from __future__ import annotations

import pytest

from app.gherkin_ru import (
    STEP_INDENT,
    GherkinParseError,
    gherkin_to_steps,
    merge_steps_into_feature_text,
    parse_feature_structure,
    steps_to_gherkin,
    suggest_step_keyword,
)

TAB = STEP_INDENT


def test_parse_goto_click_fill_select_hover() -> None:
    text = (
        "Функционал: UI\n"
        "Сценарий: Тест\n"
        f'{TAB}Допустим открыт "https://shop.com"\n'
        f'{TAB}И нажимаю "button.buy"\n'
        f'{TAB}И навожу "nav.menu"\n'
        f'{TAB}И ввожу "test" в "input#email"\n'
        f'{TAB}И выбираю "M" в "select#size"'
    )
    steps = gherkin_to_steps(text)
    assert steps == [
        {"action": "goto", "url": "https://shop.com"},
        {"action": "click", "selector": "button.buy"},
        {"action": "hover", "selector": "nav.menu"},
        {"action": "fill", "value": "test", "selector": "input#email"},
        {"action": "select", "value": "M", "selector": "select#size"},
    ]


def test_parse_legacy_two_space_indent() -> None:
    text = '  Допустим открыт "https://legacy.com"'
    steps = gherkin_to_steps(text)
    assert steps == [{"action": "goto", "url": "https://legacy.com"}]


def test_steps_to_gherkin_uses_tab_indent() -> None:
    text = steps_to_gherkin([{"action": "goto", "url": "https://a.com"}], scenario_name="T")
    assert f"{TAB}Допустим открыт" in text
    assert "  Допустим" not in text


def test_parse_keywords_and_escaped_quotes() -> None:
    text = f'{TAB}Когда ввожу "say \\"hi\\"" в "textarea.msg"'
    steps = gherkin_to_steps(text)
    assert steps == [{"action": "fill", "value": 'say "hi"', "selector": "textarea.msg"}]


def test_parse_fill_with_guillemets_inside_value() -> None:
    text = f'{TAB}И ввожу "АО «Тинькофф Банк»" в "label:has-text(\\"Наименование банка\\")"'
    steps = gherkin_to_steps(text)
    assert steps[-1] == {
        "action": "fill",
        "value": "АО «Тинькофф Банк»",
        "selector": 'label:has-text("Наименование банка")',
    }


def test_parse_invalid_step_raises() -> None:
    with pytest.raises(GherkinParseError) as exc:
        gherkin_to_steps(f"{TAB}И кликаю по кнопке")
    assert exc.value.line_no == 1


def test_roundtrip_steps_to_gherkin() -> None:
    steps = [
        {"action": "goto", "url": "https://a.com"},
        {"action": "hover", "selector": "a.menu"},
        {"action": "click", "selector": "a.item", "hoverSelector": "a.menu"},
        {"action": "fill", "value": "x", "selector": "#q"},
    ]
    text = steps_to_gherkin(steps, scenario_name="Checkout")
    reparsed = gherkin_to_steps(text)
    assert reparsed[0] == steps[0]
    assert reparsed[1] == steps[1]
    assert reparsed[2]["action"] == "click"
    assert reparsed[2]["selector"] == "a.item"
    assert reparsed[3] == steps[3]


def test_parse_assert_steps() -> None:
    text = (
        "Функционал: UI\n"
        "Сценарий: Asserts\n"
        f'{TAB}Допустим открыт "https://shop.com"\n'
        f'{TAB}И вижу "h1.title"\n'
        f'{TAB}И проверяю текст "Корзина" в ".cart-label"\n'
        f'{TAB}И проверяю url "https://shop.com/cart"'
    )
    steps = gherkin_to_steps(text)
    assert steps == [
        {"action": "goto", "url": "https://shop.com"},
        {"action": "assert_visible", "selector": "h1.title"},
        {"action": "assert_text", "value": "Корзина", "selector": ".cart-label"},
        {"action": "assert_url", "url": "https://shop.com/cart"},
    ]


def test_roundtrip_assert_steps() -> None:
    steps = [
        {"action": "goto", "url": "https://a.com"},
        {"action": "assert_visible", "selector": "#ok"},
        {"action": "assert_text", "value": "Done", "selector": ".msg"},
        {"action": "assert_url", "url": "https://a.com/done"},
    ]
    text = steps_to_gherkin(steps, scenario_name="Asserts")
    reparsed = gherkin_to_steps(text)
    assert reparsed == steps


def test_parse_wait_steps() -> None:
    text = (
        f'{TAB}Допустим открыт "https://shop.com"\n'
        f"{TAB}И жду 2 сек\n"
        f"{TAB}И жду 500 мс\n"
        f'{TAB}И жду появления "button.ready"'
    )
    steps = gherkin_to_steps(text)
    assert steps == [
        {"action": "goto", "url": "https://shop.com"},
        {"action": "wait", "ms": 2000},
        {"action": "wait", "ms": 500},
        {"action": "wait_for", "selector": "button.ready"},
    ]


def test_roundtrip_wait_steps() -> None:
    steps = [
        {"action": "goto", "url": "https://a.com"},
        {"action": "wait", "ms": 3000},
        {"action": "wait_for", "selector": "#loader"},
    ]
    text = steps_to_gherkin(steps, scenario_name="Waits")
    reparsed = gherkin_to_steps(text)
    assert reparsed == steps


def test_serialize_inserts_hover_before_click_when_needed() -> None:
    steps = [
        {"action": "goto", "url": "https://a.com"},
        {"action": "click", "selector": "a.sub", "hoverSelector": "a.menu"},
    ]
    text = steps_to_gherkin(steps)
    assert 'навожу "a.menu"' in text
    assert 'нажимаю "a.sub"' in text


def test_parse_extended_steps() -> None:
    text = (
        f'{TAB}Допустим открыт "https://site.com"\n'
        f'{TAB}И дважды нажимаю ".item"\n'
        f'{TAB}И нажимаю клавишу "Enter"\n'
        f'{TAB}И нажимаю клавишу "Tab" в "input#name"\n'
        f'{TAB}И очищаю "input#search"\n'
        f'{TAB}И отмечаю "input#terms"\n'
        f'{TAB}И снимаю отметку с "input#spam"\n'
        f'{TAB}И загружаю файл "C:\\\\docs\\\\cv.pdf" в "input[type=file]"\n'
        f'{TAB}И скроллю к "footer"\n'
        f"{TAB}И обновляю страницу\n"
        f"{TAB}И возвращаюсь назад\n"
        f'{TAB}И не вижу ".modal"\n'
        f'{TAB}И жду исчезновения ".spinner"\n'
        f'{TAB}И рисую подпись в "canvas"\n'
        f'{TAB}И нажимаю "button.next"\n'
        f"{TAB}И закрываю браузер"
    )
    steps = gherkin_to_steps(text)
    assert steps == [
        {"action": "goto", "url": "https://site.com"},
        {"action": "double_click", "selector": ".item"},
        {"action": "press", "key": "Enter"},
        {"action": "press", "key": "Tab", "selector": "input#name"},
        {"action": "clear", "selector": "input#search"},
        {"action": "check", "selector": "input#terms"},
        {"action": "uncheck", "selector": "input#spam"},
        {"action": "upload", "path": "C:\\docs\\cv.pdf", "selector": "input[type=file]"},
        {"action": "scroll_to", "selector": "footer"},
        {"action": "reload"},
        {"action": "go_back"},
        {"action": "assert_hidden", "selector": ".modal"},
        {"action": "wait_for_hidden", "selector": ".spinner"},
        {"action": "draw_signature", "selector": "canvas"},
        {"action": "click", "selector": "button.next"},
        {"action": "close_browser"},
    ]


def test_roundtrip_close_browser() -> None:
    steps = [
        {"action": "goto", "url": "https://a.com"},
        {"action": "close_browser"},
    ]
    text = steps_to_gherkin(steps, scenario_name="Close")
    reparsed = gherkin_to_steps(text)
    assert reparsed == steps


def test_roundtrip_extended_steps() -> None:
    steps = [
        {"action": "goto", "url": "https://a.com"},
        {"action": "double_click", "selector": ".row"},
        {"action": "press", "key": "Escape"},
        {"action": "press", "key": "Enter", "selector": "#form"},
        {"action": "clear", "selector": "#q"},
        {"action": "check", "selector": "#ok"},
        {"action": "uncheck", "selector": "#ads"},
        {"action": "upload", "path": "/tmp/a.png", "selector": "input.file"},
        {"action": "scroll_to", "selector": "#bottom"},
        {"action": "reload"},
        {"action": "go_back"},
        {"action": "assert_hidden", "selector": ".toast"},
        {"action": "wait_for_hidden", "selector": ".loader"},
    ]
    text = steps_to_gherkin(steps, scenario_name="Extended")
    reparsed = gherkin_to_steps(text)
    assert reparsed == steps


def test_parse_email_code_step() -> None:
    text = (
        "Функционал: Auth\n"
        "Сценарий: OTP\n"
        f'{TAB}Допустим открыт "https://shop.com/login"\n'
        f'{TAB}И ввожу код из почты "qa@test.com" в "input#otp"\n'
        f'{TAB}И ввожу код из почты в "input[name=code]"'
    )
    steps = gherkin_to_steps(text)
    assert steps[1] == {
        "action": "prompt_email_code",
        "email": "qa@test.com",
        "selector": "input#otp",
    }
    assert steps[2] == {"action": "prompt_email_code", "selector": "input[name=code]"}


def test_email_code_step_roundtrip() -> None:
    steps = [
        {"action": "goto", "url": "https://shop.com"},
        {"action": "prompt_email_code", "email": "qa@test.com", "selector": "input#otp"},
        {"action": "prompt_email_code", "selector": "input#otp"},
        {"action": "prompt_email_code", "digits": 6, "selector": "input.otp-cell"},
    ]
    text = steps_to_gherkin(steps, scenario_name="OTP")
    reparsed = gherkin_to_steps(text)
    assert reparsed == steps


def test_parse_email_code_segmented_step() -> None:
    text = (
        f'{TAB}И ввожу код из почты в 6 полей "input.otp-cell"\n'
        f'{TAB}И ввожу код из почты "qa@test.com" в 4 полей "input.pin"\n'
        f'{TAB}И ввожу код из почты с клавиатуры в 6 полей "input.pin-digit"\n'
        f'{TAB}И ввожу код из почты заполнением в "input#code"'
    )
    steps = gherkin_to_steps(text)
    assert steps[0] == {
        "action": "prompt_email_code",
        "digits": 6,
        "selector": "input.otp-cell",
    }
    assert steps[1] == {
        "action": "prompt_email_code",
        "email": "qa@test.com",
        "digits": 4,
        "selector": "input.pin",
    }
    assert steps[2] == {
        "action": "prompt_email_code",
        "digits": 6,
        "selector": "input.pin-digit",
        "inputMethod": "keyboard",
    }
    assert steps[3] == {
        "action": "prompt_email_code",
        "selector": "input#code",
        "inputMethod": "fill",
    }


def test_email_code_keyboard_roundtrip() -> None:
    steps = [
        {
            "action": "prompt_email_code",
            "digits": 6,
            "selector": "input.pin-digit",
            "inputMethod": "keyboard",
        }
    ]
    text = steps_to_gherkin(steps, scenario_name="OTP")
    reparsed = gherkin_to_steps(text)
    assert reparsed == steps


def test_suggest_step_keyword_for_new_scenario() -> None:
    assert (
        suggest_step_keyword(current_line="", cursor_column=0, has_steps_before=False)
        == "Допустим"
    )


def test_suggest_step_keyword_after_existing_steps() -> None:
    assert (
        suggest_step_keyword(current_line="", cursor_column=0, has_steps_before=True)
        == "И"
    )
    assert (
        suggest_step_keyword(current_line="\t", cursor_column=1, has_steps_before=True)
        == "И"
    )


def test_parse_generated_fill_steps() -> None:
    text = (
        "Сценарий: Данные\n"
        f'{TAB}И ввожу случайный телефон в "input[type=tel]"\n'
        f'{TAB}И ввожу случайное имя в "input#firstName"\n'
        f'{TAB}И ввожу случайную фамилию в "input#lastName"\n'
        f'{TAB}И ввожу случайное отчество в "input#patronymic"\n'
        f'{TAB}И ввожу случайный инн в "input#inn"\n'
        f'{TAB}И ввожу случайный расчётный счёт в "input#account"\n'
        f'{TAB}И ввожу случайный огрнип в "input#ogrnip"\n'
        f'{TAB}И ввожу "{{{{phone}}}}" в "input#phone2"'
    )
    steps = gherkin_to_steps(text)
    assert steps[0] == {"action": "fill_generated", "generator": "phone", "selector": "input[type=tel]"}
    assert steps[1] == {"action": "fill_generated", "generator": "first_name", "selector": "input#firstName"}
    assert steps[2] == {"action": "fill_generated", "generator": "last_name", "selector": "input#lastName"}
    assert steps[3] == {"action": "fill_generated", "generator": "patronymic", "selector": "input#patronymic"}
    assert steps[4]["generator"] == "inn"
    assert steps[5]["generator"] == "bank_account"
    assert steps[6]["generator"] == "ogrnip"
    assert steps[7] == {"action": "fill", "value": "{{phone}}", "selector": "input#phone2"}


def test_roundtrip_generated_fill_steps() -> None:
    steps = [
        {"action": "fill_generated", "generator": "address", "selector": "textarea.addr"},
        {"action": "fill", "value": "{{inn}}", "selector": "input.inn"},
    ]
    text = steps_to_gherkin(steps, scenario_name="Генерация")
    reparsed = gherkin_to_steps(text)
    assert reparsed == steps


def test_suggest_step_keyword_on_step_line() -> None:
    line = f"{TAB}Допустим открыт \"https://shop.com\""
    assert (
        suggest_step_keyword(current_line=line, cursor_column=len(line), has_steps_before=False)
        == "И"
    )


def test_parse_tags_and_comments_ignored_for_steps() -> None:
    text = (
        "Функционал: UI\n"
        "@smoke\n"
        "@wip\n"
        "Сценарий: Checkout\n"
        "\t# Старт с главной\n"
        f'{TAB}Допустим открыт "https://shop.com"\n'
        f'{TAB}И нажимаю "button.buy"'
    )
    steps = gherkin_to_steps(text)
    assert steps == [
        {"action": "goto", "url": "https://shop.com"},
        {"action": "click", "selector": "button.buy"},
    ]
    structure = parse_feature_structure(text)
    assert structure.tags == ["smoke", "wip"]
    assert structure.before_steps == ["\t# Старт с главной"]


def test_steps_to_gherkin_with_tags() -> None:
    text = steps_to_gherkin(
        [{"action": "goto", "url": "https://a.com"}],
        scenario_name="T",
        tags=["smoke", "catalog"],
    )
    assert "@smoke" in text
    assert "@catalog" in text
    assert "Сценарий: T" in text


def test_merge_steps_preserves_comments_and_tags() -> None:
    source = (
        "Функционал: UI\n"
        "@smoke\n"
        "Сценарий: Old\n"
        "\t# before step\n"
        f'{TAB}Допустим открыт "https://old.com"\n'
    )
    merged = merge_steps_into_feature_text(
        source,
        [{"action": "goto", "url": "https://new.com"}],
        tags=["smoke"],
        scenario_name="New",
    )
    assert "@smoke" in merged
    assert "# before step" in merged
    assert "https://new.com" in merged
    assert "Сценарий: New" in merged


def test_parse_repairs_missing_closing_quote_on_last_line() -> None:
    from app.gherkin_ru import parse_gherkin_steps

    text = (
        "Функционал: UI\n"
        "Сценарий: T\n"
        f'{TAB}Допустим открыт "https://shop.com"\n'
        f'{TAB}И нажимаю "button:has-text(\\"Далее\\")'
    )
    steps, canonical = parse_gherkin_steps(text)
    assert len(steps) == 2
    assert steps[-1]["action"] == "click"
    assert canonical.endswith('"')
    assert gherkin_to_steps(canonical) == steps


def test_parse_repairs_missing_closing_quote_in_middle_of_scenario() -> None:
    from app.gherkin_ru import parse_gherkin_steps

    text = (
        "Функционал: UI\n"
        "Сценарий: T\n"
        f'{TAB}Допустим открыт "https://shop.com"\n'
        f'{TAB}И отмечаю "label:has-text(\\"Согласен\\")"\n'
        f'{TAB}И нажимаю "button:has-text(\\"Далее\\")'  # legacy: no closing quote
        f'\n{TAB}И нажимаю "button:has-text(\\"Далее\\")"\n'
    )
    steps, canonical = parse_gherkin_steps(text)
    assert len(steps) == 4
    assert steps[2]["action"] == "click"
    assert steps[2]["selector"] == 'button:has-text("Далее")'
    repaired_line = canonical.splitlines()[4]
    assert repaired_line.endswith('"')


def test_parse_normalizes_legacy_unescaped_has_text_quotes() -> None:
    from app.gherkin_ru import parse_gherkin_steps

    text = (
        "Функционал: UI\n"
        "Сценарий: T\n"
        f'{TAB}И отмечаю "label:has-text("Согласен с условиями Политики конфиденциальности")"\n'
        f'{TAB}И нажимаю "button:has-text("Далее")"\n'
        f'{TAB}И жду 1 сек\n'
        f'{TAB}И нажимаю "button:has-text(\\"Далее\\")"\n'
    )
    steps, canonical = parse_gherkin_steps(text)
    assert len(steps) == 4
    assert steps[0]["action"] == "check"
    assert steps[1]["selector"] == 'button:has-text("Далее")'
    assert '\\"Далее\\"' in canonical.splitlines()[3]
    assert ':has-text("Далее")' not in canonical


def test_parse_mixed_tab_and_space_step_indents() -> None:
    from app.gherkin_ru import parse_gherkin_steps

    text = (
        "Сценарий: T\n"
        f'{TAB}Допустим открыт "https://example.com"\n'
        f'    И нажимаю "button.next"\n'
        f'{TAB}И жду 1 сек\n'
    )
    steps = gherkin_to_steps(text)
    assert [step["action"] for step in steps] == ["goto", "click", "wait"]
    _, canonical = parse_gherkin_steps(text)
    assert canonical.splitlines()[2].startswith(f"{TAB}И нажимаю")


def test_coalesce_mixed_step_indents_in_text() -> None:
    from app.gherkin_ru import coalesce_mixed_step_indents_in_text

    text = (
        "Сценарий: T\n"
        f'{TAB}Допустим открыт "https://example.com"\n'
        f'    И нажимаю "#taxationSystem"\n'
    )
    coalesced = coalesce_mixed_step_indents_in_text(text)
    assert '    И нажимаю' not in coalesced
    assert f'{TAB}И нажимаю "#taxationSystem"' in coalesced
