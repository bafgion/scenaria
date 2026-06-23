# Scenaria — завершённые спринты (v0.3.0 … v0.10.2)

Архив продуктового и технического roadmap. Детальные спецификации задач A1…V1, F4…F7, T1…T6 удалены — статус зафиксирован здесь.

**Текущий релиз:** v0.10.1 (GitHub). Код спринтов 15–16 в master; тег **v0.10.2+** — по мере релизов.

---

## Сводка релизов

| Версия | Спринт | Содержание |
|--------|--------|------------|
| v0.3.0 | 1 | Теги, post-record hints, browser session |
| v0.4.0 | 2–3 | Умные селекторы, расширенная запись, HTML-отчёты, validate, подсветка Gherkin |
| v0.4.1–v0.5.0 | 4 | CLI, история прогонов, сниппеты, find/replace по проекту |
| v0.5.0+ | 5 | Переменные, download, Firefox/WebKit, каталог шагов |
| v0.5.9 | F7 | Lucide-иконки, прогресс обновления (F5-1/2) |
| v0.6.0–v0.6.7 | — | Примеры, chip сценария, UX панелей прогона (F6-9), патчи installer |
| v0.7.0 | 6 | Плагины P0, add-on scenaria-vanessa V1, условия/циклы/Outline |
| v0.8.0 | 7 | Меню F4, TestClient (B1-3), единый GUI |
| v0.8.1 | 8 | F5-3 отмена/indeterminate обновления; фикс TestClient save dialog |
| v0.9.0 | 9 | F6: простой toolbar, чеклист Старт, настройки, batch-выбор в каталоге, B3-7 picker на паузе |
| v0.9.0 | 10 | T1: CI на PR, единые зависимости, ruff |
| v0.9.1 | 11 | T2: split MainWindow (mixins) |
| v0.9.2 | 12 | T3: split RecordingController |
| v0.10.0 | 13 | T4: стабильность тестов (integration subprocess) |
| v0.10.1 | 14 | T5: Playwright export audit, CHANGELOG, VERSIONING |
| v0.10.2 | 15 | T6: 0 skipped тестов на CI (update UI, toolbar) |

---

## Эпики (продукт — все закрыты)

| Эпик | Тема | Статус |
|------|------|--------|
| A1–A9 | Gherkin, теги, переменные, условия, Outline | ✅ |
| B1–B4 | Сессия, TestClient, запись, движки | ✅ |
| B3-7 | Picker и инструменты на паузе записи | ✅ |
| C1–C5 | Отчёты, validate, CLI, история, параллельный batch | ✅ |
| D1 | Умные селекторы | ✅ |
| E1–E2 | Подсветка, quick fixes | ✅ |
| F1–F4 | Справка, прогресс, DnD, меню / Command Palette | ✅ |
| F5 | UX автообновления portable | ✅ |
| F6 | Дружелюбный GUI для QA | ✅ |
| F7 | Lucide | ✅ |
| P0, V1 | Плагины, Vanessa add-on | ✅ |

---

## Технический долг (закрыто в v0.10.x)

| Фаза | Спринты | Тема | Статус |
|------|---------|------|--------|
| T1 | 10 | CI, зависимости, ruff | ✅ |
| T2 | 11 | MainWindow mixins | ✅ |
| T3 | 12 | RecordingController split | ✅ |
| T4 | 13 | Тесты, subprocess isolation | ✅ |
| T5 | 14 | Export audit, CHANGELOG | ✅ |
| T6 | 15 | CI без skip | ✅ |

---

## Вне scope (не планировалось)

- Облачный runner
- Visual screenshot diff
- 1С-шаги в палитре Scenaria (только в Vanessa)

---

Дальнейшее развитие: [ROADMAP.md](../ROADMAP.md) — спринты 16–20 (T7–T10).
