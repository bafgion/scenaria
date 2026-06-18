"""Scenario naming and shared errors (file-based storage)."""

from __future__ import annotations

import re
from datetime import datetime
from urllib.parse import urlparse


class ScenarioNotFoundError(FileNotFoundError):
    pass


def suggest_scenario_name(start_url: str = "") -> str:
    host = "scenario"
    if start_url:
        parsed = urlparse(start_url)
        host = (parsed.netloc or parsed.path or "scenario").replace(".", "-")
    host = re.sub(r'[<>:"/\\|?*]+', "_", host) or "scenario"
    stamp = datetime.now().strftime("%Y%m%d-%H%M")
    return f"{host}-{stamp}"
