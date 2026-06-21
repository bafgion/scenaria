"""Protocols for runner plugins and Qt menu contributions."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import TYPE_CHECKING, Callable, Protocol, runtime_checkable

if TYPE_CHECKING:
    from app.plugins.models import RunBatchResult, RunRequest, RunResult
    from app.progress_state import ProgressState


LogCallback = Callable[[str], None]
ProgressCallback = Callable[["ProgressState"], None]
StopCallback = Callable[[], bool]


@runtime_checkable
class RunnerPlugin(Protocol):
    id: str
    label: str

    def is_available(self) -> tuple[bool, str]: ...

    def run(
        self,
        request: RunRequest,
        *,
        on_log: LogCallback | None = None,
        on_progress: ProgressCallback | None = None,
        should_stop: StopCallback | None = None,
    ) -> RunBatchResult: ...

    def parse_results(self, run_dir: Path) -> RunResult: ...


class MenuHost(Protocol):
    def add_run_action(self, label: str, runner_id: str, callback: Callable[[], None]) -> None: ...

    def add_install_action(self, label: str, plugin_id: str, callback: Callable[[], None]) -> None: ...

    def add_menu_action(self, label: str, callback: Callable[[], None]) -> None: ...

    def parent_widget(self) -> object: ...

    def project_root(self) -> Path | None: ...

    def selected_feature_paths(self) -> list[Path]: ...

    def prepare_batch_run(self) -> bool: ...

    def start_runner_batch(
        self,
        runner_id: str,
        paths: list[Path],
        *,
        label: str,
        tags: list[str] | None = None,
        exclude_tags: list[str] | None = None,
    ) -> None: ...

    def ensure_plugin_installed(self, plugin_id: str) -> bool: ...

    def refresh_runner_menu(self) -> None: ...


class CliContributor(Protocol):
    def contribute_cli(self, subparsers: argparse._SubParsersAction) -> None: ...
