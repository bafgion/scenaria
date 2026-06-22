from __future__ import annotations

from app.update.progress import UpdatePhase, weighted_percent


def test_weighted_percent_download_halfway() -> None:
    assert weighted_percent(UpdatePhase.DOWNLOAD, 50, 100) == 35


def test_weighted_percent_extract_advances_past_download() -> None:
    download_end = weighted_percent(UpdatePhase.DOWNLOAD, 100, 100)
    extract_mid = weighted_percent(UpdatePhase.EXTRACT, 1, 2)
    assert extract_mid > download_end


def test_weighted_percent_launch_near_complete() -> None:
    assert weighted_percent(UpdatePhase.LAUNCH, 1, 1) == 99
