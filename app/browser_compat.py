"""Per-engine step compatibility notes for validate (B4-2)."""

from __future__ import annotations

from app.browser_config import BROWSER_ENGINES, normalize_browser_engine

# action -> {engine: warning message}
_STEP_ENGINE_WARNINGS: dict[str, dict[str, str]] = {
    "draw_signature": {
        "firefox": "Рисование подписи на canvas может отличаться в Firefox — проверьте вручную",
        "webkit": "Рисование подписи на canvas может отличаться в WebKit — проверьте вручную",
    },
    "upload": {
        "webkit": "Загрузка файлов в WebKit иногда требует видимого input — проверьте прогон",
    },
    "prompt_email_code": {
        "firefox": "Сегментированный ввод OTP протестируйте в Firefox отдельно",
        "webkit": "Сегментированный ввод OTP протестируйте в WebKit отдельно",
    },
}


def compatibility_warning(action: str, engine: str | None) -> str | None:
    """Return a non-fatal warning for *action* on *engine*, or None."""
    resolved = normalize_browser_engine(engine)
    if resolved == "chromium":
        return None
    return _STEP_ENGINE_WARNINGS.get(str(action or ""), {}).get(resolved)


def list_engine_warnings(steps: list[dict], engine: str | None) -> list[tuple[int, str, str]]:
    """Flatten steps (including nested if/repeat) and collect warnings."""
    result: list[tuple[int, str, str]] = []

    def walk(items: list[dict], index_hint: int) -> None:
        for step in items:
            action = str(step.get("action", "") or "")
            if action in {"if", "repeat"}:
                walk(list(step.get("steps") or []), index_hint)
                continue
            message = compatibility_warning(action, engine)
            if message:
                result.append((index_hint, action, message))
            index_hint += 1

    walk(list(steps), 1)
    return result


def supported_engines() -> tuple[str, ...]:
    return BROWSER_ENGINES
