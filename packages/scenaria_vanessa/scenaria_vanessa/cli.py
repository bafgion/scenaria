"""CLI commands registered by the Vanessa add-on."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from app.plugins.models import RunMode, RunRequest
from app.run_suite import infer_project_root

from scenaria_vanessa.settings import load_vanessa_settings, save_vanessa_settings
from scenaria_vanessa.vanessa_runner import VanessaRunner


def register_va_cli(subparsers: argparse._SubParsersAction) -> None:
    va_parser = subparsers.add_parser("va", help="Vanessa Automation (add-on)")
    va_sub = va_parser.add_subparsers(dest="va_command", required=True)

    run_parser = va_sub.add_parser("run", help="Запустить .feature через Vanessa")
    run_parser.add_argument("--project", metavar="PATH", help="Корень проекта Scenaria")
    run_parser.add_argument("--files", nargs="+", metavar="FEATURE", help="Файлы .feature")
    run_parser.add_argument("--dir", metavar="PATH", help="Каталог с .feature")
    run_parser.add_argument("--tag", metavar="TAG", help="Тег include")
    run_parser.add_argument("--exclude-tag", action="append", default=[], dest="exclude_tags")
    run_parser.add_argument("--base", metavar="PATH", help="Путь к va-params.base.json")
    run_parser.add_argument("--platform-exe", dest="platform_executable", metavar="PATH")
    run_parser.add_argument("--epf", dest="epf_path", metavar="PATH")
    run_parser.add_argument("--ib", dest="ib_connection_string", metavar="STRING")
    run_parser.add_argument("--allure", action="store_true", help="Включить Allure в overlay")
    run_parser.add_argument("--dry-run", action="store_true", help="Только argv + VAParams")
    run_parser.set_defaults(func=va_run_command)


def _apply_cli_overrides(args: argparse.Namespace) -> dict:
    settings = load_vanessa_settings()
    changed = False
    for key in ("platform_executable", "epf_path", "ib_connection_string"):
        value = getattr(args, key, None)
        if value:
            settings[key] = value
            changed = True
    if getattr(args, "base", None):
        settings["project_base_params"] = str(args.base)
        changed = True
    if getattr(args, "allure", False):
        settings["report_allure"] = True
        changed = True
    if changed:
        save_vanessa_settings(settings)
    return settings


def va_run_command(args: argparse.Namespace) -> int:
    settings = _apply_cli_overrides(args)
    dry_run = bool(args.dry_run)
    if dry_run:
        settings = dict(settings)
        settings["dry_run_only"] = True
        save_vanessa_settings(settings)
    else:
        settings = load_vanessa_settings()

    runner = VanessaRunner()
    available, reason = runner.is_available()
    if not available and not dry_run:
        print(reason, file=sys.stderr)
        return 2

    paths: list[Path] = []
    if args.files:
        paths.extend(Path(item) for item in args.files)
    if args.dir:
        paths.append(Path(args.dir))
    if args.project and not paths:
        paths.append(Path(args.project))
    if not paths:
        print("Укажите --project, --files или --dir", file=sys.stderr)
        return 2

    project_root = Path(args.project).resolve() if args.project else infer_project_root(paths)
    request = RunRequest(
        mode=RunMode.FILES,
        paths=paths,
        project_root=project_root,
        tags=[args.tag] if args.tag else [],
        exclude_tags=list(args.exclude_tags or []),
        runner_options={
            "report_junit": True,
            "report_allure": bool(args.allure or settings.get("report_allure", False)),
        },
    )
    try:
        result = runner.run(request, on_log=print)
    finally:
        if dry_run:
            latest = load_vanessa_settings()
            latest["dry_run_only"] = False
            save_vanessa_settings(latest)

    if dry_run:
        print(f"\nКаталог прогона: {result.run_dir}")
        if result.run_dir:
            params = result.run_dir / "VAParams.json"
            if params.is_file():
                print(f"VAParams: {params}")
        return 0
    print(f"\nИтого: {sum(1 for c in result.cases if c.success)} OK, "
          f"{sum(1 for c in result.cases if not c.success)} FAIL")
    if result.run_dir:
        print(f"Каталог прогона: {result.run_dir}")
    return 0 if result.success else 1
