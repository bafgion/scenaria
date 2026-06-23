from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.update.checker import UpdateAsset, UpdateCheckError, _asset_urls_for_release
from app.update.http_download import download_url_resilient
from app.update.installer import download_asset


def test_asset_urls_include_direct_release_link() -> None:
    release = {
        "tag_name": "v0.2.4",
        "assets": [
            {
                "name": "Scenaria-update.zip",
                "browser_download_url": "https://objects.githubusercontent.com/update.zip",
            }
        ],
    }
    urls = _asset_urls_for_release(release, "Scenaria-update.zip")
    assert urls[0] == "https://objects.githubusercontent.com/update.zip"
    assert urls[1] == "https://github.com/bafgion/scenaria/releases/download/v0.2.4/Scenaria-update.zip"


def test_download_url_resilient_retries_after_connection_reset(tmp_path: Path) -> None:
    destination = tmp_path / "pkg.zip"
    payload = b"zip-bytes"
    calls = {"count": 0}

    def fake_urlopen(request, timeout=0):
        calls["count"] += 1
        if calls["count"] == 1:
            raise OSError(10054, "Удаленный хост принудительно разорвал существующее подключение")
        response = MagicMock()
        response.__enter__ = MagicMock(return_value=response)
        response.__exit__ = MagicMock(return_value=False)
        response.status = 200
        response.getcode.return_value = 200
        response.headers = {"Content-Length": str(len(payload))}
        response.read.side_effect = [payload, b""]
        return response

    with patch("app.update.http_download.urllib.request.urlopen", side_effect=fake_urlopen):
        with patch("app.update.http_download.time.sleep"):
            download_url_resilient("https://example.com/pkg.zip", destination, total_hint=len(payload))

    assert destination.read_bytes() == payload
    assert calls["count"] == 2


def test_download_url_resilient_reports_progress_without_content_length(tmp_path: Path) -> None:
    destination = tmp_path / "pkg.zip"
    payload = b"x" * 5000
    progress: list[tuple[int, int]] = []

    def fake_urlopen(request, timeout=0):
        response = MagicMock()
        response.__enter__ = MagicMock(return_value=response)
        response.__exit__ = MagicMock(return_value=False)
        response.status = 200
        response.getcode.return_value = 200
        response.headers = {}
        response.read.side_effect = [payload, b""]
        return response

    with patch("app.update.http_download.urllib.request.urlopen", side_effect=fake_urlopen):
        download_url_resilient(
            "https://example.com/pkg.zip",
            destination,
            on_progress=lambda done, total: progress.append((done, total)),
        )

    assert destination.read_bytes() == payload
    assert progress
    assert progress[-1][0] == len(payload)
    assert progress[-1][1] == 0


def test_download_url_resilient_honours_cancel(tmp_path: Path) -> None:
    destination = tmp_path / "pkg.zip"
    state = {"reads": 0}

    def should_cancel() -> bool:
        return state["reads"] >= 1

    def fake_urlopen(request, timeout=0):
        response = MagicMock()
        response.__enter__ = MagicMock(return_value=response)
        response.__exit__ = MagicMock(return_value=False)
        response.status = 200
        response.getcode.return_value = 200
        response.headers = {"Content-Length": "1000000"}

        def read_chunk(_size: int) -> bytes:
            state["reads"] += 1
            return b"chunk"

        response.read.side_effect = read_chunk
        return response

    with patch("app.update.http_download.urllib.request.urlopen", side_effect=fake_urlopen):
        with pytest.raises(UpdateCheckError, match="отменено"):
            download_url_resilient(
                "https://example.com/pkg.zip",
                destination,
                should_cancel=should_cancel,
            )

    assert not destination.exists()


def test_download_asset_tries_alternate_url(tmp_path: Path) -> None:
    asset = UpdateAsset(
        name="Scenaria-update.zip",
        url="https://example.com/fail.zip",
        size=4,
        alternate_urls=("https://example.com/ok.zip",),
    )
    destination = tmp_path / "Scenaria-update.zip"
    payload = b"data"

    def fake_resilient(url, dest, *, total_hint=0, on_progress=None, should_cancel=None):
        if "fail" in url:
            raise UpdateCheckError("connection reset")
        dest.write_bytes(payload)

    with patch("app.update.installer.download_url_resilient", side_effect=fake_resilient):
        download_asset(asset, destination)

    assert destination.read_bytes() == payload


def test_download_asset_raises_with_manual_link_when_all_urls_fail(tmp_path: Path) -> None:
    asset = UpdateAsset(
        name="Scenaria-update.zip",
        url="https://example.com/fail.zip",
        size=0,
    )

    with patch(
        "app.update.installer.download_url_resilient",
        side_effect=UpdateCheckError("[WinError 10054] reset"),
    ):
        with pytest.raises(UpdateCheckError, match="releases/latest") as exc:
            download_asset(asset, tmp_path / "Scenaria-update.zip")

    assert "Scenaria-update.zip" in str(exc.value)
