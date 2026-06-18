from __future__ import annotations

from unittest.mock import patch

import pytest

from app.update.checker import UpdateCheckError, check_for_updates


def _release_payload():
    return {
        "tag_name": "v0.3.0",
        "name": "Scenaria v0.3.0",
        "body": "Bug fixes",
        "published_at": "2026-01-01T00:00:00Z",
        "assets": [
            {
                "name": "Scenaria-update.zip",
                "browser_download_url": "https://example.com/update.zip",
                "size": 120_000_000,
            }
        ],
    }


@patch("app.version.app_version", return_value="0.2.0")
def test_check_for_updates_requests_full_github_url(_version):
    with patch("app.update.checker._request_json") as mock_request:
        mock_request.return_value = _release_payload() | {"tag_name": "v0.2.0"}
        check_for_updates()
    mock_request.assert_called_once_with("https://api.github.com/repos/bafgion/scenaria/releases/latest")


@patch("app.version.app_version", return_value="0.2.0")
@patch("app.update.checker._request_json")
def test_check_for_updates_finds_newer(mock_request, _version):
    mock_request.return_value = _release_payload()
    info = check_for_updates()
    assert info is not None
    assert info.version == "0.3.0"
    assert info.update is not None
    assert info.update.name == "Scenaria-update.zip"


@patch("app.version.app_version", return_value="0.3.0")
@patch("app.update.checker._request_json")
def test_check_for_updates_none_when_current(mock_request, _version):
    mock_request.return_value = _release_payload()
    assert check_for_updates() is None


@patch("app.update.checker._request_json")
def test_check_for_updates_http_error(mock_request):
    mock_request.side_effect = UpdateCheckError("GitHub API HTTP 404")
    with pytest.raises(UpdateCheckError):
        check_for_updates()


@patch("app.version.app_version", return_value="0.2.0")
@patch("app.update.checker._request_json")
def test_check_for_updates_reads_manifest(mock_request, _version):
    release = _release_payload()
    release["assets"].append(
        {
            "name": "latest.json",
            "browser_download_url": "https://example.com/latest.json",
            "size": 100,
        }
    )
    manifest = {
        "version": "0.3.0",
        "assets": {
            "update": {
                "name": "Scenaria-update.zip",
                "size": 120,
                "sha256": "abc",
            }
        },
    }

    def fake_request(url, timeout=20.0):
        if url.endswith("/releases/latest"):
            return release
        if url.endswith("latest.json"):
            return manifest
        raise AssertionError(url)

    mock_request.side_effect = fake_request
    info = check_for_updates()
    assert info is not None
    assert info.update is not None
    assert info.update.sha256 == "abc"
