# Branding assets

Preview PNG variants (512×512, for `.ico` conversion):

| File | Concept |
|------|---------|
| `icon-variant-b-monogram-su.png` | Монограмма SU + узлы шагов сценария, мягкий дружелюбный стиль (**основной**) |
| `icon-variant-a-browser-gherkin.png` | Браузер + рамка инспектора + Gherkin |
| `icon-variant-c-record-click.png` | Record + клик по кнопке |

`app-icon.svg` — упрощённый вектор (запасной).

`app-icon-mark.png` / `app-icon-square.png` — обрезка мастер-иконки без чёрных полей.

`app.ico` — иконка exe (генерация: `python scripts/generate_app_icon.py`).

## Сборка `.ico` для Windows

```powershell
python scripts/generate_app_icon.py
```

В `Scenaria.spec` уже указано `icon="assets/branding/app.ico"`.
