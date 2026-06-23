"""Resilient HTTP downloads for release artifacts."""

from __future__ import annotations

import errno
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from pathlib import Path

from app.brand import BRAND_NAME
from app.update.checker import UpdateCheckError
from app.version import app_version

_CHUNK_SIZE = 256 * 1024
_MAX_ATTEMPTS = 6
_RETRY_BASE_DELAY = 1.5
_READ_TIMEOUT = 45.0

_CANCELLED_MESSAGE = "Обновление отменено"

_TRANSIENT_WINERRORS = frozenset({10053, 10054, 10060, 10061, 10065})
_TRANSIENT_ERRNOS = frozenset(
    {
        errno.ECONNRESET,
        errno.ECONNABORTED,
        errno.ETIMEDOUT,
        errno.ECONNREFUSED,
        errno.EHOSTUNREACH,
        errno.ENETUNREACH,
    }
)


def _http_headers(*, offset: int = 0) -> dict[str, str]:
    headers = {
        "User-Agent": f"{BRAND_NAME}/{app_version()}",
        "Accept": "application/octet-stream",
        "Connection": "close",
    }
    if offset > 0:
        headers["Range"] = f"bytes={offset}-"
    return headers


def _is_transient_error(exc: BaseException) -> bool:
    if isinstance(exc, urllib.error.URLError):
        reason = exc.reason
        if isinstance(reason, OSError):
            return _is_transient_os_error(reason)
        return True
    if isinstance(exc, OSError):
        return _is_transient_os_error(exc)
    return False


def _is_transient_os_error(exc: OSError) -> bool:
    winerror = getattr(exc, "winerror", None)
    if winerror in _TRANSIENT_WINERRORS:
        return True
    return exc.errno in _TRANSIENT_ERRNOS


def _parse_content_range_total(header: str) -> int | None:
    if "/" not in header:
        return None
    total_part = header.rsplit("/", 1)[-1].strip()
    if total_part.isdigit():
        return int(total_part)
    return None


def _format_download_error(url: str, exc: BaseException) -> str:
    if isinstance(exc, urllib.error.HTTPError):
        return f"HTTP {exc.code} для {url}"
    if isinstance(exc, urllib.error.URLError):
        reason = exc.reason
        return f"{reason} ({url})"
    return f"{exc} ({url})"


def _raise_if_cancelled(should_cancel: Callable[[], bool] | None, destination: Path) -> None:
    if should_cancel is None or not should_cancel():
        return
    destination.unlink(missing_ok=True)
    raise UpdateCheckError(_CANCELLED_MESSAGE)


def _download_url_once(
    url: str,
    destination: Path,
    *,
    total_hint: int,
    on_progress,
    should_cancel: Callable[[], bool] | None = None,
) -> None:
    _raise_if_cancelled(should_cancel, destination)
    offset = destination.stat().st_size if destination.is_file() else 0
    request = urllib.request.Request(url, headers=_http_headers(offset=offset))

    with urllib.request.urlopen(request, timeout=_READ_TIMEOUT) as response:
        status = int(getattr(response, "status", None) or response.getcode())
        if status == 200 and offset > 0:
            offset = 0
            destination.unlink(missing_ok=True)

        content_length = int(response.headers.get("Content-Length", "0") or 0)
        total = _parse_content_range_total(str(response.headers.get("Content-Range", "")))
        if total is None:
            if status == 206 and content_length > 0:
                total = offset + content_length
            elif total_hint > 0:
                total = total_hint
            else:
                total = content_length

        mode = "ab" if offset > 0 else "wb"
        read = offset
        cancelled = False
        with destination.open(mode) as handle:
            while True:
                if should_cancel and should_cancel():
                    cancelled = True
                    break
                chunk = response.read(_CHUNK_SIZE)
                if not chunk:
                    break
                handle.write(chunk)
                read += len(chunk)
                if on_progress is not None:
                    on_progress(min(read, total) if total > 0 else read, total)
        if cancelled:
            destination.unlink(missing_ok=True)
            raise UpdateCheckError(_CANCELLED_MESSAGE)


def download_url_resilient(
    url: str,
    destination: Path,
    *,
    total_hint: int = 0,
    on_progress=None,
    should_cancel: Callable[[], bool] | None = None,
) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    last_error: BaseException | None = None

    for attempt in range(_MAX_ATTEMPTS):
        try:
            _raise_if_cancelled(should_cancel, destination)
            _download_url_once(
                url,
                destination,
                total_hint=total_hint,
                on_progress=on_progress,
                should_cancel=should_cancel,
            )
            return
        except UpdateCheckError:
            raise
        except (urllib.error.URLError, urllib.error.HTTPError, OSError) as exc:
            last_error = exc
            if attempt >= _MAX_ATTEMPTS - 1 or not _is_transient_error(exc):
                break
            time.sleep(_RETRY_BASE_DELAY * (attempt + 1))

    assert last_error is not None
    raise UpdateCheckError(_format_download_error(url, last_error)) from last_error
