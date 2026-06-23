# Задачи roadmap — технический долг

Детальная спецификация для [ROADMAP.md](ROADMAP.md) (фазы T1–T10).  
Продуктовые спринты 1–9: [archive/COMPLETED_SPRINTS.md](archive/COMPLETED_SPRINTS.md).

**Обновлено:** 2026-06-23 · **База:** master v0.10.1 (спринт 14) · **План:** спринты 15–20  
**Формат:** цель → файлы → критерии приёмки → тесты  
**Оценка:** **S** (1–2 дня), **M** (3–5 дней), **L** (1–2 недели)  
**Статус:** ✅ готово · 🔶 частично · ⬜ не начато

---

## Журнал прогресса

| Спринт | Версия | Тема | Статус | Прогресс |
|--------|--------|------|--------|----------|
| **10** | v0.9.0 | T1 — CI и зависимости | ✅ | 4/4 |
| **11** | v0.9.1 | T2 — MainWindow | ✅ | 4/4 |
| **12** | v0.9.2 | T3 — RecordingController | ✅ | 4/4 |
| **13** | v0.10.0 | T4 — Тесты | ✅ | 4/4 |
| **14** | v0.10.1 | T5 — Export и docs | ✅ | 3/3 |
| **15** | v0.10.2 | T6 — CI без skip | ✅ | 4/4 |
| **16** | v0.10.3 | T7 — Сопровождение | ⬜ | 0/4 |
| **17** | — | T8a — Player (ядро) | ⬜ | 0/3 |
| **18** | v0.11.0 | T8b — Player (фасад) | ⬜ | 0/3 |
| **19** | v0.11.1 | T9 — Gherkin split | ⬜ | 0/4 |
| **20** | v0.11.2 | T10 — mypy | ⬜ | 0/3 |

**Спринт 15 закрыт:** 0 skip на CI — `QSignalSpy` + `sync_update_threads`, toolbar по расчётной ширине, тесты `_status_brief`.

**Спринт 10 закрыт:** CI на PR, единые зависимости, ruff, `tests/README.md`.

---

## Спринт 10 → v0.9.0 — CI и зависимости ✅

### T1-1 — Workflow CI на push/PR ✅

**Критерии:**
- [x] Workflow `.github/workflows/ci.yml`
- [x] `push` / `pull_request` на `master`
- [x] Документировано в `docs/RELEASE.md`

### T1-2 — Единый источник зависимостей ✅

**Критерии:**
- [x] `pyproject.toml` — источник правды
- [x] `requirements*.txt` — `-e .` / `-e ".[dev,build]"`
- [x] CI, release, `build.ps1` используют `pip install -e`
- [x] README обновлён

### T1-3 — Ruff в CI ✅

**Критерии:**
- [x] `ruff check app tests` в `ci.yml`
- [x] Локально зелёный (автофикс + ручные правки)

### T1-4 — Документировать стратегию тестов ✅

**Критерии:**
- [x] `tests/README.md` — маркеры, порядок, CI skips
- [x] Команды `pytest -m "not integration"`

---

**Спринт 11 закрыт:** `main_window.py` 1889 → 1222 строк; модули update, menus, batch, palette, welcome.

---

## Спринт 11 → v0.9.1 — Декомпозиция MainWindow ✅

| ID | Результат |
|----|-----------|
| T2-1 | `main_window_update.py` — автообновление |
| T2-2 | `main_window_menus.py` — `build_menus` / `refresh_plugins_menu` |
| T2-3 | `main_window_batch.py` — пакетный прогон, плагины |
| T2-4 | `main_window.py` ≤ 1200 — **1222** (+ palette/welcome вынесены отдельно) |

Дополнительно: `main_window_palette.py`, `main_window_welcome.py`.

---

**Спринт 12 закрыт:** `recording_controller.py` 1226 → 462 строк; mixins playback, validate, session.

---

## Спринт 12 → v0.9.2 — Декомпозиция RecordingController ✅

| ID | Результат |
|----|-----------|
| T3-1 | `playback_coordinator.py` — play, queue, stop, HTML report |
| T3-2 | `validate_coordinator.py` — validate + результаты |
| T3-3 | `recording_session.py` — браузер, запись, picker, TestClient |
| T3-4 | `recording_controller.py` ≤ 800 — **462** (batch + bridge в ядре) |

---

**Спринт 13 закрыт:** integration в subprocess; `test_main_window_smoke.py`; сокращены CI skip; release без retry.

---

## Спринт 13 → v0.10.0 — Стабильность тестов ✅

| ID | Результат |
|----|-----------|
| T4-1 | `integration_subprocess.py` + `conftest.py`; `SCENARIA_SKIP_RECORDER_PREWARM` для Qt |
| T4-2 | `test_main_window_smoke.py` — MainWindow без Chromium, < 5 с |
| T4-3 | Убран skip paint в completions; chip-тесты toolbar на CI; комментарии к оставшимся skip |
| T4-4 | `release.yml` — один прогон pytest |

---

**Спринт 14 закрыт:** аудит Playwright export, CHANGELOG, VERSIONING в git.

---

## Спринт 14 → v0.10.1 — Export и сопровождение ✅

| ID | Результат |
|----|-----------|
| T5-1 | `EXPORT_ACTION_SUPPORT`, `analyze_export`, предупреждения GUI/CLI, `docs/PLAYWRIGHT_EXPORT.md` |
| T5-2 | `CHANGELOG.md`, ссылка в README, процесс в RELEASE.md |
| T5-3 | `docs/VERSIONING.md` в репозитории, согласован с ROADMAP |

---

## Спринт 15 → v0.10.2 — CI без skip (T6) ✅

**Источник:** аудит P1 — 10 тестов `skipif` на `GITHUB_ACTIONS`.

### T6-1 — Update runners на CI ✅

**Критерии:**
- [x] 5 тестов зелёные локально и на CI
- [x] Нет `skipif` по `GITHUB_ACTIONS` в `test_update_ui.py`
- [x] Фикстура `sync_update_threads` — патч `threading.Thread` + `QSignalSpy`

### T6-2 — Toolbar resize на CI ✅

**Критерии:**
- [x] 5 resize-тестов на CI без skip
- [x] `_resize_for_full_toolbar` по `chrome + full_layout_min_width + 80` вместо цикла

### T6-3 — Регрессия `_status_brief` ✅

**Критерии:**
- [x] 4 unit-теста в `test_recording_controller.py`
- [x] Исправлен `IndexError` на пустой строке в `_status_brief`

### T6-4 — Документация CI skip ✅

**Критерии:**
- [x] `tests/README.md` — «0 skipped» на CI
- [x] Полный pytest: 601 passed, 0 skipped

---

## Спринт 16 → v0.10.3 — Сопровождение (T7)

**Источник:** аудит P2.

### T7-1 — MainWindow ≤ 1200 ⬜

**Цель:** закрыть хвост T2-4 (сейчас **1222** строки).

**Поведение:**
- Вынести ещё один связный блок (кандидаты: drag-drop handlers, status/sync, `_reset_layout` cluster) в `main_window_*.py`

**Критерии:**
- [ ] `main_window.py` ≤ 1200 строк
- [ ] `test_menu_structure.py`, `test_main_window_smoke.py` зелёные

**Оценка:** S

---

### T7-2 — Архив спринтов ⬜

**Цель:** `archive/COMPLETED_SPRINTS.md` отражает v0.10.x.

**Критерии:**
- [ ] Таблица: спринты 10–14, релизы v0.9.0–v0.10.1
- [ ] Ссылка из README при необходимости

**Оценка:** S

---

### T7-3 — Ruff rules ⬜

**Цель:** явная конфигурация линтера.

**Поведение:**
- `[tool.ruff.lint] select = [...]` — минимум `E`, `F`, `I`, `UP`
- Исправить новые находки или `ignore` с комментарием

**Критерии:**
- [ ] CI ruff без сюрпризов
- [ ] Документировано в `tests/README.md` или CONTRIBUTING one-liner

**Оценка:** S

---

### T7-4 — Guard для split-скриптов ⬜

**Цель:** ловить mixin-методы без `self` до runtime.

**Поведение:**
- `scripts/check_mixin_methods.py` — AST: методы в `*_coordinator.py` / `recording_session.py` должны иметь `self`
- Опционально: шаг в CI или pre-commit (документировать)

**Критерии:**
- [ ] Скрипт ловит `_status_brief(message)` без `self`
- [ ] Упоминание в `docs/MIGRATION.md`

**Оценка:** S

---

## Спринт 17 — T8a: Player — исполнение шагов

**База:** `player.py` ~1594 строк. Релиз **v0.11.0** — после спринта 18.

### T8a-1 — `player_step_executor.py` ⬜

**Цель:** вынести `execute_step` и dispatch по `action`.

**Критерии:**
- [ ] Модуль ≤ 600 строк
- [ ] `tests/test_player_execute.py` без изменений поведения

**Оценка:** L

---

### T8a-2 — `player_context.py` ⬜

**Цель:** `RunContext`, переменные, `fill_generated`, downloads state — отдельно от Playwright page API.

**Критерии:**
- [ ] `tests/test_run_variables.py`, `test_player_execute.py` (generated) зелёные

**Оценка:** M · **Зависимости:** T8a-1 частично

---

### T8a-3 — Урезать `player.py` (промежуточно) ⬜

**Критерии:**
- [ ] `player.py` ≤ 1100 строк после T8a
- [ ] Нет циклических импортов

**Оценка:** S

---

## Спринт 18 → v0.11.0 — T8b: Player — фасад

### T8b-1 — `player_highlight.py` ⬜

**Цель:** `_maybe_highlight`, cleanup, picker overlay hooks.

**Оценка:** M

---

### T8b-2 — Worker lifecycle ⬜

**Цель:** thread/worker/queue остаются в `ScenarioPlayer`; координаторы — делегаты.

**Критерии:**
- [ ] Ручной smoke: прогон, stop, play from step N, batch queue

**Оценка:** M

---

### T8b-3 — `player.py` ≤ 900 ⬜

**Критерии:**
- [ ] LOC ≤ 900
- [ ] `scripts/split_player.py` (опционально, по образцу recording_controller)

**Оценка:** S · **Зависимости:** T8a-*

---

## Спринт 19 → v0.11.1 — Gherkin split (T9)

### T9-1 — `gherkin_parse.py` ⬜

**Цель:** парсинг строк → step dict.

**Критерии:**
- [ ] `tests/test_gherkin_ru.py` зелёные

**Оценка:** L

---

### T9-2 — `gherkin_serialize.py` ⬜

**Цель:** step dict → текст `.feature`.

**Оценка:** M

---

### T9-3 — `gherkin_ru.py` фасад ⬜

**Критерии:**
- [ ] `gherkin_ru.py` ≤ 800 строк
- [ ] Публичные импорты сохранены (`gherkin_to_steps`, `parse_gherkin_steps`, …)

**Оценка:** S

---

### T9-4 — Блоки и контекст ⬜

**Цель:** не дублировать логику с `gherkin_blocks.py` / `gherkin_context.py`.

**Критерии:**
- [ ] `test_gherkin_blocks.py`, `test_gherkin_context.py` зелёные

**Оценка:** M

---

## Спринт 20 → v0.11.2 — Static typing (T10)

### T10-1 — mypy в проекте ⬜

**Поведение:**
- `optional-dependencies.dev`: `mypy>=1.0`
- `[tool.mypy]` — `python_version`, `packages = ["app.mvc"]`

**Оценка:** S

---

### T10-2 — CI mypy ⬜

**Критерии:**
- [ ] Шаг в `ci.yml` или отдельный job
- [ ] 0 errors на `app/mvc/controllers/`, `app/mvc/models/`

**Оценка:** M · **Зависимости:** T10-1, желательно T8

---

### T10-3 — Типы export + catalog ⬜

**Критерии:**
- [ ] `app/playwright_export.py`, `app/step_catalog.py` в scope mypy
- [ ] Без `# type: ignore` без комментария

**Оценка:** M

---

## Сводная таблица

| ID | Название | Спринт | Оценка | Статус | Блокирует |
|----|----------|--------|--------|--------|-----------|
| T1-1 | CI workflow | 10 | S | ✅ | T1-3, T4-* |
| T1-2 | Зависимости | 10 | S | ✅ | — |
| T1-3 | Ruff CI | 10 | S | ✅ | T1-1 |
| T1-4 | Док тестов | 10 | S | ✅ | — |
| T2-1 | Update module | 11 | M | ✅ | — |
| T2-2 | Menu factory | 11 | M | ✅ | T2-3 |
| T2-3 | Batch module | 11 | M | ✅ | — |
| T2-4 | MainWindow LOC | 11 | S | ✅ | T2-1…3 |
| T3-1 | PlaybackCoordinator | 12 | M | ✅ | — |
| T3-2 | ValidateCoordinator | 12 | M | ✅ | — |
| T3-3 | RecordingSession | 12 | L | ✅ | — |
| T3-4 | RecordingController LOC | 12 | S | ✅ | T3-1…3 |
| T4-1 | Integration subprocess | 13 | L | ✅ | T4-4 |
| T4-2 | Qt smoke | 13 | M | ✅ | — |
| T4-3 | Убрать skip CI | 13 | M | ✅ | T4-1, T4-2 |
| T4-4 | Release без retry | 13 | S | ✅ | T4-1…3 |
| T5-1 | Export audit | 14 | M | ✅ | — |
| T5-2 | CHANGELOG | 14 | S | ✅ | — |
| T5-3 | VERSIONING в git | 14 | S | ✅ | — |
| T6-1 | Update UI tests CI | 15 | M | ✅ | T6-4 |
| T6-2 | Toolbar resize CI | 15 | M | ✅ | T6-4 |
| T6-3 | `_status_brief` test | 15 | S | ✅ | — |
| T6-4 | Docs 0 skip | 15 | S | ✅ | T6-1, T6-2 |
| T7-1 | MainWindow LOC | 16 | S | ⬜ | — |
| T7-2 | Archive v0.10 | 16 | S | ⬜ | — |
| T7-3 | Ruff select | 16 | S | ⬜ | — |
| T7-4 | Mixin guard script | 16 | S | ⬜ | — |
| T8a-1 | player_step_executor | 17 | L | ⬜ | T8b-* |
| T8a-2 | player_context | 17 | M | ⬜ | T8a-1 |
| T8a-3 | player interim LOC | 17 | S | ⬜ | T8a-1,2 |
| T8b-1 | player_highlight | 18 | M | ⬜ | T8a-* |
| T8b-2 | player worker | 18 | M | ⬜ | T8a-* |
| T8b-3 | player ≤900 | 18 | S | ⬜ | T8b-1,2 |
| T9-1 | gherkin_parse | 19 | L | ⬜ | T9-3 |
| T9-2 | gherkin_serialize | 19 | M | ⬜ | T9-1 |
| T9-3 | gherkin_ru facade | 19 | S | ⬜ | T9-1,2 |
| T9-4 | blocks integration | 19 | M | ⬜ | T9-1 |
| T10-1 | mypy config | 20 | S | ⬜ | T10-2 |
| T10-2 | mypy CI | 20 | M | ⬜ | T10-1, T8 |
| T10-3 | mypy export/catalog | 20 | M | ⬜ | T10-2 |

---

## Риски

| Риск | Задачи | Митигация |
|------|--------|-----------|
| Рефакторинг ломает хоткеи | T2-2, T7-1 | тесты меню; не менять `QAction.objectName` |
| Циклические импорты при split | T2, T3, T8, T9 | `TYPE_CHECKING`, lazy imports, `app/mvc/types.py` |
| Subprocess тесты медленнее | T4-1 | отдельный subprocess; документировано |
| Export scope creep | T5-1 | каталог веб-шагов only |
| Player split ломает прогон | T8* | T6 сначала; `test_player_execute.py`; ручной smoke |
| Gherkin split ломает `.feature` | T9* | только move code; golden tests `test_gherkin_ru.py` |
| mypy шум до split player | T10 | T10 после T8; узкий scope `app/mvc/` |

---

## Definition of Done

1. Код + pytest по задаче
2. CI зелёный (после T1-1)
3. Для T2/T3 — ручной smoke сценарий: открыть проект → запись → прогон
4. CHANGELOG при релизе (после T5-2)
