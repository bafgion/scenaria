# Roadmap Scenaria — технический долг и инфраструктура

**Текущий релиз:** v0.10.1 (спринт 14 — export audit + CHANGELOG)  
**Следующий план:** спринты 15–20 (фазы T6–T10) — см. ниже.  
**Продуктовые спринты 1–9:** завершены — [archive/COMPLETED_SPRINTS.md](archive/COMPLETED_SPRINTS.md).

Фазы T1–T5 **закрыты** (v0.9.0 … v0.10.1). Дальше — доводка CI, сопровождение и декомпозиция `player` / `gherkin_ru` по [аудиту 2026-06-23](#контекст-аудит-2026-06-23).

Версионирование: [VERSIONING.md](VERSIONING.md). Детали задач: [ROADMAP_TASKS.md](ROADMAP_TASKS.md).

---

## Контекст (аудит 2026-06-23)

| Проблема | Риск | Спринт |
|----------|------|--------|
| 10 тестов skip на `GITHUB_ACTIONS` | Дыры в CI-покрытии Qt/update/toolbar | **15 (T6)** |
| `main_window.py` ≤ 1200 LOC (1146) | T2/T7 закрыт | — |
| `player.py` ~1 600 строк | Сложность изменений прогона | **17–18 (T8)** |
| `gherkin_ru.py` ~1 200 строк | Сложность парсера | **19 (T9)** |
| Нет static typing | Регрессии при split (пример: `_status_brief`) | **20 (T10)** |
| Архив `COMPLETED_SPRINTS` устарел | Путаница с версией | **16 (T7)** |

**Закрыто в T1–T5:** CI на PR, split MainWindow/RecordingController, subprocess-тесты, export audit, CHANGELOG.

**Не в этом roadmap:** новые пользовательские фичи — отдельный продуктовый эпик после T6–T10 (или параллельно мелкими PATCH).

---

## Фазы T1–T5 (завершены)

<details>
<summary>Развернуть T1–T5</summary>

### Фаза T1 — CI и зависимости (спринт 10 → v0.9.0) ✅

### Фаза T2 — MainWindow (спринт 11 → v0.9.1) ✅

### Фаза T3 — RecordingController (спринт 12 → v0.9.2) ✅

### Фаза T4 — Тесты (спринт 13 → v0.10.0) ✅

### Фаза T5 — Export и docs (спринт 14 → v0.10.1) ✅

</details>

---

## Фазы T6–T10 (план)

### Фаза T6 — CI без skip (спринт 15 → v0.10.2)

Цель: **0 skip** на GitHub Actions при полном `pytest`.

- Стабилизировать `test_update_ui.py` (QEventLoop + QThread) через моки/синхронные сигналы
- Стабилизировать resize-тесты toolbar: фиксированные размеры или helper вместо циклов
- Регрессионный тест `_status_brief` после split RecordingController
- Обновить `tests/README.md` (убрать таблицу CI skip, если пусто)

### Фаза T7 — Сопровождение (спринт 16 → v0.10.3)

Цель: закрыть хвосты T2 и документации.

- `main_window.py` ≤ **1 200** строк
- Обновить `archive/COMPLETED_SPRINTS.md` (v0.10.x, техдолг)
- Ruff: явный набор правил в `pyproject.toml` (не только defaults)
- Чеклист для `scripts/split_*.py`: методы-mixin с `self` (док или lint-скрипт)

### Фаза T8 — Декомпозиция Player (спринты 17–18 → v0.11.0)

Цель: `player.py` < **900** строк, тестируемые модули.

**Спринт 17:** выделить исполнение шагов и контекст прогона.  
**Спринт 18:** highlight/picker/batch-очередь, фасад `ScenarioPlayer`.

Ориентир по модулям (уточнить в T8-*):

- `player_step_executor.py` — `execute_step`, action dispatch
- `player_context.py` — `RunContext`, переменные, генераторы
- `player_highlight.py` — подсветка, scroll, focus
- `player.py` — фасад, lifecycle, worker thread

### Фаза T9 — Декомпозиция Gherkin (спринт 19 → v0.11.1)

Цель: `gherkin_ru.py` < **800** строк.

- `gherkin_parse.py` — `parse_gherkin_steps`, `_parse_step_body`
- `gherkin_serialize.py` — `steps_to_gherkin`, outline/tags
- `gherkin_ru.py` — публичный API, re-export, тонкие обёртки
- Без изменения синтаксиса `.feature` на диске

### Фаза T10 — Статическая типизация (спринт 20 → v0.11.2)

Цель: mypy на критичных слоях без массового `# type: ignore`.

- `pyproject.toml`: `[tool.mypy]` + optional-dep `dev`
- CI: job `mypy` (или шаг в `ci.yml`) для `app/mvc/`, `app/playwright_export.py`
- Постепенно: `app/step_catalog.py`, координаторы recording

---

## Порядок релизов

| Релиз | Спринт | Содержание | Тип |
|-------|--------|------------|-----|
| **v0.9.0** | 10 | T1 CI — **закрыт** | MINOR |
| **v0.9.1** | 11 | T2 MainWindow — **закрыт** | PATCH |
| **v0.9.2** | 12 | T3 RecordingController — **закрыт** | PATCH |
| **v0.10.0** | 13 | T4 тесты — **закрыт** | MINOR |
| **v0.10.1** | 14 | T5 export — **закрыт** | PATCH |
| **v0.10.2** | 15 | **T6** CI без skip | PATCH |
| **v0.10.3** | 16 | **T7** сопровождение | PATCH |
| **v0.11.0** | 17–18 | **T8** Player split | MINOR |
| **v0.11.1** | 19 | **T9** Gherkin split | PATCH |
| **v0.11.2** | 20 | **T10** mypy | PATCH |

T8 — два спринта подряд, один MINOR-релиз. T6 желательно **до** крупного split T8 (защита CI).

---

## Метрики успеха

| Метрика | Цель | Спринт |
|---------|------|--------|
| CI skip на GITHUB_ACTIONS | **0** | T6 |
| `main_window.py` | ≤ 1 200 LOC | T7 |
| `player.py` | ≤ 900 LOC (сейчас 754) | T8b |
| `gherkin_ru.py` | ≤ 800 LOC | T9 |
| mypy | 0 errors на `app/mvc/` | T10 |

---

## Definition of Done (общий)

1. Код + pytest по задаче
2. CI зелёный на PR (после T6 — без skip)
3. Для T8/T9 — ручной smoke: открыть проект → запись → прогон
4. Секция в CHANGELOG при релизе

---

## Вне scope (T6–T10)

- Сборка macOS/Linux
- Продуктовые фичи (новый UX, интеграции) — эпик **P** после T8 или отдельной веткой
- Vanessa / 1С-шаги в core export
- Полный mypy на `player.py` до завершения T8
