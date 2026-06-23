# Задачи roadmap — технический долг

Детальная спецификация для [ROADMAP.md](ROADMAP.md) (фазы T1–T5).  
Продуктовые спринты 1–9: [archive/COMPLETED_SPRINTS.md](archive/COMPLETED_SPRINTS.md).

**Обновлено:** 2026-06-23 · **База:** master v0.9.0 (спринт 10)  
**Формат:** цель → файлы → критерии приёмки → тесты  
**Оценка:** **S** (1–2 дня), **M** (3–5 дней), **L** (1–2 недели)  
**Статус:** ✅ готово · 🔶 частично · ⬜ не начато

---

## Журнал прогресса

| Спринт | Версия | Тема | Статус | Прогресс |
|--------|--------|------|--------|----------|
| **10** | v0.9.0 | T1 — CI и зависимости | ✅ | 4/4 |
| **11** | v0.9.1 | T2 — MainWindow | ⬜ | 0/4 |
| **12** | v0.9.2 | T3 — RecordingController | ⬜ | 0/4 |
| **13** | v0.10.0 | T4 — Тесты | ⬜ | 0/4 |
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

## Спринт 11 → v0.9.1 — Декомпозиция MainWindow

### T2-1 — Модуль обновлений ⬜

**Цель:** вынести update flow из `main_window.py`.

**Поведение:**
- Класс или mixin `MainWindowUpdateMixin` / `UpdateUiController` в `app/qt/main_window_update.py`
- Методы: check, download, progress dialog, cancel, open log
- `MainWindow` делегирует; сигналы без изменения для пользователя

**Критерии:**
- [ ] `main_window.py` уменьшен ≥ 200 строк
- [ ] Существующие `test_update_*.py` зелёные
- [ ] Ручной smoke: проверка обновления (mock или staging)

**Оценка:** M · **Зависимости:** T1-1 (желательно)

---

### T2-2 — Фабрика меню ⬜

**Цель:** сборка QAction и меню вне `MainWindow.__init__`.

**Файлы:**
- `app/qt/main_window_menus.py` — функции `build_menus(window) -> MenuHandles`
- Или группы: project, scenario, record, plugins, view, help

**Критерии:**
- [ ] Горячие клавиши без изменений (`test_main_window_menus.py` / аналог)
- [ ] `main_window.py` уменьшен ≥ 300 строк суммарно с T2-1

**Оценка:** M

---

### T2-3 — Пакетный прогон и выбор каталога ⬜

**Цель:** логика «Выбрано N», run selected, batch runners — отдельный модуль.

**Файлы:**
- `app/qt/main_window_batch.py`

**Критерии:**
- [ ] `test_catalog_run_selection*.py` зелёные
- [ ] ПКМ каталога и меню «Запуск» работают как раньше

**Оценка:** M · **Зависимости:** T2-2 частично

---

### T2-4 — Лимит размера MainWindow ⬜

**Цель:** зафиксировать результат спринта.

**Критерии:**
- [ ] `main_window.py` ≤ **1 200** строк (без пустых комментариев-заглушек)
- [ ] Нет новых циклических импортов
- [ ] `pytest tests/test_main_window*.py -q` зелёный

**Оценка:** S · **Зависимости:** T2-1…T2-3

---

## Спринт 12 → v0.9.2 — Декомпозиция RecordingController

### T3-1 — PlaybackCoordinator ⬜

**Цель:** play/stop/pause, run from step, headless — отдельный класс.

**Файлы:**
- `app/mvc/controllers/playback_coordinator.py`
- `recording_controller.py` — делегирование

**Критерии:**
- [ ] `test_recording_controller.py`, `test_player*.py` зелёные
- [ ] Нет изменения публичных сигналов `RecordingController`

**Оценка:** M

---

### T3-2 — ValidateCoordinator ⬜

**Цель:** validate selectors и связь с `ValidateResultsPanel`.

**Файлы:**
- `app/mvc/controllers/validate_coordinator.py`

**Критерии:**
- [ ] `test_validate*.py` зелёные
- [ ] GUI validate из меню и toolbar без регрессии

**Оценка:** M

---

### T3-3 — RecordingSession ⬜

**Цель:** open browser, record modes, TestClient, picker, append record.

**Файлы:**
- `app/mvc/controllers/recording_session.py`

**Критерии:**
- [ ] `test_recording_pause_tools.py`, `test_recording_controller.py` зелёные
- [ ] TestClient + open browser smoke

**Оценка:** L

---

### T3-4 — Лимит размера RecordingController ⬜

**Критерии:**
- [ ] `recording_controller.py` ≤ **800** строк
- [ ] Контроллер остаётся единой точкой входа для `AppController`

**Оценка:** S · **Зависимости:** T3-1…T3-3

---

## Спринт 13 → v0.10.0 — Стабильность тестов

### T4-1 — Integration в subprocess ⬜

**Цель:** Playwright-тесты не делят процесс с Qt.

**Поведение:**
- `pytest` marker `integration_subprocess` или wrapper `tests/run_integration_isolated.py`
- `conftest.py`: integration job в CI отдельно или последним в subprocess

**Критерии:**
- [ ] Полный `pytest` на Windows без access violation (≥ 3 прогона подряд)
- [ ] Документация в `tests/README.md`

**Оценка:** L · **Зависимости:** T1-1

---

### T4-2 — Безопасные Qt smoke ⬜

**Цель:** минимальный тест `MainWindow` с mock recorder/player.

**Поведение:**
- `tests/test_main_window_smoke.py` — создать окно, закрыть, без Chromium
- Не запускать после integration в том же процессе (порядок в conftest)

**Критерии:**
- [ ] Тест стабилен на CI (не skip)
- [ ] Время < 5 с

**Оценка:** M

---

### T4-3 — Убрать лишние skip на GITHUB_ACTIONS ⬜

**Цель:** вернуть отключённые Qt-тесты, где возможно.

**Критерии:**
- [ ] Список skip сокращён; каждый оставшийся skip — комментарий «почему»
- [ ] CI зелёный

**Оценка:** M · **Зависимости:** T4-1, T4-2

---

### T4-4 — Release workflow без retry ×3 ⬜

**Цель:** один прогон pytest в `release.yml` при стабильном CI.

**Критерии:**
- [ ] `release.yml`: цикл retry удалён или max 1
- [ ] Последний релизный тег прошёл CI с первой попытки

**Оценка:** S · **Зависимости:** T4-1…T4-3

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
| T2-1 | Update module | 11 | M | ⬜ | — |
| T2-2 | Menu factory | 11 | M | ⬜ | T2-3 |
| T2-3 | Batch module | 11 | M | ⬜ | — |
| T2-4 | MainWindow LOC | 11 | S | ⬜ | T2-1…3 |
| T3-1 | PlaybackCoordinator | 12 | M | ⬜ | — |
| T3-2 | ValidateCoordinator | 12 | M | ⬜ | — |
| T3-3 | RecordingSession | 12 | L | ⬜ | — |
| T3-4 | RecordingController LOC | 12 | S | ⬜ | T3-1…3 |
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
