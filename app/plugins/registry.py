"""Runner plugin registry."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.plugins.loader import KNOWN_OPTIONAL_PLUGINS, discover_plugins
from app.plugins.playwright_runner import PlaywrightRunner

logger = logging.getLogger(__name__)

_registry: PluginRegistry | None = None


@dataclass(frozen=True)
class RunnerInfo:
    id: str
    label: str
    available: bool
    reason: str
    installed: bool


class PluginRegistry:
    def __init__(self) -> None:
        self._runners: dict[str, Any] = {}
        self._errors: dict[str, str] = {}
        self._project_root: Path | None = None

    def set_project_root(self, root: Path | None) -> None:
        self._project_root = root.resolve() if root is not None else None

    def reload(self, *, project_root: Path | None = None) -> None:
        if project_root is not None:
            self._project_root = project_root.resolve()
        self._runners, self._errors = discover_plugins(self._project_root)
        for plugin_id, message in self._errors.items():
            logger.warning("Плагин %s отключён: %s", plugin_id, message)

    def list_runners(self) -> list[Any]:
        return list(self._runners.values())

    def get_runner(self, runner_id: str) -> Any | None:
        return self._runners.get(runner_id)

    def load_errors(self) -> dict[str, str]:
        return dict(self._errors)

    def runner_infos(self) -> list[RunnerInfo]:
        infos: list[RunnerInfo] = []
        for runner in self._runners.values():
            available, reason = runner.is_available()
            infos.append(
                RunnerInfo(
                    id=str(runner.id),
                    label=str(runner.label),
                    available=available,
                    reason=reason,
                    installed=True,
                )
            )
        for plugin_id, label in KNOWN_OPTIONAL_PLUGINS.items():
            if plugin_id in self._runners:
                continue
            reason = self._errors.get(plugin_id, "add-on не установлен")
            infos.append(
                RunnerInfo(
                    id=plugin_id,
                    label=label,
                    available=False,
                    reason=reason,
                    installed=False,
                )
            )
        return sorted(infos, key=lambda item: (item.id != PlaywrightRunner.id, item.label.lower()))

    def contribute_menus(self, host) -> None:
        for runner in self._runners.values():
            contribute = getattr(runner, "contribute_menus", None)
            if callable(contribute):
                try:
                    contribute(host)
                except Exception as exc:  # noqa: BLE001
                    logger.warning("contribute_menus(%s): %s", runner.id, exc)

    def contribute_cli(self, subparsers) -> None:
        for runner in self._runners.values():
            contribute = getattr(runner, "contribute_cli", None)
            if callable(contribute):
                try:
                    contribute(subparsers)
                except Exception as exc:  # noqa: BLE001
                    logger.warning("contribute_cli(%s): %s", runner.id, exc)


def get_registry() -> PluginRegistry:
    global _registry
    if _registry is None:
        _registry = PluginRegistry()
        _registry.reload()
    return _registry


def reset_registry() -> None:
    global _registry
    _registry = None
