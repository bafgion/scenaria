"""Command palette helpers for MainWindow (T2-2 supplement)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.settings import load_settings, save_settings

if TYPE_CHECKING:
    from app.qt.main_window import MainWindow


class MainWindowPaletteMixin:
    def _collect_palette_commands(self: MainWindow):
        from app.qt.widgets.command_palette import PaletteCommand, normalize_menu_label, shortcut_text

        commands: list[PaletteCommand] = []
        seen: set[str] = set()

        def walk_menu(menu, prefix: str = "") -> None:
            for action in menu.actions():
                if action.isSeparator():
                    continue
                sub = action.menu()
                if sub is not None:
                    part = normalize_menu_label(action.text())
                    next_prefix = f"{prefix}{part} → " if part else prefix
                    walk_menu(sub, next_prefix)
                    continue
                label = normalize_menu_label(action.text())
                if not label:
                    continue
                full_label = f"{prefix}{label}" if prefix else label
                if full_label in seen:
                    continue
                seen.add(full_label)
                commands.append(
                    PaletteCommand(
                        id=full_label.lower(),
                        label=full_label,
                        shortcut=shortcut_text(action),
                        run=action.trigger,
                    )
                )

        for top in self.menuBar().actions():
            menu = top.menu()
            if menu is not None:
                walk_menu(menu)
        return sorted(commands, key=lambda item: item.label.lower())

    def _open_command_palette(self: MainWindow) -> None:
        from app.qt.widgets.command_palette import open_command_palette

        commands = self._collect_palette_commands()
        settings = load_settings()
        recent = list(settings.get("palette_recent_commands") or [])
        selected = open_command_palette(self, commands, recent_ids=recent)
        if selected is None:
            return
        recent = [selected.id] + [item for item in recent if item != selected.id]
        settings["palette_recent_commands"] = recent[:5]
        save_settings(settings)
        selected.run()
