"""Generate recording controller split modules (sprint 12). Run from repo root."""
from __future__ import annotations

import ast
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE_PATH = ROOT / "app/mvc/controllers/recording_controller.py"

PLAYBACK = {
    "_resolve_play_scenarios",
    "play",
    "_run_next_queued_play",
    "_sync_player_browser_state",
    "_player_worker_active",
    "player_worker_active",
    "_start_player_play",
    "handle_escape",
    "stop_playback",
    "close_player_browser",
    "_on_play_log",
    "_on_play_step",
    "_on_play_queue_continue",
    "_on_play_done",
    "_save_html_report",
    "_on_player_browser_started",
    "_on_player_browser_closed",
}

VALIDATE = {"validate_current", "_on_validation_done"}

SESSION = {
    "sync_browser_state",
    "_sync_browser_state",
    "_editor_test_client",
    "open_browser",
    "_confirm_replace_steps",
    "quick_record",
    "close_browser",
    "focus_browser",
    "_on_browser_focused",
    "start_recording",
    "continue_recording",
    "_begin_append_recording",
    "_on_continue_prepare_done",
    "_on_append_start_error",
    "stop_recording",
    "toggle_pause",
    "undo_last_step",
    "fetch_url_from_tab",
    "save_browser_session",
    "save_test_client_sync",
    "is_picking",
    "pick_selector",
    "_start_picking",
    "cancel_pick_selector",
    "apply_recording_modes",
    "on_step_row_selected",
    "_on_browser_opened",
    "_on_browser_closed",
    "_on_recording_started",
    "_on_recording_stopped",
    "_on_pause_toggled",
    "_on_steps_undone",
    "_on_url_fetched",
    "_on_picker_done",
    "_validate_url",
}

CORE = {
    "__init__",
    "set_parent_widget",
    "attach_bridge",
    "is_batch_running",
    "batch_runner_id",
    "stop_batch",
    "stop_vanessa",
    "_emit_session",
    "_set_pending",
    "_recorder_status",
    "_bridge_ref",
    "_on_error",
    "_on_step_recorded",
    "_status_brief",
    "run_project_suite",
    "run_project_suite_with_runner",
    "run_project_tag",
    "run_features_with_runner",
    "rerun_vanessa_failed",
    "run_selected_features",
    "_start_feature_batch",
    "_on_batch_progress",
    "_on_batch_partial",
    "_on_batch_done",
}


def _load_methods() -> tuple[dict[str, str], list[str]]:
    source = SOURCE_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "RecordingController")
    methods: dict[str, str] = {}
    for node in cls.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            seg = ast.get_source_segment(source, node)
            if seg:
                lines = seg.splitlines()
                methods[node.name] = "\n".join(["    " + lines[0], *lines[1:]])
    header: list[str] = []
    for line in source.splitlines():
        header.append(line)
        if line.startswith("class RecordingController"):
            break
    return methods, header


def _rewrite_method_self(method_src: str, host: str = "RecordingController") -> str:
    lines = method_src.splitlines()
    out: list[str] = []
    for i, line in enumerate(lines):
        if i == 0 and line.strip().startswith("def "):
            name = line.strip().split("(")[0].replace("def ", "")
            if name == "__init__":
                out.append(line)
            else:
                out.append(line.replace(f"def {name}(self", f"def {name}(self: {host}"))
        else:
            out.append(line)
    return "\n".join(out)


def _mixin_file(class_name: str, doc: str, method_names: set[str], methods: dict[str, str]) -> str:
    ordered = [name for name in methods if name in method_names]
    for name in method_names:
        if name not in methods:
            raise SystemExit(f"missing method {name} in {class_name}")
    body = "\n\n".join(_rewrite_method_self(methods[name]) for name in ordered)
    return (
        f'"""{doc}"""\n\n'
        "from __future__ import annotations\n\n"
        "import threading\n"
        "import time\n"
        "from pathlib import Path\n"
        "from typing import TYPE_CHECKING, Any\n\n"
        "from PySide6.QtCore import QTimer\n\n"
        "from app.brand import BRAND_NAME\n"
        "from app.feature_store import get_root\n"
        "from app.gherkin_ru import GherkinParseError\n"
        "from app.qt.dialogs import alert, confirm\n"
        "from app.run_display import compare_run_with_recording\n"
        "from app.run_status_store import record_run\n"
        "from app.run_suite import collect_play_scenarios\n"
        "from app.scenario_utils import ScenarioNotFoundError\n"
        "from app.steps import normalize_steps\n\n"
        "if TYPE_CHECKING:\n"
        "    from app.mvc.controllers.recording_controller import RecordingController\n\n\n"
        f"class {class_name}:\n"
        f'    """{doc}"""\n\n'
        f"{body}\n"
    )


def _core_controller(methods: dict[str, str], header: list[str]) -> str:
    ordered = [name for name in methods if name in CORE]
    body = "\n\n".join(methods[name] for name in ordered)
    imports = '''"""Recording, playback, and browser session controller."""

from __future__ import annotations

import threading
import time
from pathlib import Path
from typing import Any

from PySide6.QtCore import QObject, Signal

from app.progress_state import ProgressState
from app.feature_store import get_root
from app.project_config import default_runner
from app.run_suite import collect_feature_files, format_suite_summary
from app.plugins.models import RunMode, RunRequest
from app.plugins.registry import get_registry
from app.mvc.models.catalog_model import CatalogModel
from app.mvc.models.scenario_model import ScenarioModel
from app.mvc.models.session_model import SessionModel
from app.mvc.controllers.playback_coordinator import PlaybackCoordinatorMixin
from app.mvc.controllers.recording_session import RecordingSessionMixin
from app.mvc.controllers.validate_coordinator import ValidateCoordinatorMixin
from app.player import ScenarioPlayer
from app.qt.worker_bridge import WorkerBridge
from app.recorder import ScenarioRecorder
from app.steps import apply_coalesced_step

'''
    class_def = (
        "class RecordingController(\n"
        "    QObject,\n"
        "    PlaybackCoordinatorMixin,\n"
        "    ValidateCoordinatorMixin,\n"
        "    RecordingSessionMixin,\n"
        "):\n"
    )
    signals = textwrap.indent(
        "\n".join(
            line
            for line in Path(SOURCE_PATH).read_text(encoding="utf-8").splitlines()
            if "Signal(" in line or (line.strip().endswith("= Signal") and "Signal" in line)
        ),
        "    ",
    )
    # re-read signals block from source between class line and __init__
    source = SOURCE_PATH.read_text(encoding="utf-8")
    start = source.index("    status = Signal")
    end = source.index("    def __init__")
    signals_block = source[start:end].rstrip() + "\n\n"
    return imports + class_def + signals_block + body + "\n"


def main() -> None:
    methods, _header = _load_methods()
    all_assigned = PLAYBACK | VALIDATE | SESSION | CORE
    extra = set(methods) - all_assigned
    if extra:
        raise SystemExit(f"unassigned methods: {sorted(extra)}")

    (ROOT / "app/mvc/controllers/playback_coordinator.py").write_text(
        _mixin_file("PlaybackCoordinatorMixin", "Playback flow (T3-1).", PLAYBACK, methods),
        encoding="utf-8",
    )
    (ROOT / "app/mvc/controllers/validate_coordinator.py").write_text(
        _mixin_file("ValidateCoordinatorMixin", "Selector validate flow (T3-2).", VALIDATE, methods),
        encoding="utf-8",
    )
    (ROOT / "app/mvc/controllers/recording_session.py").write_text(
        _mixin_file("RecordingSessionMixin", "Browser record/session flow (T3-3).", SESSION, methods),
        encoding="utf-8",
    )
    (ROOT / "app/mvc/controllers/recording_controller.py").write_text(
        _core_controller(methods, _header),
        encoding="utf-8",
    )
    print("split complete")


if __name__ == "__main__":
    main()
