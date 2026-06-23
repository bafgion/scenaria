# Roadmap Scenaria — технический долг и инфраструктура

**Текущий релиз:** v0.9.2 (спринт 12 — RecordingController split)  
**Продуктовые спринты 1–9:** завершены — см. [archive/COMPLETED_SPRINTS.md](archive/COMPLETED_SPRINTS.md).

После v0.8.x фокус смещается с новых фич на **устойчивость разработки**: CI, декомпозиция крупных модулей, стабильные тесты, единые зависимости.

Версионирование: [VERSIONING.md](VERSIONING.md). Детали задач: [ROADMAP_TASKS.md](ROADMAP_TASKS.md).

---

## Контекст (аудит кодовой базы, 2026-06)

| Проблема | Риск |
|----------|------|
| `main_window.py` ~1 900 строк | Любое изменение UI ломает смежные сценарии |
| `recording_controller.py` ~1 200 строк | Запись/прогон/validate/picker в одном классе |
| CI только на тег релиза | Регрессии между релизами не ловятся |
| Qt + Playwright в одном pytest-процессе | Flaky / access violation на Windows |
| `requirements.txt` + `pyproject.toml` | Расхождение версий |
| `playwright_export.py` — часть шагов `TODO` | Экспорт обещает больше, чем делает |
| Retry pytest ×3 в release workflow | Маскирует нестабильность |

**Не в этом roadmap:** новые пользовательские фичи (кроме мелких багфиксов). Их — отдельным эпиком после стабилизации инфраструктуры.

---

## Фазы

### Фаза T1 — CI и зависимости (спринт 10 → v0.9.0)

Цель: обратная связь на каждый push/PR, один источник зависимостей.

- Workflow `ci.yml`: `pytest` на `windows-latest` без сборки EXE
- Job быстрый: unit + Qt; integration — отдельный job или `continue-on-error` до T4
- `ruff check` в CI
- Зависимости: `pyproject.toml` — источник правды; `requirements*.txt` синхронизировать или генерировать

### Фаза T2 — Декомпозиция MainWindow (спринт 11 → v0.9.1)

Цель: `main_window.py` < **1 200** строк, тестируемые модули.

- `app/qt/main_window_update.py` — проверка/скачивание/установка обновлений
- `app/qt/main_window_menus.py` — сборка меню и QAction (или фабрика)
- `app/qt/main_window_batch.py` — пакетный прогон, выбор в каталоге
- `MainWindow` — только wiring, layout, делегирование

### Фаза T3 — Декомпозиция RecordingController (спринт 12 → v0.9.2)

Цель: `recording_controller.py` < **800** строк.

- `PlaybackCoordinator` — start/stop/pause player, run from step N
- `ValidateCoordinator` — validate selectors, связь с UI-панелью
- `RecordingSession` — open browser, record modes, TestClient, picker
- Контроллер — фасад и сигналы Qt

### Фаза T4 — Стабильность тестов (спринт 13 → v0.10.0)

Цель: зелёный CI без retry ×3.

- Integration-тесты Playwright — **subprocess** или отдельный pytest worker
- Безопасные Qt smoke: `MainWindow` с mock `ScenarioRecorder` / без Chromium
- Убрать skip Qt на `GITHUB_ACTIONS` там, где тесты стабилизированы
- Снизить retry в `release.yml` до 1 (после зелёного CI)

### Фаза T5 — Экспорт и сопровождение (спринт 14 → v0.10.1)

- Аудит `playwright_export.py`: реализовать или явно пометить unsupported в CLI/GUI
- `CHANGELOG.md` — пользовательские изменения по релизам
- `VERSIONING.md` в репозитории (сейчас локальный)

---

## Порядок релизов

| Релиз | Спринт | Содержание | Тип |
|-------|--------|------------|-----|
| **v0.9.0** | 10 | **T1** CI на PR, ruff, единые зависимости — **закрыт** | MINOR |
| **v0.9.1** | 11 | **T2** MainWindow split | PATCH |
| **v0.9.2** | 12 | **T3** RecordingController split | PATCH |
| **v0.10.0** | 13 | **T4** стабильные тесты | MINOR |
| **v0.10.1** | 14 | **T5** export + CHANGELOG | PATCH |

Порядок T2/T3 можно менять; **T1 желательно первым** — защита рефакторинга.

---

## Метрики успеха

| Метрика | Цель | Спринт |
|---------|------|--------|
| CI на PR | < 15 мин, без EXE | T1 |
| `main_window.py` | < 1 200 LOC | T2 |
| `recording_controller.py` | < 800 LOC | T3 |
| Release pytest retry | 0–1 | T4 |
| Export: шаги без `TODO` | 100 % каталога или явный список unsupported | T5 |

---

## Definition of Done (общий)

1. Код + pytest (unit; integration/Qt по смыслу задачи)
2. Поведение GUI/CLI не регрессирует (ручной smoke для T2/T3)
3. CI зелёный на PR
4. Строка в CHANGELOG при релизе

---

## Вне scope

- Сборка macOS/Linux
- mypy/pyright (отдельный эпик после T4)
- Разбиение `player.py` / `gherkin_ru.py` (после T2–T3, если понадобится)
