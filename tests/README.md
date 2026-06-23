# Тесты Scenaria

## Установка

```powershell
pip install -e ".[dev]"
python -m playwright install chromium
```

Версии пакетов задаются в `pyproject.toml`. Файлы `requirements*.txt` — тонкие обёртки (`-e .` / `-e ".[dev,build]"`).

## Быстрый прогон

```powershell
python -m pytest tests/ -q
```

Полный suite (~560 тестов) на Windows занимает несколько минут; integration-тесты запускают реальный Chromium.

## Разделение по типам

| Тип | Как запустить | Примечание |
|-----|---------------|------------|
| Unit | `pytest tests/ -q -m "not integration"` | Без браузера |
| Integration | `pytest tests/ -q -m integration` | Маркер `@pytest.mark.integration` |
| Qt | Автоопределение в `conftest.py` | Модули с `PySide6` / фикстура `qapp` |

Примеры:

```powershell
# Только unit (быстрее)
python -m pytest tests/ -q -m "not integration"

# Только integration
python -m pytest tests/ -q -m integration

# Один файл
python -m pytest tests/test_gherkin_ru.py -q
```

## Порядок выполнения (`conftest.py`)

На Windows Playwright и Qt в **одном** процессе pytest иногда дают access violation. Поэтому:

1. **Integration** — первыми (реальный браузер)
2. **Unit** — без Qt и без браузера
3. **Qt** — последними

Integration-тесты дополнительно сериализуются глобальным lock — одновременно только одна сессия Chromium.

## CI (GitHub Actions)

Workflow `.github/workflows/ci.yml` на `push` / `pull_request` в `master`:

1. `pip install -e ".[dev]"`
2. `ruff check app tests`
3. `pytest tests/ -q`

Release workflow (тег `v*`) дополнительно собирает portable EXE.

### Известные ограничения на CI

| Файл | Поведение | Причина |
|------|-----------|---------|
| `test_gherkin_completions.py` | skip на `GITHUB_ACTIONS` | Нестабильный completion popup в headless |
| `test_toolbar_sidebar_layout.py` | skip при неудачной проверке ширины | Headless layout отличается от desktop |
| `test_update_ui.py` | часть тестов skip на CI | Таймеры / модальные окна обновления |

Стабилизация — спринт 13 (T4).

## Линтер

```powershell
python -m ruff check app tests
```

Конфигурация: `[tool.ruff]` в `pyproject.toml`.

## Настройки в тестах

Фикстура `isolated_settings` (autouse) перенаправляет `settings.json` в `tmp_path` — тесты не пишут в `%APPDATA%/Scenaria`.
