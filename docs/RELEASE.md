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

Версия хранится в `pyproject.toml` (`version = "…"`). Перед релизом увеличьте её.

## Сборка локально

```powershell
cd scripts
.\build.ps1
```

Результат в `dist/`:

| Файл | Назначение |
|------|------------|
| `Scenaria-Portable/` | portable-папка |
| `Scenaria-Portable.zip` | полная установка (с Chromium) |
| `Scenaria-update.zip` | обновление без `browsers/` и `data/` |
| `latest.json` | манифест с SHA256 для проверки целостности |

### Уменьшение размера

- PyInstaller больше не тянет все подмодули PySide6 (Qt3D/QML/WebEngine).
- В `browsers/` копируются только `chromium-*` и `ffmpeg-*` (без `chromium_headless_shell-*`).

## Авторелиз через GitHub Actions

1. Обновите версию в `pyproject.toml`.
2. Закоммитьте и создайте тег:

```powershell
git add pyproject.toml
git commit -m "Release v0.2.1"
git tag v0.2.1
git push origin main --tags
```

Workflow `.github/workflows/release.yml` соберёт portable, прогонит тесты и опубликует Release с тремя артефактами.

## Автообновление в приложении

В portable EXE:

- при старте — тихая проверка GitHub Releases;
- **Справка → Проверить обновления…** — ручная проверка;
- при наличии версии — скачивание `Scenaria-update.zip` (без браузера), замена `exe` и `_internal`, папки `data/` и `browsers/` не трогаются;
- перезапуск через `_apply_update.bat`.

Первичная установка — полный `Scenaria-Portable.zip`.

## GitHub CLI

```powershell
gh auth login
gh auth status
```
