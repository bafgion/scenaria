# Playwright export

Scenaria может экспортировать сценарий из `.feature` в тест Playwright (TypeScript или Python).

- GUI: **Сценарий → Экспорт Playwright…**
- CLI: `scenaria export path/to/scenario.feature [-o out.spec.ts] [--python] [--force]`

Источник правды по покрытию: `EXPORT_ACTION_SUPPORT` в `app/playwright_export.py`.

## Поддерживаемые шаги (полный экспорт)

| action | Playwright |
|--------|------------|
| `goto` | `page.goto` |
| `go_back` | `page.goBack` / `go_back` |
| `reload` | `page.reload` |
| `scroll_to` | `scrollIntoViewIfNeeded` |
| `click` | `locator.click` |
| `double_click` | `dblclick` |
| `hover` | `hover` |
| `fill` | `fill` |
| `clear` | `clear` |
| `select` | `selectOption` / `select_option` |
| `check` / `uncheck` | `check` / `uncheck` |
| `press` | `keyboard.press` или `locator.press` |
| `upload` | `setInputFiles` |
| `draw_signature` | mouse path на canvas |
| `assert_visible` / `assert_hidden` | `expect` visibility |
| `assert_text` | `toContainText` |
| `assert_url` | `toHaveURL` |
| `wait` | `waitForTimeout` |
| `wait_for` / `wait_for_hidden` | `locator.waitFor` |
| `close_browser` | `browser.close` |

## Частичный экспорт

| action | Поведение |
|--------|-----------|
| `fill_generated` | `fill` с `process.env.SCRANARIA_GEN_<NAME>` (или `os.environ` в Python) и placeholder `REPLACE_<generator>`. Генераторы Scenaria в CI нужно подставить вручную или через фикстуру. |

## Не экспортируется

В файл попадает комментарий `unsupported action: …`. CLI без `--force` завершается с кодом 1; GUI показывает предупреждение.

| action | Причина |
|--------|---------|
| `if`, `repeat`, `while`, `for_each` | Вложенная логика Gherkin |
| `switch_tab`, `close_tab`, `assert_tab_count` | Мультивкладки |
| `download_click`, `assert_download_contains` | Загрузки и файловая проверка |
| `remember_text`, `remember_field`, `remember_url` | Переменные сценария |
| `prompt_email_code` | Интерактив / OTP из почты |

Шаги Vanessa Automation и других add-on в этот список не входят.

## Предупреждения

- В начале файла — блок `Scenaria export notice` с partial/unsupported action.
- CLI печатает `warning:` в stderr; `--force` записывает файл несмотря на unsupported.
- GUI спрашивает подтверждение при partial или unsupported шагах.
