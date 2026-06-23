# Changelog

Все заметные изменения Scenaria для пользователей. Формат основан на [Keep a Changelog](https://keepachangelog.com/ru/1.1.0/).

Версионирование: [docs/VERSIONING.md](docs/VERSIONING.md).

## [Unreleased]

## [0.10.1] — 2026-06-23

Релиз технического долга (спринты 10–14) после v0.8.1.

### Added

- CI на каждый push/PR (`ci.yml`: ruff + pytest).
- Декомпозиция `MainWindow` и `RecordingController` (модули-миксины).
- Стабильный прогон тестов: integration Playwright в subprocess, Qt smoke.
- Аудит экспорта Playwright: partial/unsupported шаги, предупреждения в GUI и CLI ([docs/PLAYWRIGHT_EXPORT.md](docs/PLAYWRIGHT_EXPORT.md)).
- `CHANGELOG.md`, `docs/VERSIONING.md` в репозитории.

### Changed

- Единый источник зависимостей: `pyproject.toml`.
- Экспорт `fill_generated`: placeholder через `SCENARIA_GEN_*` вместо `TODO: generate`.
- Release workflow: один прогон pytest без retry ×3.

### Fixed

- `_status_brief` при завершении прогона теста (регрессия после split RecordingController).

## [0.10.0] — 2026-06-23

Технический релиз (спринт 13): стабильность тестов на Windows CI.

### Changed

- Integration-тесты Playwright запускаются в отдельном subprocess; Qt-тесты не делят процесс с Chromium.
- Release workflow: один прогон pytest без retry ×3.

## [0.9.0] — 2026-06-23

Технический релиз (спринт 10): CI на каждый push/PR.

### Added

- GitHub Actions `ci.yml`: ruff + pytest на `master`.
- Документация стратегии тестов (`tests/README.md`).

### Changed

- Единый источник зависимостей: `pyproject.toml`.

## [0.8.1] — 2026-06-23

### Fixed

- Диалог сохранения TestClient: корректное начальное значение имени профиля.

### Changed

- UX автообновления: отмена загрузки, indeterminate progress (F5-3).

## [0.8.0] — 2026-06-23

### Added

- **TestClient** — именованные сессии браузера через блок `Контекст:` в `.feature`.
- Пример `examples/05-testclient-kontekst.feature`.

### Changed

- Единый стиль GUI (тема, диалоги, панели).
- Структура меню **Проект / Сценарий / Запись и тест** (F4).

## [0.7.0] — 2026-06-23

### Added

- Плагины runner'ов (P0), add-on **Vanessa Automation**.
- Условия (`Если …`), циклы (`Повторяю`, `Пока`, `Для каждого`), Outline в Gherkin.

## [0.6.8] — 2026-06-22

### Changed

- Упрощённый toolbar записи, чеклист на вкладке «Старт», улучшенные настройки (F6).
- Picker и инструменты доступны на паузе записи (B3-7).

---

## Шаблон для следующего релиза

Перед тегом `vX.Y.Z` добавьте секцию **выше** `[Unreleased]`:

```markdown
## [X.Y.Z] — YYYY-MM-DD

### Added
- …

### Changed
- …

### Fixed
- …
```

Затем очистите `[Unreleased]` или перенесите пункты в новую секцию. Процесс: [docs/RELEASE.md](docs/RELEASE.md).

[Unreleased]: https://github.com/bafgion/scenaria/compare/v0.10.1...HEAD
[0.10.1]: https://github.com/bafgion/scenaria/compare/v0.10.0...v0.10.1
[0.10.0]: https://github.com/bafgion/scenaria/compare/v0.9.0...v0.10.0
[0.9.0]: https://github.com/bafgion/scenaria/compare/v0.8.1...v0.9.0
[0.8.1]: https://github.com/bafgion/scenaria/compare/v0.8.0...v0.8.1
[0.8.0]: https://github.com/bafgion/scenaria/compare/v0.7.0...v0.8.0
[0.7.0]: https://github.com/bafgion/scenaria/compare/v0.6.9...v0.7.0
[0.6.8]: https://github.com/bafgion/scenaria/releases/tag/v0.6.8
