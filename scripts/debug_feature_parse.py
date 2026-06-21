from pathlib import Path

from app.gherkin_ru import GherkinParseError, gherkin_to_steps

path = Path(r"c:\Users\bafgion\Downloads") / "Создание Без договора.feature"
full = path.read_text(encoding="utf-8")
lines = full.splitlines()

for drop in (0, 1, 2, 3):
    text = "\n".join(lines[: len(lines) - drop]) + "\n"
    try:
        steps = gherkin_to_steps(text)
        print(f"drop {drop}: OK {len(steps)} steps, last={steps[-1].get('action')}")
    except GherkinParseError as exc:
        print(f"drop {drop}: FAIL line {exc.line_no}: {exc}")
