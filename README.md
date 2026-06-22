# Scenaria

**Scenaria** — desktop-приложение для записи и автоматического воспроизведения автотестов сайтов. Сценарии хранятся в **русском Gherkin** (`.feature`) и выполняются через **Playwright**.

Подходит для любых сайтов: формы, модалки, навигация, загрузка файлов, проверки.

## Быстрый старт

1. Установите зависимости и запустите `python main.py`
2. На вкладке **«Старт»** нажмите **«Открыть примеры сценариев»**
3. Запустите `01-pervaya-proverka.feature` (**Ctrl+Enter**)

Подробное руководство: **[docs/GETTING_STARTED.md](docs/GETTING_STARTED.md)**  
Примеры сценариев: **[examples/](examples/)**

## Возможности

- Запись кликов, ввода, навигации, чекбоксов и др.
- Редактор Gherkin с автодополнением (**Ctrl+Space**)
- Справка по шагам с категориями (условия, циклы, генераторы…)
- Дерево проекта, поиск, статусы последнего прогона
- Условия (`Если …`) и циклы (`Повторяю`, `Пока`, `Для каждого`)
- Воспроизведение в открытом браузере или headless
- Пакетный запуск всех `.feature` в проекте
- Экспорт: Gherkin, JSON, ZIP, Playwright (TypeScript / Python)
- CLI для CI без GUI
- Portable EXE (Windows) с автообновлением

## Установка

```powershell
cd scenaria
pip install -r requirements.txt
python -m playwright install chromium
```

Разработка и тесты:

```powershell
pip install -r requirements-dev.txt
python -m pytest tests/ -q
```

Или через `pyproject.toml`:

```powershell
pip install -e ".[dev]"
```

## Запуск GUI

```powershell
python main.py
```

## CLI (без окна)

```powershell
# Запуск одного файла или всей папки проекта (headless)
python -m app run ./examples/01-pervaya-proverka.feature
python -m app run ./my-project --junit report.xml

# С видимым браузером
python -m app run ./features --headed

# Экспорт в Playwright
python -m app export ./features/login.feature -o test_login.spec.ts
python -m app export ./features/login.feature --python -o test_login.py
```

`main.py` также пробрасывает подкоманды: `python main.py run …`, `python main.py export …`.

## Сборка portable EXE (Windows)

```powershell
cd scenaria\scripts
.\build.ps1
```

Результат: `dist/Scenaria/` (включая `examples/`) и `dist/Scenaria-Portable.zip`. Копируйте **всю папку** (внутри `browsers/` с Chromium).

Подробнее: [docs/RELEASE.md](docs/RELEASE.md) — авторелизы GitHub и автообновление portable EXE.

## Рабочий процесс

1. **Открыть проект** — папка с `.feature` файлами (проводник слева) или **примеры** со «Старта»
2. Создать или открыть сценарий
3. **Открыть браузер** → при необходимости **Начать запись**
4. **Остановить запись** — шаги появятся в редакторе
5. **Сохранить** (Ctrl+S) — запись в `.feature`
6. **Запустить тест** (Ctrl+Enter) — перед запуском Gherkin применяется автоматически

Неприменённые правки в редакторе подсвечиваются баннером «Применить». При запуске теста они применяются сами; для ручного применения: **Ctrl+Shift+S**.

В панели действий **chip** с именем файла показывает, какой сценарий открыт (на вкладке «Старт» скрыт).

## Шаги Gherkin (кратко)

| Категория | Примеры |
|-----------|---------|
| Навигация | `открыт "url"`, `обновляю страницу`, `возвращаюсь назад` |
| Формы и ввод | `нажимаю`, `ввожу`, `выбираю`, `отмечаю`, `загружаю файл` |
| Генераторы | `ввожу случайный телефон`, `ввожу "{{first_name}}"` |
| Ожидание | `жду 2 сек`, `жду появления`, `жду исчезновения` |
| Проверки | `вижу`, `не вижу`, `проверяю текст`, `проверяю url` |
| Условия | `Если вижу "…"`, `Если url содержит "…"` + вложенные шаги |
| Циклы | `Повторяю 3 раза`, `Пока вижу "…"`, `Для каждого "…" как "var"` |

Полный каталог — **Ctrl+Space** в редакторе или **Справка → Справка по шагам…**

## Документация

| Файл | Содержание |
|------|------------|
| [docs/GETTING_STARTED.md](docs/GETTING_STARTED.md) | Первые шаги, интерфейс, Gherkin |
| [examples/README.md](examples/README.md) | Готовые примеры для новичков |
| [docs/RELEASE.md](docs/RELEASE.md) | Сборка, релизы, автообновление |
| [docs/VERSIONING.md](docs/VERSIONING.md) | SemVer и теги |
| [docs/ROADMAP.md](docs/ROADMAP.md) | Планы развития |
| [docs/MIGRATION.md](docs/MIGRATION.md) | Структура кода (для разработчиков) |

## Данные приложения

Черновики и настройки: `%APPDATA%\Scenaria\` (или `data\` рядом с exe в portable-сборке).

Настройки записи (`Только важные`, `Только ссылки`, `Headless`) сохраняются между сеансами.

## Структура проекта

```
app/
  gherkin_ru.py      # парсер/сериализатор Gherkin
  player.py          # воспроизведение Playwright
  recorder.py        # запись из браузера
  step_catalog.py    # справка и категории шагов
  qt/                # интерфейс PySide6
examples/            # примеры сценариев для новичков
docs/                # документация
tests/               # pytest
```

## Сторонние компоненты

Иконки в интерфейсе — [Lucide](https://lucide.dev) (MIT License). SVG-разметка встроена в `app/qt/lucide_svgs.py`.
