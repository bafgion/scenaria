# PySide6 + MVC

Qt UI — единственный интерфейс приложения.

## Structure

```
app/
  mvc/
    models/       # state, no widgets
    controllers/  # actions, wiring
  qt/
    widgets/      # views (welcome, editor, step help, …)
    theme.py
    main_window.py
  recorder.py
  player.py
  step_catalog.py # step help categories
  feature_store.py
  gherkin_ru.py
  gherkin_context.py   # Контекст / TestClient в .feature
  gherkin_blocks.py    # Если / Повторяю / Пока / Для каждого
  test_clients.py      # .scenaria/test_clients/*.json
examples/         # shipped beginner .feature files
docs/             # user + release docs
```

## Run

```bash
python main.py
```

Portable build: `scripts\build.ps1` → `dist\Scenaria\Scenaria.exe` (includes `examples/`).

## User docs

- [GETTING_STARTED.md](GETTING_STARTED.md)
- [../examples/README.md](../examples/README.md)
