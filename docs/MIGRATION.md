# PySide6 + MVC

Qt UI — единственный интерфейс приложения.

## Structure

```
app/
  mvc/
    models/       # state, no widgets
    controllers/  # actions, wiring
  qt/
    widgets/      # views
    theme.py
    main_window.py
  recorder.py
  player.py
  feature_store.py
  gherkin_ru.py
  scenario_utils.py
  run_display.py
  step_display.py
```

## Run

```bash
python main.py
```

Portable build: `scripts\build.ps1` → `dist\Scenaria\Scenaria.exe`
