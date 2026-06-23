# Задачи roadmap — технический долг

Детальная спецификация для [ROADMAP.md](ROADMAP.md) (фазы T1–T5).  
Продуктовые спринты 1–9: [archive/COMPLETED_SPRINTS.md](archive/COMPLETED_SPRINTS.md).

**Обновлено:** 2026-06-23 · **База:** master v0.10.0 (спринт 13)  
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
| **14** | v0.10.1 | T5 — Export и docs | ⬜ | 0/3 |

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

## Спринт 14 → v0.10.1 — Export и сопровождение

### T5-1 — Playwright export audit ⬜

**Цель:** убрать «тихие» `TODO` в экспорте.

**Поведение:**
- Таблица: шаг каталога → TS/Python генератор или `unsupported`
- GUI/CLI: предупреждение при экспорте с unsupported шагами

**Файлы:**
- `app/playwright_export.py`, `tests/test_playwright_export.py`

**Критерии:**
- [ ] Нет `TODO: generate` для шагов из основного каталога ИЛИ явный список в docs
- [ ] Тест на каждый поддерживаемый action

**Оценка:** M

---

### T5-2 — CHANGELOG.md ⬜

**Цель:** пользовательская история релизов в репозитории.

**Содержание:**
- v0.7.0 … v0.8.1 из release notes GitHub (кратко)
- Шаблон для следующих релизов

**Критерии:**
- [ ] Ссылка из README
- [ ] Процесс в RELEASE.md: «добавить секцию в CHANGELOG перед тегом»

**Оценка:** S

---

### T5-3 — VERSIONING.md в git ⬜

**Цель:** правила версий видны контрибьюторам.

**Критерии:**
- [ ] Файл не в `.gitignore`
- [ ] Согласован с ROADMAP (таблица релизов T1–T5)

**Оценка:** S

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
| T4-1 | Integration subprocess | 13 | L | ⬜ | T4-4 |
| T4-2 | Qt smoke | 13 | M | ⬜ | — |
| T4-3 | Убрать skip CI | 13 | M | ⬜ | T4-1, T4-2 |
| T4-4 | Release без retry | 13 | S | ⬜ | T4-1…3 |
| T5-1 | Export audit | 14 | M | ⬜ | — |
| T5-2 | CHANGELOG | 14 | S | ⬜ | — |
| T5-3 | VERSIONING в git | 14 | S | ⬜ | — |

---

## Риски

| Риск | Задачи | Митигация |
|------|--------|-----------|
| Рефакторинг ломает хоткеи | T2-2 | тесты меню; не менять `QAction.objectName` |
| Циклические импорты при split | T2, T3 | выносить протоколы/типы в `app/mvc/types.py` |
| Subprocess тесты медленнее | T4-1 | отдельный CI job, параллель с unit |
| Export scope creep | T5-1 | только каталог веб-шагов; VA — out of scope |

---

## Definition of Done

1. Код + pytest по задаче
2. CI зелёный (после T1-1)
3. Для T2/T3 — ручной smoke сценарий: открыть проект → запись → прогон
4. CHANGELOG при релизе (после T5-2)
