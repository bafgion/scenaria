# Scenaria

**Scenaria** — desktop-приложение для записи и автоматического воспроизведения автотестов сайтов. Сценарии хранятся в **русском Gherkin** (`.feature`) и выполняются через **Playwright**.

Подходит для любых сайтов: формы, модалки, навигация, загрузка файлов, проверки.

## Возможности

- Запись кликов, ввода, навигации, чекбоксов и др.
- Редактор Gherkin с автодополнением (Ctrl+Space)
- Дерево проекта, поиск, статусы последнего прогона
- Воспроизведение в открытом браузере или headless
- Пакетный запуск всех `.feature` в проекте
- Экспорт: Gherkin, JSON, ZIP, Playwright (TypeScript / Python)
- CLI для CI без GUI

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
python -m app run ./features/login.feature
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

Результат: `dist/Scenaria/` и `dist/Scenaria-Portable.zip`. Копируйте **всю папку** (внутри `browsers/` с Chromium).

Подробнее: [docs/RELEASE.md](docs/RELEASE.md) — авторелизы GitHub и автообновление portable EXE.

## Рабочий процесс

1. **Открыть проект** — папка с `.feature` файлами (проводник слева)
2. Создать или открыть сценарий
3. **Открыть браузер** → при необходимости **Начать запись**
4. **Остановить запись** — шаги появятся в редакторе
5. **Сохранить** (Ctrl+S) — запись в `.feature`
6. **Запустить тест** (Ctrl+Enter) — перед запуском Gherkin применяется автоматически

Неприменённые правки в редакторе подсвечиваются баннером «Применить». При запуске теста они применяются сами; для ручного применения: **Ctrl+Shift+S**.

## Шаги Gherkin (кратко)

| Категория | Примеры |
|-----------|---------|
| Навигация | `открыт "url"`, `обновляю страницу`, `возвращаюсь назад` |
| Действия | `нажимаю`, `ввожу`, `выбираю`, `отмечаю`, `нажимаю клавишу "Enter"` |
| Ожидание | `жду 2 сек`, `жду появления`, `жду исчезновения` |
| Проверки | `вижу`, `не вижу`, `проверяю текст`, `проверяю url` |

Полный список — **Ctrl+Space** в редакторе или «Справка» под редактором.

## Данные приложения

Черновики и настройки: `%APPDATA%\Scenaria\` (или `data\` рядом с exe в portable-сборке).

Настройки записи (`Только важные`, `Только ссылки`, `Headless`) сохраняются между сеансами.

## Структура проекта

```
app/
  gherkin_ru.py      # парсер/сериализатор Gherkin
  player.py          # воспроизведение Playwright
  recorder.py        # запись из браузера
  qt/                # интерфейс PySide6
tests/               # pytest
```

## Сторонние компоненты

Иконки в интерфейсе — [Lucide](https://lucide.dev) (MIT License). SVG-разметка встроена в `app/qt/lucide_svgs.py`.
