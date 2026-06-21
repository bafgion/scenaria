"""Headless CLI for running `.feature` scenarios."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from app.junit_report import write_junit_report
from app.paths import configure_playwright_browsers
from app.playwright_export import ExportFormat, export_scenario_playwright
from app.feature_store import load_feature
from app.plugins.installer import (
    PluginInstallError,
    install_from_zip,
    install_plugin,
    list_installed_plugins,
    uninstall_plugin,
)
from app.plugins.models import RunMode, RunRequest
from app.plugins.registry import get_registry, reset_registry
from app.run_suite import format_suite_summary, infer_project_root
from app.scenario_io import export_scenario_feature, export_scenario_json, import_scenario_json
from app.settings import load_settings
from app.validate_runner import validate_feature_paths


def _parse_cli_variables(raw: list[str] | None) -> dict[str, str]:
    variables: dict[str, str] = {}
    for item in raw or []:
        if "=" not in item:
            print(f"Неверный формат --var (ожидается NAME=VALUE): {item}", file=sys.stderr)
            continue
        name, value = item.split("=", 1)
        name = name.strip()
        if name:
            variables[name] = value
    return variables


def run_command(args: argparse.Namespace) -> int:
    configure_playwright_browsers()
    paths = [Path(p) for p in args.paths]
    registry = get_registry()
    runner = registry.get_runner("playwright")
    if runner is None:
        print("Встроенный runner Playwright недоступен", file=sys.stderr)
        return 2
    tag = getattr(args, "tag", None)
    request = RunRequest(
        mode=RunMode.FILES,
        paths=paths,
        project_root=infer_project_root(paths),
        headless=not args.headed,
        slow_mo_ms=args.slow_mo,
        browser_engine=getattr(args, "browser", None) or load_settings().get("browser_engine"),
        variables=_parse_cli_variables(getattr(args, "var", None)),
        tags=[tag] if tag else [],
    )
    result = runner.run(request, on_log=print)
    cases = result.to_legacy_cases()
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


def validate_command(args: argparse.Namespace) -> int:
    configure_playwright_browsers()
    paths = [Path(p) for p in args.paths]
    cases = validate_feature_paths(
        paths,
        headless=not args.headed,
        on_log=print,
        browser_engine=getattr(args, "browser", None),
    )
    if not cases:
        print("Не найдено .feature файлов", file=sys.stderr)
        return 2

    failed = sum(1 for case in cases if not case.get("success"))
    for case in cases:
        path = case.get("path")
        label = path.name if hasattr(path, "name") else str(case.get("name", "?"))
        if case.get("success"):
            print(f"OK  {label}")
        else:
            print(f"FAIL {label}", file=sys.stderr)
            for issue in case.get("issues", []):
                print(f"  • {issue}", file=sys.stderr)

    if args.json:
        payload: dict[str, Any] = {
            "success": failed == 0,
            "cases": [
                {
                    **case,
                    "path": str(case.get("path", "")),
                }
                for case in cases
            ],
        }
        target = Path(args.json)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"JSON: {target}")

    print(f"\nИтого: {len(cases) - failed} OK, {failed} FAIL из {len(cases)}")
    return 1 if failed else 0


def export_json_command(args: argparse.Namespace) -> int:
    source = Path(args.source).resolve()
    if not source.is_file():
        print(f"Файл не найден: {source}", file=sys.stderr)
        return 2
    try:
        feature = load_feature(source)
    except Exception as exc:  # noqa: BLE001
        print(f"Ошибка чтения: {exc}", file=sys.stderr)
        return 2
    scenario = {
        "name": feature.get("name", source.stem),
        "startUrl": feature.get("startUrl", ""),
        "steps": feature.get("steps", []),
    }
    target = Path(args.output).resolve() if args.output else source.with_suffix(".json")
    export_scenario_json(target, scenario)
    print(f"Экспорт JSON: {target}")
    return 0


def import_json_command(args: argparse.Namespace) -> int:
    source = Path(args.source).resolve()
    if not source.is_file():
        print(f"Файл не найден: {source}", file=sys.stderr)
        return 2
    try:
        scenario = import_scenario_json(source)
    except Exception as exc:  # noqa: BLE001
        print(f"Ошибка импорта: {exc}", file=sys.stderr)
        return 2
    target = Path(args.output).resolve() if args.output else source.with_suffix(".feature")
    export_scenario_feature(target, scenario)
    print(f"Импорт JSON → {target}")
    return 0


def plugins_list_command(_args: argparse.Namespace) -> int:
    registry = get_registry()
    installed = {item["id"]: item for item in list_installed_plugins()}
    print("Доступные runner'ы:")
    for info in registry.runner_infos():
        state = "OK" if info.available else "—"
        suffix = f" ({info.reason})" if info.reason and not info.available else ""
        version = ""
        if info.id in installed:
            version = f" v{installed[info.id].get('version', '')}".rstrip()
        print(f"  [{state}] {info.id}: {info.label}{version}{suffix}")
    errors = registry.load_errors()
    if errors:
        print("\nОшибки загрузки:")
        for plugin_id, message in errors.items():
            print(f"  {plugin_id}: {message}", file=sys.stderr)
    return 0


def plugins_install_command(args: argparse.Namespace) -> int:
    plugin_id = getattr(args, "plugin_id", None)
    zip_path = Path(args.path) if getattr(args, "path", None) else None
    url = getattr(args, "url", None)
    if zip_path is not None and not plugin_id:
        try:
            target = install_from_zip(zip_path)
        except PluginInstallError as exc:
            print(str(exc), file=sys.stderr)
            return 2
        print(f"Установлено: {target}")
        return 0
    if not plugin_id:
        print("Укажите id плагина или --path к zip", file=sys.stderr)
        return 2
    try:
        target = install_plugin(plugin_id, zip_path=zip_path, url=url)
    except PluginInstallError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(f"Установлено: {target}")
    return 0


def plugins_uninstall_command(args: argparse.Namespace) -> int:
    if not uninstall_plugin(args.plugin_id):
        print(f"Плагин «{args.plugin_id}» не установлен", file=sys.stderr)
        return 2
    reset_registry()
    get_registry().reload()
    print(f"Удалено: {args.plugin_id}")
    return 0


def va_missing_command(_args: argparse.Namespace) -> int:
    print(
        "Vanessa add-on не установлен.\n"
        "  scenaria plugins install vanessa\n"
        "  scenaria plugins install --path scenaria-vanessa.zip",
        file=sys.stderr,
    )
    return 2


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
    run_parser.add_argument(
        "--tag",
        metavar="TAG",
        help="Запуск только сценариев с указанным @тегом",
    )
    run_parser.add_argument(
        "--browser",
        choices=["chromium", "firefox", "webkit"],
        default=None,
        help="Движок Playwright (по умолчанию из settings.json)",
    )
    run_parser.add_argument(
        "--var",
        action="append",
        default=[],
        metavar="NAME=VALUE",
        help="Переменная сценария для подстановки {{NAME}}",
    )
    run_parser.set_defaults(func=run_command)

    export_parser = sub.add_parser("export", help="Экспорт .feature в Playwright тест")
    export_parser.add_argument("source", help="Файл .feature")
    export_parser.add_argument("-o", "--output", metavar="PATH", help="Путь к выходному файлу")
    export_parser.add_argument("--python", action="store_true", help="Python вместо TypeScript")
    export_parser.set_defaults(func=export_command)

    validate_parser = sub.add_parser("validate", help="Проверить селекторы в .feature без прогона шагов")
    validate_parser.add_argument("paths", nargs="+", help="Файл .feature или папка проекта")
    validate_parser.add_argument(
        "--headed",
        action="store_true",
        help="Показать окно браузера (по умолчанию headless)",
    )
    validate_parser.add_argument("--json", metavar="PATH", help="Сохранить отчёт в JSON")
    validate_parser.add_argument(
        "--browser",
        choices=["chromium", "firefox", "webkit"],
        default=None,
        help="Движок Playwright (по умолчанию из settings.json)",
    )
    validate_parser.set_defaults(func=validate_command)

    export_json_parser = sub.add_parser("export-json", help="Экспорт .feature в JSON")
    export_json_parser.add_argument("source", help="Файл .feature")
    export_json_parser.add_argument("-o", "--output", metavar="PATH", help="Путь к .json")
    export_json_parser.set_defaults(func=export_json_command)

    import_json_parser = sub.add_parser("import-json", help="Импорт JSON в .feature")
    import_json_parser.add_argument("source", help="Файл .json")
    import_json_parser.add_argument("-o", "--output", metavar="PATH", help="Путь к .feature")
    import_json_parser.set_defaults(func=import_json_command)

    plugins_parser = sub.add_parser("plugins", help="Управление add-on плагинами")
    plugins_sub = plugins_parser.add_subparsers(dest="plugins_command", required=True)

    plugins_list = plugins_sub.add_parser("list", help="Список runner'ов и установленных add-on")
    plugins_list.set_defaults(func=plugins_list_command)

    plugins_install = plugins_sub.add_parser("install", help="Установить add-on из zip или Releases")
    plugins_install.add_argument("plugin_id", nargs="?", help="Идентификатор плагина, например vanessa")
    plugins_install.add_argument("--path", metavar="ZIP", help="Локальный zip-архив add-on")
    plugins_install.add_argument("--url", metavar="URL", help="URL zip (корпоративный mirror)")
    plugins_install.set_defaults(func=plugins_install_command)

    plugins_uninstall = plugins_sub.add_parser("uninstall", help="Удалить установленный add-on")
    plugins_uninstall.add_argument("plugin_id", help="Идентификатор плагина")
    plugins_uninstall.set_defaults(func=plugins_uninstall_command)

    registry = get_registry()
    registry.contribute_cli(sub)

    if "va" not in getattr(sub, "_name_parser_map", {}):
        va_parser = sub.add_parser("va", help="Vanessa Automation (add-on)")
        va_parser.set_defaults(func=va_missing_command)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
