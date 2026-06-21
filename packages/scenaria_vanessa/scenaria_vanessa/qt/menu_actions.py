"""Attach Vanessa items to the core Plugins menu."""

from __future__ import annotations


def contribute_vanessa_menus(host) -> None:
    host.add_menu_action("Настройки Vanessa…", lambda: _open_settings(host))
    host.add_menu_action("Прогон Vanessa…", lambda: _open_run_dialog(host))


def _ensure_installed(host, plugin_id: str = "vanessa") -> bool:
    ensure = getattr(host, "ensure_plugin_installed", None)
    if callable(ensure):
        return bool(ensure(plugin_id))
    return True


def _open_settings(host) -> None:
    if not _ensure_installed(host, "vanessa"):
        return
    from scenaria_vanessa.qt.vanessa_settings_dialog import VanessaSettingsDialog

    parent = host.parent_widget()
    dialog = VanessaSettingsDialog(parent)
    if dialog.exec():
        refresh = getattr(host, "refresh_runner_menu", None)
        if callable(refresh):
            refresh()


def _open_run_dialog(host) -> None:
    if not _ensure_installed(host, "vanessa"):
        return
    from scenaria_vanessa.qt.run_dialog import VanessaRunDialog

    parent = host.parent_widget()
    project_root = host.project_root()
    selected = host.selected_feature_paths()
    dialog = VanessaRunDialog(parent, project_root=project_root, selected_paths=selected)
    if not dialog.exec():
        return
    options = dialog.options()
    paths = options.paths or ([project_root] if project_root is not None else [])
    if not paths:
        return
    label = "Прогон Vanessa"
    if options.tags:
        label += f" @{','.join(options.tags)}"
    host.start_runner_batch(
        "vanessa",
        paths,
        label=label,
        tags=options.tags,
        exclude_tags=options.exclude_tags,
        runner_options={
            "report_junit": options.report_junit,
            "report_allure": options.report_allure,
        },
    )
