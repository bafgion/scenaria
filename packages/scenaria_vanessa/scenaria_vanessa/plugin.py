"""Vanessa Automation plugin entry point."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from scenaria_vanessa.vanessa_runner import VanessaRunner


class VanessaPlugin:
    id = "vanessa"
    label = "Vanessa Automation"

    def __init__(self) -> None:
        self._runner = VanessaRunner()

    def is_available(self) -> tuple[bool, str]:
        return self._runner.is_available()

    def run(self, request, *, on_log=None, on_progress=None, should_stop=None):
        return self._runner.run(
            request,
            on_log=on_log,
            on_progress=on_progress,
            should_stop=should_stop,
        )

    def parse_results(self, run_dir: Path):
        return self._runner.parse_results(run_dir)

    def contribute_menus(self, host) -> None:
        from scenaria_vanessa.qt.menu_actions import contribute_vanessa_menus

        contribute_vanessa_menus(host)

    def contribute_cli(self, subparsers: argparse._SubParsersAction) -> None:
        from scenaria_vanessa.cli import register_va_cli

        register_va_cli(subparsers)
