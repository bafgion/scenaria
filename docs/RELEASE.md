# Релизы и автообновление

## Подготовка репозитория (один раз)

```powershell
cd scenaria
git init
git add .
git commit -m "Initial commit"
gh repo create scenaria --private --source=. --push
copy release.json.example release.json
# отредактируйте github_repo в release.json при необходимости
```

`release.json` в `.gitignore` — локальная настройка. В CI используется `app/release_info.py` (`DEFAULT_GITHUB_REPO` или переменная `SHOP_UI_RECORDER_GITHUB_REPO`).

## Версия

Версия хранится в `pyproject.toml` (`version = "…"`). Перед релизом увеличьте её. Правила SemVer: [VERSIONING.md](VERSIONING.md).

## Сборка локально

```powershell
cd scripts
.\build.ps1
```

Результат в `dist/`:

| Файл / папка | Назначение |
|--------------|------------|
| `Scenaria/` | portable-папка |
| `Scenaria/examples/` | примеры сценариев для новичков (копируются из `examples/`) |
| `Scenaria-Portable.zip` | полная установка (с Chromium) |
| `Scenaria-update.zip` | обновление без `browsers/` и `data/` |
| `latest.json` | манифест с SHA256 для проверки целостности |

### Уменьшение размера

- PyInstaller больше не тянет все подмодули PySide6 (Qt3D/QML/WebEngine).
- В `browsers/` копируются только `chromium-*` и `ffmpeg-*` (без `chromium_headless_shell-*`).

## Авторелиз через GitHub Actions

1. Добавьте секцию в [CHANGELOG.md](CHANGELOG.md) для новой версии.
2. Обновите версию в `pyproject.toml`.
3. Закоммитьте и создайте тег:

```powershell
git add pyproject.toml
git commit -m "Release v0.8.0"
git tag v0.8.0
git push origin master --tags
```

Workflow `.github/workflows/release.yml` соберёт portable, прогонит тесты и опубликует Release с тремя артефактами.

## CI на push и pull request

Workflow [`.github/workflows/ci.yml`](../.github/workflows/ci.yml) запускается при каждом `push` и `pull_request` в `master`:

1. установка `pip install -e ".[dev]"` и Chromium для Playwright;
2. `ruff check app tests`;
3. `pytest tests/ -q` (без сборки EXE).

Цель — ловить регрессии до тега релиза. Подробнее о типах тестов и маркерах: [tests/README.md](../tests/README.md).

Зависимости: единый источник — `pyproject.toml`; `requirements.txt` и `requirements-dev.txt` — обёртки `-e .` / `-e ".[dev,build]"`.

## Автообновление в приложении

В portable EXE:

- при старте — тихая проверка GitHub Releases;
- **Справка → Проверить обновления…** — ручная проверка;
- при наличии версии — скачивание `Scenaria-update.zip` (без браузера), замена `exe` и `_internal`, папки `data/` и `browsers/` не трогаются;
- перезапуск через `_apply_update.bat`.

### Что видит пользователь при обновлении

Модальное окно **«Загрузка обновления»** с прогресс-баром и фазами:

| Фаза | Подпись |
|------|---------|
| Скачивание | Процент и объём файла |
| Проверка файла | Контрольная сумма |
| Распаковка | Разбор архива |
| Подготовка к установке | Копирование в staging |
| Перезапуск | Запуск `_apply_update.bat` |

При ошибке — диалог с текстом и ссылкой на страницу загрузки. Лог установки: `_apply_update.log` рядом с `Scenaria.exe`.

Первичная установка — полный `Scenaria-Portable.zip`.

## GitHub CLI

```powershell
gh auth login
gh auth status
```

## См. также

- [CHANGELOG.md](../CHANGELOG.md) — история релизов
- [GETTING_STARTED.md](GETTING_STARTED.md) — onboarding и примеры
- [README.md](../README.md) — обзор продукта
