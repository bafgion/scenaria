"""Execute a single recorded scenario step (T8a)."""

from __future__ import annotations

from collections.abc import Callable

from playwright.sync_api import Page

from app.download_helpers import file_contains_substring, save_playwright_download
from app.play_log import (
    format_click_log,
    format_fill_generated_log,
    format_fill_log,
    step_log_target,
)
from app.player_context import RunContext, _evaluate_condition, resolve_email_for_code_prompt
from app.player_highlight import _maybe_highlight, remove_highlight
from app.player_step_helpers import (
    LogCallback,
    _fill_locator,
    _otp_fields_visible,
    _prepare_click_target,
    _reveal_hover_menu,
    fill_verification_code,
)
from app.selector_resolve import resolve_chained_locator, resolve_hover_locator
from app.signature_draw import draw_signature_on_canvas
from app.steps import NAV_TIMEOUT_MS, NAV_WAIT_UNTIL, urls_match

CloseBrowserCallback = Callable[[], None]

def execute_step(
    page: Page,
    step: dict,
    index: int,
    on_log: LogCallback,
    *,
    highlight: bool = True,
    interactive: bool = True,
    prior_steps: list[dict] | None = None,
    on_close_browser: CloseBrowserCallback | None = None,
    run_context: RunContext | None = None,
) -> None:
    ctx = run_context or RunContext()
    page = ctx.current_page(page)
    action = step.get("action")

    if action == "if":
        condition = step.get("condition") or {}
        nested = list(step.get("steps") or [])
        if _evaluate_condition(page, condition, ctx):
            on_log(f"{index}. Если → выполняю блок ({len(nested)} шаг.)")
            for sub_index, sub_step in enumerate(nested, start=1):
                execute_step(
                    page,
                    sub_step,
                    index,
                    on_log,
                    highlight=highlight,
                    interactive=interactive,
                    prior_steps=prior_steps,
                    on_close_browser=on_close_browser,
                    run_context=ctx,
                )
        else:
            on_log(f"{index}. Если → пропуск блока")
        remove_highlight(page)
        return

    if action == "repeat":
        from app.settings import load_settings

        max_iterations = max(1, int(load_settings().get("max_loop_iterations", 100)))
        count = min(max(1, int(step.get("count") or 1)), max_iterations)
        nested = list(step.get("steps") or [])
        on_log(f"{index}. Повторяю {count} раз(а), {len(nested)} шаг. в теле")
        for iteration in range(1, count + 1):
            on_log(f"{index}.{iteration} итерация")
            for sub_step in nested:
                execute_step(
                    page,
                    sub_step,
                    index,
                    on_log,
                    highlight=highlight,
                    interactive=interactive,
                    prior_steps=prior_steps,
                    on_close_browser=on_close_browser,
                    run_context=ctx,
                )
        remove_highlight(page)
        return

    if action == "while":
        from app.settings import load_settings

        max_iterations = max(1, int(load_settings().get("max_loop_iterations", 100)))
        condition = step.get("condition") or {}
        nested = list(step.get("steps") or [])
        iterations = 0
        while _evaluate_condition(page, condition, ctx) and iterations < max_iterations:
            iterations += 1
            on_log(f"{index}.{iterations} Пока → тело ({len(nested)} шаг.)")
            for sub_step in nested:
                page = ctx.current_page(page)
                execute_step(
                    page,
                    sub_step,
                    index,
                    on_log,
                    highlight=highlight,
                    interactive=interactive,
                    prior_steps=prior_steps,
                    on_close_browser=on_close_browser,
                    run_context=ctx,
                )
        page = ctx.current_page(page)
        if iterations >= max_iterations and _evaluate_condition(page, condition, ctx):
            raise RuntimeError("Превышен лимит итераций цикла «пока»")
        on_log(f"{index}. Пока → завершено ({iterations} ит.)")
        remove_highlight(page)
        return

    if action == "for_each":
        selector = ctx.resolve_text(str(step.get("selector", "") or ""))
        variable = str(step.get("variable", "") or "")
        nested = list(step.get("steps") or [])
        locators = page.locator(selector).all()
        on_log(f"{index}. Для каждого «{selector}» → {len(locators)} элемент(ов)")
        for item_index, locator in enumerate(locators, start=1):
            try:
                value = (locator.inner_text(timeout=3000) or "").strip()
            except Exception:  # noqa: BLE001
                value = str(item_index)
            if not value:
                value = str(item_index)
            ctx.remember(variable, value)
            on_log(f"{index}.{item_index} «{variable}» = «{value}»")
            for sub_step in nested:
                page = ctx.current_page(page)
                execute_step(
                    page,
                    sub_step,
                    index,
                    on_log,
                    highlight=highlight,
                    interactive=interactive,
                    prior_steps=prior_steps,
                    on_close_browser=on_close_browser,
                    run_context=ctx,
                )
        page = ctx.current_page(page)
        remove_highlight(page)
        return

    if action == "switch_tab":
        from app.tab_helpers import resolve_tab_page

        mode = str(step.get("mode", "") or "")
        value = ctx.resolve_text(str(step.get("value", "") or ""))
        target = resolve_tab_page(page.context, mode=mode, value=value)
        if target is None:
            raise RuntimeError(f"Вкладка не найдена ({mode}: {value})".rstrip(": "))
        ctx.set_current_page(target)
        try:
            target.bring_to_front()
        except Exception:  # noqa: BLE001
            pass
        on_log(f"{index}. Переключение вкладки → {mode}")
        remove_highlight(target)
        return

    if action == "close_tab":
        from app.tab_helpers import open_pages

        pages = open_pages(page.context)
        if len(pages) <= 1:
            raise RuntimeError("Нельзя закрыть единственную вкладку")
        current = page
        remaining = [item for item in pages if item != current]
        current.close()
        fallback = remaining[-1] if remaining else pages[0]
        ctx.set_current_page(fallback)
        on_log(f"{index}. Закрыта текущая вкладка")
        remove_highlight(fallback)
        return

    if action == "assert_tab_count":
        from app.tab_helpers import open_pages

        expected = int(step.get("count", 0))
        actual = len(open_pages(page.context))
        on_log(f"{index}. Проверка вкладок → {actual} из {expected}")
        if actual != expected:
            raise AssertionError(f"Ожидалось вкладок: {expected}, открыто: {actual}")
        remove_highlight(page)
        return

    if action == "goto":
        url = ctx.resolve_text(str(step.get("url", "")))
        if urls_match(page.url, url):
            on_log(f"{index}. Уже на странице → {url}")
            return
        on_log(f"{index}. Переход → {url}")
        remove_highlight(page)
        page.goto(url, wait_until=NAV_WAIT_UNTIL, timeout=NAV_TIMEOUT_MS)
        return

    if action in {"remember_text", "remember_field", "remember_url"}:
        if action == "remember_text":
            variable = str(step.get("variable", "") or "")
            value = ctx.resolve_text(str(step.get("value", "") or ""))
            ctx.remember(variable, value)
            on_log(f"{index}. Запомнено «{variable}» = «{value}»")
        elif action == "remember_field":
            variable = str(step.get("variable", "") or "")
            field_selector = str(step.get("selector", "") or "")
            locator = page.locator(field_selector).first
            locator.wait_for(state="visible", timeout=10000)
            try:
                value = locator.input_value(timeout=3000)
            except Exception:  # noqa: BLE001
                value = (locator.inner_text(timeout=3000) or "").strip()
            ctx.remember(variable, value)
            on_log(f"{index}. Запомнено «{variable}» из поля {field_selector}")
        else:
            variable = str(step.get("variable", "") or "")
            ctx.remember(variable, page.url)
            on_log(f"{index}. Запомнено «{variable}» = текущий URL")
        remove_highlight(page)
        return

    if action == "assert_url":
        expected = ctx.resolve_text(str(step.get("url", "")))
        on_log(f"{index}. Проверка URL → {expected}")
        if not urls_match(page.url, expected):
            raise AssertionError(f"Ожидался URL «{expected}», сейчас: {page.url}")
        remove_highlight(page)
        return

    if action == "reload":
        on_log(f"{index}. Обновление страницы")
        remove_highlight(page)
        page.reload(wait_until=NAV_WAIT_UNTIL, timeout=NAV_TIMEOUT_MS)
        return

    if action == "go_back":
        on_log(f"{index}. Назад в истории")
        remove_highlight(page)
        page.go_back(wait_until=NAV_WAIT_UNTIL, timeout=NAV_TIMEOUT_MS)
        return

    if action == "close_browser":
        on_log(f"{index}. Закрываю браузер")
        remove_highlight(page)
        if on_close_browser is not None:
            on_close_browser()
        else:
            browser = page.context.browser
            if browser is not None:
                browser.close()
        return

    if action == "wait":
        ms = max(0, int(step.get("ms", 1000)))
        on_log(f"{index}. Пауза {ms} мс")
        remove_highlight(page)
        page.wait_for_timeout(ms)
        return

    if action == "wait_for":
        selector = step.get("selector", "")
        timeout_ms = max(1000, int(step.get("timeout_ms", 30000)))
        on_log(f"{index}. Жду появления → {step_log_target(step, selector)}")
        _maybe_highlight(page, selector, enabled=highlight, pause_ms=200)
        page.locator(selector).first.wait_for(state="visible", timeout=timeout_ms)
        remove_highlight(page)
        return

    if action == "wait_for_hidden":
        selector = step.get("selector", "")
        timeout_ms = max(1000, int(step.get("timeout_ms", 30000)))
        on_log(f"{index}. Жду исчезновения → {step_log_target(step, selector)}")
        _maybe_highlight(page, selector, enabled=highlight, pause_ms=200)
        page.locator(selector).first.wait_for(state="hidden", timeout=timeout_ms)
        remove_highlight(page)
        return

    if action == "press":
        key = str(step.get("key", "Enter"))
        target_selector = str(step.get("selector", "") or "").strip()
        if target_selector:
            on_log(f"{index}. Клавиша «{key}» → {step_log_target(step, target_selector)}")
            _maybe_highlight(page, target_selector, enabled=highlight, pause_ms=200)
            page.locator(target_selector).first.press(key, timeout=15000)
        else:
            on_log(f"{index}. Клавиша «{key}»")
            page.keyboard.press(key)
        remove_highlight(page)
        return

    selector = step.get("selector", "")
    if action not in {"press"} and not selector:
        on_log(f"{index}. Пропуск шага без селектора")
        return

    if action not in {"press"} and not selector:
        on_log(f"{index}. Пропуск шага без селектора")
        return

    if action == "hover":
        on_log(f"{index}. Наведение → {step_log_target(step, selector)}")
        _maybe_highlight(page, selector, enabled=highlight, pause_ms=200)
        locator = resolve_hover_locator(page, selector)
        locator.scroll_into_view_if_needed(timeout=5000)
        locator.hover(timeout=15000, force=True)
        page.wait_for_timeout(400)
        remove_highlight(page)
        return

    if action == "click":
        on_log(format_click_log(index, step))
        _maybe_highlight(page, selector, enabled=highlight, pause_ms=200)
        _prepare_click_target(page, step, on_log, index)
        locator = resolve_chained_locator(page, selector)
        try:
            locator.click(timeout=9000)
        except Exception:
            if _reveal_hover_menu(page, selector, on_log, index):
                resolve_chained_locator(page, selector).click(timeout=9000)
            else:
                raise
        remove_highlight(page)
        page.wait_for_load_state("domcontentloaded")
        return

    if action == "fill":
        selector = step.get("selector", "")
        raw_value = str(step.get("value", "") or "")
        value = ctx.resolve_text(raw_value)
        masked = "***" if step.get("inputType") in {"password"} else value
        _maybe_highlight(page, selector, enabled=highlight, pause_ms=200)
        on_log(format_fill_log(index, step, masked))
        _fill_locator(page, selector, value)
        return

    if action == "fill_generated":
        selector = step.get("selector", "")
        generator = str(step.get("generator", "") or "")
        value = ctx.generate(generator)
        _maybe_highlight(page, selector, enabled=highlight, pause_ms=200)
        on_log(format_fill_generated_log(index, step, generator, value))
        _fill_locator(page, selector, value)
        return

    if action == "prompt_email_code":
        import os

        selector = step.get("selector", "")
        timeout_ms = max(1000, int(step.get("timeout_ms", 60000)))
        on_log(f"{index}. Жду поля кода → {selector}")
        try:
            page.locator(selector).first.wait_for(state="visible", timeout=timeout_ms)
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(
                f"Поля кода не появились за {timeout_ms // 1000} с — "
                f"возможно, шаг стоит слишком рано в сценарии ({selector})"
            ) from exc

        email = resolve_email_for_code_prompt(page, step, prior_steps or [], run_context=ctx)
        if not email:
            raise RuntimeError(
                'Не удалось определить email для кода. '
                'Укажите в шаге: ввожу код из почты "user@mail.com" в "селектор"'
            )

        env_code = os.environ.get("SCENARIA_EMAIL_CODE", "").strip()
        if env_code:
            on_log(f"{index}. Код из SCENARIA_EMAIL_CODE ({email}) → {selector}")
            code = env_code
        elif interactive:
            from app.qt.sync_prompts import prompt_email_code_blocking

            on_log(f"{index}. Код из почты ({email}) → {selector}")
            code = prompt_email_code_blocking(email=email, selector=selector)
        else:
            raise RuntimeError(
                "Шаг «код из почты» в headless: задайте переменную окружения SCENARIA_EMAIL_CODE"
            )
        if code is None:
            raise RuntimeError("Ввод кода из почты отменён")
        value = code.strip()
        if not value:
            raise RuntimeError("Код из почты не введён")
        digits = step.get("digits")
        parsed_digits = int(digits) if digits else None
        input_method = str(step.get("inputMethod", "") or "").strip() or None
        locator = page.locator(selector)
        if not _otp_fields_visible(locator):
            on_log(f"{index}. Экран кода уже закрыт — продолжаем сценарий")
            remove_highlight(page)
            return
        fill_mode = fill_verification_code(
            page,
            selector,
            value,
            digits=parsed_digits,
            input_method=input_method,
            allow_advancing=True,
        )
        if fill_mode.endswith("-submit") or fill_mode == "already-submitted":
            on_log(f"{index}. Код принят, форма перешла дальше ({fill_mode})")
        else:
            on_log(f"{index}. Ввод кода ({fill_mode}) → {selector}")
        remove_highlight(page)
        return

    if action == "select":
        value = step.get("value", "")
        on_log(f"{index}. Выбор «{value}» → {selector}")
        page.locator(selector).first.select_option(value=value, timeout=15000)
        remove_highlight(page)
        return

    if action == "double_click":
        on_log(f"{index}. Двойной клик → {selector}")
        page.locator(selector).first.dblclick(timeout=9000)
        remove_highlight(page)
        return

    if action == "clear":
        on_log(f"{index}. Очистка → {selector}")
        page.locator(selector).first.clear(timeout=15000)
        remove_highlight(page)
        return

    if action == "check":
        on_log(f"{index}. Отметка → {selector}")
        page.locator(selector).first.check(timeout=15000)
        remove_highlight(page)
        return

    if action == "uncheck":
        on_log(f"{index}. Снятие отметки → {selector}")
        page.locator(selector).first.uncheck(timeout=15000)
        remove_highlight(page)
        return

    if action == "scroll_to":
        on_log(f"{index}. Скролл → {selector}")
        page.locator(selector).first.scroll_into_view_if_needed()
        remove_highlight(page)
        return

    if action == "draw_signature":
        on_log(f"{index}. Подпись")
        draw_signature_on_canvas(page, selector)
        remove_highlight(page)
        return

    if action == "upload":
        from app.upload_helpers import resolve_upload_path, validate_upload_path

        path = str(step.get("path", "") or "")
        missing = validate_upload_path(path, ctx.project_root)
        if missing:
            raise FileNotFoundError(missing)
        resolved = resolve_upload_path(path, ctx.project_root)
        on_log(f"{index}. Загрузка файла → {resolved}")
        page.locator(selector).first.set_input_files(str(resolved))
        remove_highlight(page)
        return

    if action == "download_click":
        on_log(f"{index}. Скачивание по клику → {selector}")
        _maybe_highlight(page, selector, enabled=highlight, pause_ms=200)
        with page.expect_download(timeout=60000) as download_info:
            page.locator(selector).first.click(timeout=15000)
        saved = save_playwright_download(download_info.value, ctx.download_dir())
        ctx.set_last_download(saved)
        on_log(f"{index}. Файл сохранён → {saved.name}")
        remove_highlight(page)
        return

    if action == "assert_download_contains":
        needle = str(step.get("value", "") or "")
        downloaded = ctx.last_download
        if downloaded is None or not downloaded.is_file():
            raise AssertionError("Нет скачанного файла — сначала выполните «скачиваю по клику на …»")
        on_log(f"{index}. Проверка скачанного файла «{downloaded.name}»")
        if downloaded.stat().st_size <= 0:
            raise AssertionError(f"Скачанный файл пуст: {downloaded.name}")
        if not file_contains_substring(downloaded, needle):
            raise AssertionError(f"Файл «{downloaded.name}» не содержит «{needle}»")
        remove_highlight(page)
        return

    if action == "assert_visible":
        on_log(f"{index}. Проверка видимости → {selector}")
        page.locator(selector).first.wait_for(state="visible", timeout=10000)
        remove_highlight(page)
        return

    if action == "assert_text":
        expected = ctx.resolve_text(str(step.get("value", "") or ""))
        on_log(f"{index}. Проверка текста «{expected}» → {selector}")
        locator = page.locator(selector).first
        locator.wait_for(state="visible", timeout=10000)
        actual = (locator.inner_text(timeout=5000) or "").strip()
        if expected not in actual:
            raise AssertionError(f"Ожидался текст «{expected}», получено: «{actual[:120]}»")
        remove_highlight(page)
        return

    if action == "assert_hidden":
        on_log(f"{index}. Проверка скрытия → {selector}")
        locator = page.locator(selector)
        if locator.count() > 0 and locator.first.is_visible(timeout=2000):
            raise AssertionError(f"Элемент всё ещё виден: {selector}")
        remove_highlight(page)
        return

    on_log(f"{index}. Неизвестное действие: {action}")
    remove_highlight(page)
