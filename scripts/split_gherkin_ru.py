"""Gherkin module layout reference after T9 split.

Run from repo root:
    python scripts/split_gherkin_ru.py

Modules:
    gherkin_ru.py        — constants, feature structure, quote helpers, re-exports
    gherkin_parse.py     — step line parsing, normalization, repair
    gherkin_serialize.py — steps_to_gherkin, build_feature_text, merge
    gherkin_blocks.py    — Если / Повторяю / Пока / Для каждого
    gherkin_context.py   — Контекст block and TestClient steps
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULES = [
    "app/gherkin_ru.py",
    "app/gherkin_parse.py",
    "app/gherkin_serialize.py",
    "app/gherkin_blocks.py",
    "app/gherkin_context.py",
]


def main() -> None:
    print("Gherkin package layout (post T9):")
    total = 0
    for rel in MODULES:
        path = ROOT / rel
        lines = len(path.read_text(encoding="utf-8").splitlines()) if path.is_file() else 0
        total += lines
        print(f"  {rel}: {lines}")
    print(f"  total: {total}")


if __name__ == "__main__":
    main()
