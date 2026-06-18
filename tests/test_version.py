from app.version import app_version, is_newer_version, version_tuple


def test_app_version_matches_pyproject():
    assert app_version() == "0.2.0"


def test_version_tuple():
    assert version_tuple("0.2.10") == (0, 2, 10)
    assert version_tuple("v1.0.0") == (1, 0, 0)


def test_is_newer_version():
    assert is_newer_version("0.3.0", "0.2.0")
    assert not is_newer_version("0.2.0", "0.2.0")
    assert not is_newer_version("0.1.9", "0.2.0")
