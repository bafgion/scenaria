"""Headless CLI for running `.feature` scenarios."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

from app.junit_report import write_junit_report
from app.paths import configure_playwright_browsers
from app.playwright_export import ExportFormat, export_scenario_playwright
from app.feature_store import load_feature
from app.run_suite import format_suite_summary, run_feature_paths


def run_command(args: argparse.Namespace) -> int:
    configure_playwright_browsers()
    paths = [Path(p) for p in args.paths]
    cases = run_feature_paths(
        paths,
        headless=not args.headed,
        slow_mo_ms=args.slow_mo,
        on_log=print,
    )
    if not cases:
        print("Не найдено .feature файлов", file=sys.stderr)
        return 2

    failed = sum(1 for case in cases if not case.get("success"))
    for case in cases:
        if not case.get("success"):
            print(f"FAIL: {case.get('message', '')}", file=sys.stderr)
        else:
            print(f"OK ({case.get('executed', 0)}/{case.get('total', 0)})")

    if args.junit:
        write_junit_report(Path(args.junit), cases=cases)

    print(f"\n{format_suite_summary(cases)}")
    return 1 if failed else 0


def export_command(args: argparse.Namespace) -> int:
    source = Path(args.source).resolve()
    if not source.is_file():
        print(f"Файл не найден: {source}", file=sys.stderr)
        return 2

    feature = load_feature(source)
    scenario = {
        "name": feature.get("name", source.stem),
        "startUrl": feature.get("startUrl", ""),
        "steps": feature.get("steps", []),
    }
    fmt = ExportFormat.PYTHON if args.python else ExportFormat.TYPESCRIPT
    text = export_scenario_playwright(scenario, fmt=fmt)

    if args.output:
        target = Path(args.output)
    else:
        suffix = ".py" if fmt == ExportFormat.PYTHON else ".spec.ts"
        target = source.with_suffix(suffix)

    target.write_text(text, encoding="utf-8")
    print(f"Экспорт: {target}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="scenaria", description="Scenaria CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    run_parser = sub.add_parser("run", help="Запустить .feature сценарии headless")
    run_parser.add_argument("paths", nargs="+", help="Файл .feature или папка проекта")
    run_parser.add_argument(
        "--headed",
        action="store_true",
        help="Показать окно браузера (по умолчанию headless)",
    )
    run_parser.add_argument("--slow-mo", type=int, default=0, dest="slow_mo", help="Задержка между действиями, мс")
    run_parser.add_argument("--junit", metavar="PATH", help="Путь к JUnit XML отчёту")
    run_parser.set_defaults(func=run_command)

    export_parser = sub.add_parser("export", help="Экспорт .feature в Playwright тест")
    export_parser.add_argument("source", help="Файл .feature")
    export_parser.add_argument("-o", "--output", metavar="PATH", help="Путь к выходному файлу")
    export_parser.add_argument("--python", action="store_true", help="Python вместо TypeScript")
    export_parser.set_defaults(func=export_command)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
