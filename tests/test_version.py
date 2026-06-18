from app.version import _normalize_version, _read_bundled_version, _read_pyproject_version, app_version, is_newer_version, version_tuple


def test_app_version_matches_pyproject():
    assert app_version() == _read_pyproject_version()


def test_normalize_version_strips_utf8_bom():
    assert _normalize_version("\ufeff0.2.2") == "0.2.2"


def test_read_bundled_version_strips_bom(tmp_path, monkeypatch):
    exe_dir = tmp_path / "Scenaria"
    exe_dir.mkdir()
    (exe_dir / "Scenaria.exe").write_text("", encoding="utf-8")
    (exe_dir / "version.txt").write_bytes(b"\xef\xbb\xbf0.2.2")
    monkeypatch.setattr("sys.frozen", True, raising=False)
    monkeypatch.setattr("sys.executable", str(exe_dir / "Scenaria.exe"), raising=False)
    assert _read_bundled_version() == "0.2.2"


def test_version_tuple():
    assert version_tuple("0.2.10") == (0, 2, 10)
    assert version_tuple("v1.0.0") == (1, 0, 0)


def test_is_newer_version():
    assert is_newer_version("0.3.0", "0.2.0")
    assert not is_newer_version("0.2.0", "0.2.0")
    assert not is_newer_version("0.1.9", "0.2.0")
