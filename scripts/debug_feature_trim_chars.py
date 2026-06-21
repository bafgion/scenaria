from pathlib import Path

from app.gherkin_ru import GherkinParseError, gherkin_to_steps

path = Path(r"c:\Users\bafgion\Downloads") / "Создание Без договора.feature"
full = path.read_text(encoding="utf-8")

failures = 0
for length in range(len(full), len(full) - 500, -1):
    text = full[:length]
    try:
        gherkin_to_steps(text)
    except GherkinParseError as exc:
        failures += 1
        if failures <= 10:
            tail = text.splitlines()[-1] if text.splitlines() else ""
            print(f"len={length} line={exc.line_no} tail={tail[:80]!r}")

print("total failures in last 500 chars window:", failures)
