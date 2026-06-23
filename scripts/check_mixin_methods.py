#!/usr/bin/env python3
"""AST guard: mixin instance methods must declare `self` as the first parameter."""

from __future__ import annotations

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCAN_GLOBS = (
    "app/mvc/controllers/*_coordinator.py",
    "app/mvc/controllers/recording_session.py",
    "app/qt/main_window_*.py",
)


def _is_instance_method(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    for decorator in node.decorator_list:
        name = ""
        if isinstance(decorator, ast.Name):
            name = decorator.id
        elif isinstance(decorator, ast.Attribute):
            name = decorator.attr
        if name in {"staticmethod", "classmethod"}:
            return False
    return True


def _missing_self(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    if not _is_instance_method(node):
        return False
    if not node.args.args:
        return True
    return node.args.args[0].arg != "self"


def _scan_file(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    issues: list[str] = []
    for node in tree.body:
        if not isinstance(node, ast.ClassDef):
            continue
        for child in node.body:
            if not isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            if _missing_self(child):
                rel = path.relative_to(ROOT)
                issues.append(f"{rel}:{child.lineno} {child.name}() missing `self`")
    return issues


def main() -> int:
    paths: list[Path] = []
    for pattern in SCAN_GLOBS:
        paths.extend(sorted(ROOT.glob(pattern)))
    if not paths:
        print("check_mixin_methods: no files matched", file=sys.stderr)
        return 2

    issues: list[str] = []
    for path in paths:
        issues.extend(_scan_file(path))

    if issues:
        print("Mixin methods without `self`:", file=sys.stderr)
        for issue in issues:
            print(f"  {issue}", file=sys.stderr)
        return 1
    print(f"check_mixin_methods: OK ({len(paths)} files)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
