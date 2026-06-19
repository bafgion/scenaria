"""HTTP Basic Auth helpers for Playwright browser contexts."""

from __future__ import annotations

from typing import Any
from urllib.parse import unquote, urlunparse, urlparse


def host_from_url(url: str) -> str:
    if not url:
        return ""
    parsed = urlparse(url if "://" in url else f"https://{url}")
    return (parsed.hostname or "").lower()


def parse_url_credentials(url: str) -> tuple[str, str, str] | None:
    """Return (username, password, url_without_credentials) when embedded in URL."""
    if not url or "://" not in url:
        return None
    parsed = urlparse(url)
    if not parsed.username:
        return None
    username = unquote(parsed.username)
    password = unquote(parsed.password or "")
    clean = urlunparse(
        (
            parsed.scheme,
            parsed.netloc.split("@", 1)[-1],
            parsed.path,
            parsed.params,
            parsed.query,
            parsed.fragment,
        )
    )
    return username, password, clean


def strip_url_credentials(url: str) -> str:
    parsed = parse_url_credentials(url)
    if parsed is None:
        return url
    return parsed[2]


def resolve_http_credentials(url: str, settings: dict[str, Any] | None = None) -> dict[str, str] | None:
    """Credentials for Playwright ``http_credentials`` from URL or saved settings."""
    if url:
        embedded = parse_url_credentials(url)
        if embedded is not None:
            username, password, _ = embedded
            if username:
                return {"username": username, "password": password}

    host = host_from_url(url)
    if not host or not settings:
        return None

    entry = (settings.get("http_auth") or {}).get(host)
    if not isinstance(entry, dict):
        return None
    username = str(entry.get("username") or "").strip()
    if not username:
        return None
    return {"username": username, "password": str(entry.get("password") or "")}


def auth_key(credentials: dict[str, str] | None) -> tuple[str, str] | None:
    if not credentials:
        return None
    username = credentials.get("username", "")
    if not username:
        return None
    return username, credentials.get("password", "")


def store_host_credentials(host: str, username: str, password: str, settings: dict[str, Any]) -> dict[str, Any]:
    host = host.strip().lower()
    http_auth = dict(settings.get("http_auth") or {})
    if host and username.strip():
        http_auth[host] = {"username": username.strip(), "password": password}
    elif host in http_auth:
        del http_auth[host]
    settings["http_auth"] = http_auth
    return settings


def credentials_for_host(host: str, settings: dict[str, Any]) -> tuple[str, str]:
    host = host.strip().lower()
    entry = (settings.get("http_auth") or {}).get(host) or {}
    if not isinstance(entry, dict):
        return "", ""
    return str(entry.get("username") or ""), str(entry.get("password") or "")


def list_http_auth_hosts(settings: dict[str, Any]) -> list[str]:
    http_auth = settings.get("http_auth") or {}
    if not isinstance(http_auth, dict):
        return []
    return sorted(
        host
        for host, entry in http_auth.items()
        if isinstance(entry, dict) and str(entry.get("username") or "").strip()
    )


def remove_host_credentials(host: str, settings: dict[str, Any]) -> dict[str, Any]:
    host = host.strip().lower()
    http_auth = dict(settings.get("http_auth") or {})
    http_auth.pop(host, None)
    settings["http_auth"] = http_auth
    return settings


def origin_for_url(url: str) -> str:
    if not url:
        return ""
    parsed = urlparse(url if "://" in url else f"https://{url}")
    host = parsed.hostname or ""
    if not host:
        return ""
    scheme = parsed.scheme or "https"
    port = parsed.port
    if port and not ((scheme == "https" and port == 443) or (scheme == "http" and port == 80)):
        return f"{scheme}://{host}:{port}"
    return f"{scheme}://{host}"


def playwright_http_credentials(url: str, settings: dict[str, Any] | None = None) -> dict[str, str] | None:
    """Credentials dict for Playwright, scoped to the target site origin."""
    credentials = resolve_http_credentials(url, settings)
    if not credentials:
        return None
    origin = origin_for_url(url) or origin_for_url(f"https://{host_from_url(url)}")
    if origin:
        return {**credentials, "origin": origin}
    return credentials


def apply_url_credentials_to_settings(url: str, settings: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    """If URL contains user:pass@host, persist for host and return clean URL."""
    parsed = parse_url_credentials(url)
    if parsed is None:
        return url, settings
    username, password, clean = parsed
    host = host_from_url(clean)
    if host and username:
        settings = store_host_credentials(host, username, password, settings)
    return clean, settings
