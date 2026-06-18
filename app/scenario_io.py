"""Export and import scenarios."""

from __future__ import annotations

import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.gherkin_ru import gherkin_to_steps, steps_to_gherkin
from app.feature_store import get_root


def export_scenario_feature(target: Path, scenario: dict[str, Any]) -> Path:
    name = scenario.get("name", "") or target.stem
    text = steps_to_gherkin(list(scenario.get("steps", [])), scenario_name=name)
    target.write_text(text + "\n", encoding="utf-8")
    return target


def import_scenario_feature(source: Path) -> dict[str, Any]:
    text = source.read_text(encoding="utf-8")
    steps = gherkin_to_steps(text)
    name = source.stem
    start_url = ""
    if steps and steps[0].get("action") == "goto":
        start_url = steps[0].get("url", "")
    return {"name": name, "startUrl": start_url, "steps": steps}


def import_and_save_feature(source: Path) -> dict[str, Any]:
    """
    Legacy name: used to save into SQLite.
    Now it only parses and returns scenario data; caller should save into the feature directory.
    """
    return import_scenario_feature(source)


def export_scenario_json(target: Path, scenario: dict[str, Any]) -> Path:
    payload = {
        "name": scenario.get("name", ""),
        "startUrl": scenario.get("startUrl", ""),
        "exportedAt": datetime.now(timezone.utc).isoformat(),
        "steps": scenario.get("steps", []),
    }
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return target


def import_scenario_json(source: Path) -> dict[str, Any]:
    data = json.loads(source.read_text(encoding="utf-8"))
    return {
        "name": data.get("name", source.stem),
        "startUrl": data.get("startUrl", ""),
        "steps": list(data.get("steps", [])),
    }


def export_scenario_zip(target: Path, scenario: dict[str, Any]) -> Path:
    scenario_name = str(scenario.get("name", "") or target.stem)
    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(
            f"{scenario_name}.feature",
            steps_to_gherkin(list(scenario.get("steps", [])), scenario_name=scenario_name) + "\n",
        )
    return target


def import_and_save_json(source: Path) -> dict[str, Any]:
    """
    Legacy name: used to save into SQLite.
    Now it only parses and returns scenario data; caller should save into the feature directory.
    """
    return import_scenario_json(source)
