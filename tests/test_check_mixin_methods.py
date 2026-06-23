"""Guard script for mixin method signatures."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "check_mixin_methods.py"


def test_check_mixin_methods_script_passes() -> None:
    result = subprocess.run(
        [sys.executable, str(SCRIPT)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr or result.stdout


def test_scan_flags_method_without_self() -> None:
    from scripts.check_mixin_methods import _scan_file

    source = """
class BrokenMixin:
    def broken(message: str) -> None:
        pass
"""
    path = ROOT / "_tmp_broken_mixin.py"
    path.write_text(source, encoding="utf-8")
    try:
        issues = _scan_file(path)
    finally:
        path.unlink(missing_ok=True)
    assert any("broken" in issue for issue in issues)
