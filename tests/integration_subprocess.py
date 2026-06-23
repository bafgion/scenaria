"""Run Playwright integration tests outside the main pytest process.

On Windows, Chromium (Playwright) and Qt in one process can trigger access
violations. When the suite mixes integration and Qt tests, conftest runs
integration here first, then unit/Qt in the parent process.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_ENV_FLAG = "SCENARIA_INTEGRATION_SUBPROCESS"


def integration_subprocess_active() -> bool:
    return os.environ.get(_ENV_FLAG) == "1"


def run_integration_tests() -> int:
    """Run all integration-marked tests in a fresh Python process."""
    env = os.environ.copy()
    env[_ENV_FLAG] = "1"
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "tests/",
        "-q",
        "-m",
        "integration",
        "--integration-in-process",
    ]
    result = subprocess.run(cmd, cwd=ROOT, env=env)
    return int(result.returncode)
