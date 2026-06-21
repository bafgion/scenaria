"""CLI import/export JSON tests."""

from __future__ import annotations

import json
from pathlib import Path

from app.cli import build_parser, export_json_command, import_json_command


def test_build_parser_has_json_commands() -> None:
    parser = build_parser()
    export_args = parser.parse_args(["export-json", "demo.feature", "-o", "out.json"])
    assert export_args.command == "export-json"
    assert export_args.output == "out.json"
    import_args = parser.parse_args(["import-json", "demo.json"])
    assert import_args.command == "import-json"


def test_export_json_command_writes_file(tmp_path: Path) -> None:
    feature = tmp_path / "demo.feature"
    feature.write_text(
        'Функционал: UI\nСценарий: Demo\n\tДопустим открыт "https://example.com"\n',
        encoding="utf-8",
    )
    json_path = tmp_path / "demo.json"
    code = export_json_command(
        build_parser().parse_args(["export-json", str(feature), "-o", str(json_path)])
    )
    assert code == 0
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["name"]
    assert payload["steps"]


def test_import_json_command_writes_feature(tmp_path: Path) -> None:
    source = tmp_path / "demo.json"
    source.write_text(
        json.dumps(
            {
                "name": "Demo",
                "startUrl": "https://example.com",
                "steps": [{"action": "goto", "url": "https://example.com"}],
            }
        ),
        encoding="utf-8",
    )
    target = tmp_path / "demo.feature"
    code = import_json_command(
        build_parser().parse_args(["import-json", str(source), "-o", str(target)])
    )
    assert code == 0
    text = target.read_text(encoding="utf-8")
    assert "https://example.com" in text
    assert "Сценарий:" in text
