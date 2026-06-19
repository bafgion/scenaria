"""Check GitHub Releases for application updates."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any

from app.brand import BRAND_NAME, PORTABLE_ZIP, UPDATE_ZIP
from app.release_info import github_repo
from app.version import app_version, is_newer_version


@dataclass(frozen=True)
class UpdateAsset:
    name: str
    url: str
    size: int
    sha256: str | None = None
    alternate_urls: tuple[str, ...] = ()

    @property
    def all_urls(self) -> tuple[str, ...]:
        urls: list[str] = []
        seen: set[str] = set()
        for candidate in (self.url, *self.alternate_urls):
            if candidate and candidate not in seen:
                urls.append(candidate)
                seen.add(candidate)
        return tuple(urls)


@dataclass(frozen=True)
class UpdateInfo:
    version: str
    title: str
    notes: str
    published_at: str
    portable: UpdateAsset | None
    update: UpdateAsset | None

    @property
    def is_newer(self) -> bool:
        return is_newer_version(self.version)


class UpdateCheckError(RuntimeError):
    pass


def _api_url(path: str) -> str:
    return f"https://api.github.com/repos/{github_repo()}{path}"


def _request_json(url: str, timeout: float = 20.0) -> Any:
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": f"{BRAND_NAME}/{app_version()}",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise UpdateCheckError(f"GitHub API HTTP {exc.code}") from exc
    except urllib.error.URLError as exc:
        raise UpdateCheckError(f"Не удалось проверить обновления: {exc.reason}") from exc
    except OSError as exc:
        raise UpdateCheckError(f"Не удалось проверить обновления: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise UpdateCheckError("Некорректный ответ GitHub API") from exc


def _normalize_tag(tag: str) -> str:
    return tag.strip().lstrip("v")


def _direct_release_url(tag: str, name: str) -> str:
    return f"https://github.com/{github_repo()}/releases/download/{tag}/{name}"


def _asset_urls_for_release(release: dict[str, Any], name: str) -> tuple[str, ...]:
    urls: list[str] = []
    seen: set[str] = set()
    for entry in release.get("assets", []):
        if entry.get("name") != name:
            continue
        url = str(entry.get("browser_download_url", ""))
        if url and url not in seen:
            urls.append(url)
            seen.add(url)
    tag = str(release.get("tag_name", "")).strip()
    if tag:
        direct = _direct_release_url(tag, name)
        if direct not in seen:
            urls.append(direct)
    return tuple(urls)


def _asset_from_release(entry: dict[str, Any], release: dict[str, Any]) -> UpdateAsset | None:
    name = str(entry.get("name", ""))
    if not name:
        return None
    urls = _asset_urls_for_release(release, name)
    if not urls:
        return None
    return UpdateAsset(
        name=name,
        url=urls[0],
        size=int(entry.get("size", 0) or 0),
        alternate_urls=urls[1:],
    )


def _manifest_assets(release: dict[str, Any]) -> tuple[UpdateAsset | None, UpdateAsset | None]:
    for entry in release.get("assets", []):
        if entry.get("name") != "latest.json":
            continue
        url = str(entry.get("browser_download_url", ""))
        if not url:
            break
        try:
            manifest = _request_json(url)
        except UpdateCheckError:
            break
        assets = manifest.get("assets", {})
        portable = assets.get("portable", {})
        update = assets.get("update", {})
        portable_asset = None
        update_asset = None
        if portable.get("name"):
            portable_name = str(portable["name"])
            portable_urls = _asset_urls_for_release(release, portable_name)
            portable_asset = UpdateAsset(
                name=portable_name,
                url=portable_urls[0] if portable_urls else "",
                size=int(portable.get("size", 0) or 0),
                sha256=str(portable.get("sha256", "")) or None,
                alternate_urls=portable_urls[1:],
            )
        if update.get("name"):
            update_name = str(update["name"])
            update_urls = _asset_urls_for_release(release, update_name)
            update_asset = UpdateAsset(
                name=update_name,
                url=update_urls[0] if update_urls else "",
                size=int(update.get("size", 0) or 0),
                sha256=str(update.get("sha256", "")) or None,
                alternate_urls=update_urls[1:],
            )
        return portable_asset, update_asset
    return None, None


def _pick_assets(release: dict[str, Any]) -> tuple[UpdateAsset | None, UpdateAsset | None]:
    portable, update = _manifest_assets(release)
    if portable or update:
        return portable, update

    portable_asset = None
    update_asset = None
    for entry in release.get("assets", []):
        asset = _asset_from_release(entry, release)
        if asset is None:
            continue
        if asset.name == PORTABLE_ZIP:
            portable_asset = asset
        elif asset.name == UPDATE_ZIP:
            update_asset = asset
    return portable_asset, update_asset


def check_for_updates() -> UpdateInfo | None:
    release = _request_json(_api_url("/releases/latest"))
    version = _normalize_tag(str(release.get("tag_name", "")))
    if not version:
        raise UpdateCheckError("У релиза нет tag_name")

    portable, update = _pick_assets(release)
    info = UpdateInfo(
        version=version,
        title=str(release.get("name", "") or f"v{version}"),
        notes=str(release.get("body", "") or "").strip(),
        published_at=str(release.get("published_at", "")),
        portable=portable,
        update=update,
    )
    if not info.is_newer:
        return None
    if portable is None and update is None:
        raise UpdateCheckError("В релизе нет ZIP-артефактов обновления")
    return info
