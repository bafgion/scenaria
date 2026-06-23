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

## Split modules (mixins)

Large Qt/controllers modules use mixins (`main_window_*.py`, `*_coordinator.py`, `recording_session.py`).  
Every **instance method** on a mixin class must take `self` as the first parameter (see sprint 12 regression).

Before push:

```bash
python scripts/check_mixin_methods.py
```

CI runs the same guard after `ruff check`.

## User docs

- [GETTING_STARTED.md](GETTING_STARTED.md)
- [../examples/README.md](../examples/README.md)
