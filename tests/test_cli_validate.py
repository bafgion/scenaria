"""CLI validate command tests."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from app.cli import build_parser, validate_command
from app.selector_validate import StepValidateResult, format_validate_report_text


def test_build_parser_has_validate_subcommand() -> None:
    parser = build_parser()
    args = parser.parse_args(["validate", "demo.feature", "--json", "out.json"])
    assert args.command == "validate"
    assert args.paths == ["demo.feature"]
    assert args.json == "out.json"


def test_format_validate_report_text_includes_issues() -> None:
    results = [
        StepValidateResult(1, "click", "button", "not_found", "элемент не найден"),
    ]
    text = format_validate_report_text(results, issues=["Шаг 1: элемент не найден → button"])
    assert "not_found" not in text
    assert "Не найден" in text
    assert "button" in text


def test_validate_command_writes_json(tmp_path: Path) -> None:
    feature = tmp_path / "demo.feature"
    feature.write_text(
        'Функционал: UI\nСценарий: Demo\n\tДопустим открыт "https://example.com"\n',
        encoding="utf-8",
    )
    json_path = tmp_path / "report.json"
    mock_case = {
        "path": feature,
        "name": "demo",
        "success": True,
        "issues": [],
        "results": [],
    }

    with patch("app.cli.validate_feature_paths", return_value=[mock_case]):
        code = validate_command(
            build_parser().parse_args(["validate", str(feature), "--json", str(json_path)])
        )

    assert code == 0
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["success"] is True
    assert payload["cases"][0]["name"] == "demo"
