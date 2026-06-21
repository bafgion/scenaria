"""CLI run command tests."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from app.cli import build_parser, run_command
from app.run_suite import infer_project_root, resolve_feature_files


def test_build_parser_has_run_tag_and_junit() -> None:
    parser = build_parser()
    args = parser.parse_args(["run", "./project", "--tag", "smoke", "--junit", "out.xml"])
    assert args.command == "run"
    assert args.paths == ["./project"]
    assert args.tag == "smoke"
    assert args.junit == "out.xml"


def test_resolve_feature_files_filters_by_tag(tmp_path: Path) -> None:
    (tmp_path / "a.feature").write_text(
        "Функционал: UI\n@smoke\nСценарий: A\n\tДопустим открыт \"https://a.com\"\n",
        encoding="utf-8",
    )
    (tmp_path / "b.feature").write_text(
        "Функционал: UI\nСценарий: B\n\tДопустим открыт \"https://b.com\"\n",
        encoding="utf-8",
    )
    files = resolve_feature_files([tmp_path], tag="smoke")
    assert len(files) == 1
    assert files[0].stem == "a"


def test_infer_project_root_from_directory(tmp_path: Path) -> None:
    assert infer_project_root([tmp_path]) == tmp_path.resolve()


def test_run_command_passes_tag_and_project_root(tmp_path: Path) -> None:
    feature = tmp_path / "demo.feature"
    feature.write_text(
        'Функционал: UI\n@smoke\nСценарий: Demo\n\tДопустим открыт "https://example.com"\n',
        encoding="utf-8",
    )
    mock_case = {
        "path": feature,
        "name": "demo",
        "success": True,
        "message": "ok",
        "executed": 1,
        "total": 1,
    }

    class FakeBatch:
        def to_legacy_cases(self):
            return [mock_case]

    class FakeRunner:
        def run(self, request, *, on_log=None):
            self.request = request
            return FakeBatch()

    fake_runner = FakeRunner()
    with patch("app.cli.get_registry") as get_registry:
        get_registry.return_value.get_runner.return_value = fake_runner
        code = run_command(
            build_parser().parse_args(["run", str(tmp_path), "--tag", "smoke"])
        )

    assert code == 0
    assert fake_runner.request.tag == "smoke"
    assert fake_runner.request.project_root == tmp_path.resolve()
