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

На Windows Playwright и Qt в **одном** процессе pytest иногда дают access violation.

**Полный прогон** (`pytest tests/`):

1. Integration-тесты — в **отдельном subprocess** (`tests/integration_subprocess.py`, флаг `SCENARIA_INTEGRATION_SUBPROCESS=1`)
2. Unit — без Qt и без браузера
3. Qt — в основном процессе (после integration)

Только integration или только unit/Qt — в текущем процессе, без subprocess.

Integration-тесты в одном процессе дополнительно сериализуются глобальным lock — одновременно только одна сессия Chromium.

Флаги:

- `--integration-in-process` — отключить subprocess (используется дочерним процессом)
- `SCENARIA_INTEGRATION_SUBPROCESS=1` — признак дочернего integration-прогона
- `SCENARIA_SKIP_RECORDER_PREWARM=1` — autouse в conftest для unit/Qt (без Playwright при `AppController()`)

## CI (GitHub Actions)

Workflow `.github/workflows/ci.yml` на `push` / `pull_request` в `master`:

1. `pip install -e ".[dev]"`
2. `ruff check app tests`
3. `pytest tests/ -q` (subprocess isolation включён автоматически)

Release workflow (тег `v*`) — один прогон pytest без retry, затем сборка portable EXE.

### Известные ограничения на CI

| Файл | Поведение | Причина |
|------|-----------|---------|
| `test_toolbar_sidebar_layout.py` | skip resize/splitter тестов на CI | Headless: ширина toolbar не растёт как на desktop |
| `test_update_ui.py` | skip runner-тестов с QEventLoop на CI | QThread + QEventLoop нестабильны на headless Windows |

`test_gherkin_completions.py` и chip-тесты toolbar снова запускаются на CI после изоляции Playwright (спринт 13).

## Линтер

```powershell
python -m ruff check app tests
```

Конфигурация: `[tool.ruff]` в `pyproject.toml`.

## Настройки в тестах

Фикстура `isolated_settings` (autouse) перенаправляет `settings.json` в `tmp_path` — тесты не пишут в `%APPDATA%/Scenaria`.
