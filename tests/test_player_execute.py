"""Unit tests for scenario step execution."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.player import execute_step, fill_verification_code, resolve_email_for_code_prompt
from app.run_variables import RunContext


@pytest.fixture
def page() -> MagicMock:
    mock = MagicMock()
    mock.url = "https://example.com"
    locator = MagicMock()
    mock.locator.return_value = locator
    locator.first = locator
    return mock


def test_execute_goto(page: MagicMock) -> None:
    logs: list[str] = []
    execute_step(page, {"action": "goto", "url": "https://example.com/page"}, 1, logs.append)
    page.goto.assert_called_once()
    assert "domcontentloaded" in str(page.goto.call_args)


def test_execute_click_logs_single_line_without_menu_hover(page: MagicMock) -> None:
    logs: list[str] = []
    execute_step(
        page,
        {"action": "click", "selector": 'button:has-text("Далее")'},
        12,
        logs.append,
        highlight=False,
    )
    assert logs == ['12. Клик «Далее»']


def test_execute_fill_generated_logs_short_label(page: MagicMock) -> None:
    logs: list[str] = []
    execute_step(
        page,
        {
            "action": "fill_generated",
            "generator": "last_name",
            "selector": 'label:has-text("Фамилия *")',
            "text": "Фамилия *",
        },
        3,
        logs.append,
        highlight=False,
    )
    assert len(logs) == 1
    assert logs[0].startswith("3. Фамилия:")
    assert "случайную" not in logs[0]


def test_execute_press_keyboard(page: MagicMock) -> None:
    logs: list[str] = []
    execute_step(page, {"action": "press", "key": "Enter"}, 1, logs.append, highlight=False)
    page.keyboard.press.assert_called_once_with("Enter")


def test_execute_assert_hidden_visible_raises(page: MagicMock) -> None:
    locator = page.locator.return_value.first
    locator.count.return_value = 1
    locator.is_visible.return_value = True
    with pytest.raises(AssertionError):
        execute_step(
            page,
            {"action": "assert_hidden", "selector": ".modal"},
            1,
            lambda _m: None,
            highlight=False,
        )


def test_execute_scroll_to(page: MagicMock) -> None:
    logs: list[str] = []
    execute_step(
        page,
        {"action": "scroll_to", "selector": "#footer"},
        1,
        logs.append,
        highlight=False,
    )
    page.locator.return_value.first.scroll_into_view_if_needed.assert_called_once()


def test_execute_draw_signature(page: MagicMock) -> None:
    locator = page.locator.return_value.first
    locator.bounding_box.return_value = {"x": 10, "y": 20, "width": 200, "height": 100}
    execute_step(
        page,
        {"action": "draw_signature", "selector": "canvas"},
        1,
        lambda _m: None,
        highlight=False,
    )
    page.mouse.down.assert_called_once()
    page.mouse.up.assert_called_once()


def test_execute_close_browser(page: MagicMock) -> None:
    closed: list[str] = []

    def on_close() -> None:
        closed.append("yes")

    execute_step(
        page,
        {"action": "close_browser"},
        1,
        lambda _m: None,
        highlight=False,
        on_close_browser=on_close,
    )
    assert closed == ["yes"]


def test_execute_reload(page: MagicMock) -> None:
    execute_step(page, {"action": "reload"}, 1, lambda _m: None, highlight=False)
    page.reload.assert_called_once()


def test_resolve_email_from_step_field() -> None:
    page = MagicMock()
    step = {"action": "prompt_email_code", "email": "qa@test.com", "selector": "input#otp"}
    assert resolve_email_for_code_prompt(page, step, []) == "qa@test.com"


def test_resolve_email_from_prior_fill(page: MagicMock) -> None:
    step = {"action": "prompt_email_code", "selector": "input#otp"}
    prior = [{"action": "fill", "value": "user@example.com", "selector": "input#email"}]
    assert resolve_email_for_code_prompt(page, step, prior) == "user@example.com"


def test_resolve_email_from_page_input(page: MagicMock) -> None:
    body = MagicMock()
    body.inner_text.return_value = ""

    field = MagicMock()
    field.first = field
    field.count.return_value = 1
    field.input_value.return_value = "inbox@shop.ru"

    def locator_side_effect(selector: str) -> MagicMock:
        if selector == "body":
            return body
        return field

    page.locator.side_effect = locator_side_effect

    step = {"action": "prompt_email_code", "selector": "input#otp"}
    assert resolve_email_for_code_prompt(page, step, []) == "inbox@shop.ru"


def test_resolve_email_from_page_text(page: MagicMock) -> None:
    body = MagicMock()
    page.locator.return_value = body
    body.inner_text.return_value = (
        "Мы отправили код подтверждения по адресу test12@mail.ru. "
        "Если вы не получили письмо, проверьте папку Спам"
    )

    step = {"action": "prompt_email_code", "selector": "input.otp"}
    assert resolve_email_for_code_prompt(page, step, []) == "test12@mail.ru"


def test_fill_verification_code_segmented_keyboard(page: MagicMock) -> None:
    locator = MagicMock()
    page.locator.return_value = locator
    locator.count.return_value = 6
    locator.nth.return_value = locator
    locator.input_value.side_effect = ["1", "2", "3", "4", "5", "6"]

    mode = fill_verification_code(page, "input.pin-digit", "123456", digits=6)
    assert mode == "segmented-keyboard:6"
    page.keyboard.type.assert_called_once_with("123456", delay=80)
    assert locator.fill.call_count == 0


def test_fill_verification_code_segmented_fill(page: MagicMock) -> None:
    locator = MagicMock()
    page.locator.return_value = locator
    locator.count.return_value = 6
    locator.nth.return_value = locator
    locator.input_value.side_effect = ["1", "2", "3", "4", "5", "6"]

    mode = fill_verification_code(
        page,
        "input.pin-digit",
        "123456",
        digits=6,
        input_method="fill",
    )
    assert mode == "segmented-fill:6"
    assert locator.fill.call_count == 6
    page.keyboard.type.assert_not_called()


def test_fill_verification_code_single(page: MagicMock) -> None:
    locator = MagicMock()
    page.locator.return_value = locator
    locator.count.return_value = 1
    locator.first = locator

    mode = fill_verification_code(page, "input#code", "123456")
    assert mode == "single"
    locator.first.fill.assert_called_once_with("123456", timeout=15000)


def test_fill_verification_code_after_auto_submit(page: MagicMock) -> None:
    locator = MagicMock()
    page.locator.return_value = locator
    locator.count.return_value = 0

    mode = fill_verification_code(
        page,
        "input.pin-digit",
        "123456",
        digits=6,
        allow_advancing=True,
    )
    assert mode == "already-submitted"


def test_fill_verification_code_segmented_auto_submit_after_keyboard(page: MagicMock) -> None:
    locator = MagicMock()
    page.locator.return_value = locator
    locator.count.side_effect = [6, 0]
    locator.nth.return_value = locator
    locator.first = locator
    locator.input_value.return_value = ""

    mode = fill_verification_code(page, "input.pin-digit", "123456", digits=6)
    assert mode == "segmented-keyboard:6-submit"
    page.keyboard.type.assert_called_once()


def test_execute_fill_generated(page: MagicMock) -> None:
    logs: list[str] = []
    ctx = RunContext(seed=5)
    execute_step(
        page,
        {"action": "fill_generated", "generator": "phone", "selector": "input#tel"},
        1,
        logs.append,
        highlight=False,
        run_context=ctx,
    )
    locator = page.locator.return_value.first
    locator.fill.assert_called_once()
    value = locator.fill.call_args.args[0]
    assert value.startswith("+79")


def test_execute_fill_placeholder(page: MagicMock) -> None:
    logs: list[str] = []
    ctx = RunContext(seed=6)
    execute_step(
        page,
        {"action": "fill", "value": "{{inn}}", "selector": "input#inn"},
        1,
        logs.append,
        highlight=False,
        run_context=ctx,
    )
    value = page.locator.return_value.first.fill.call_args.args[0]
    assert len(value) == 12 and value.isdigit()


def test_prompt_email_code_uses_env_var_in_headless(page: MagicMock, monkeypatch) -> None:
    monkeypatch.setenv("SCENARIA_EMAIL_CODE", "123456")
    field = MagicMock()
    field.first = field
    field.count.return_value = 1

    def locator_side_effect(selector: str) -> MagicMock:
        if selector == "input#otp":
            return field
        return page.locator.return_value

    page.locator.side_effect = locator_side_effect
    logs: list[str] = []
    execute_step(
        page,
        {"action": "prompt_email_code", "email": "qa@test.com", "selector": "input#otp"},
        1,
        logs.append,
        highlight=False,
        interactive=False,
    )
    assert any("SCENARIA_EMAIL_CODE" in line for line in logs)

