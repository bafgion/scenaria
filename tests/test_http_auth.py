"""HTTP Basic Auth resolution for Playwright."""

from __future__ import annotations

from app.browser_config import browser_context_options
from app.http_auth import (
    apply_url_credentials_to_settings,
    credentials_for_host,
    host_from_url,
    list_http_auth_hosts,
    origin_for_url,
    parse_url_credentials,
    playwright_http_credentials,
    remove_host_credentials,
    resolve_http_credentials,
    store_host_credentials,
    strip_url_credentials,
)
from app.settings import DEFAULTS, load_settings, save_settings


def test_parse_url_credentials() -> None:
    parsed = parse_url_credentials("https://user:secret@stage.example.com/path")
    assert parsed is not None
    username, password, clean = parsed
    assert username == "user"
    assert password == "secret"
    assert clean == "https://stage.example.com/path"


def test_strip_url_credentials() -> None:
    assert strip_url_credentials("https://u:p@host.test/") == "https://host.test/"


def test_resolve_from_settings() -> None:
    settings = dict(DEFAULTS)
    settings["http_auth"] = {"stage.example.com": {"username": "qa", "password": "pw"}}
    creds = resolve_http_credentials("https://stage.example.com/", settings)
    assert creds == {"username": "qa", "password": "pw"}


def test_resolve_prefers_url_credentials() -> None:
    settings = dict(DEFAULTS)
    settings["http_auth"] = {"stage.example.com": {"username": "saved", "password": "x"}}
    creds = resolve_http_credentials("https://inline:pass@stage.example.com/", settings)
    assert creds == {"username": "inline", "password": "pass"}


def test_apply_url_credentials_to_settings() -> None:
    settings = dict(DEFAULTS)
    clean, settings = apply_url_credentials_to_settings(
        "https://qa:pw@stage.example.com/",
        settings,
    )
    assert clean == "https://stage.example.com/"
    assert settings["http_auth"]["stage.example.com"] == {"username": "qa", "password": "pw"}


def test_browser_context_options_includes_credentials() -> None:
    settings = dict(DEFAULTS)
    settings["http_auth"] = {"stage.example.com": {"username": "qa", "password": "pw"}}
    opts = browser_context_options("https://stage.example.com/", settings=settings)
    assert opts["http_credentials"] == {
        "username": "qa",
        "password": "pw",
        "origin": "https://stage.example.com",
    }


def test_list_http_auth_hosts() -> None:
    settings = dict(DEFAULTS)
    settings["http_auth"] = {
        "b.example.com": {"username": "b", "password": "1"},
        "a.example.com": {"username": "a", "password": "2"},
        "empty.example.com": {"username": "", "password": ""},
    }
    assert list_http_auth_hosts(settings) == ["a.example.com", "b.example.com"]


def test_remove_host_credentials() -> None:
    settings = dict(DEFAULTS)
    settings = store_host_credentials("one.test", "u", "p", settings)
    settings = store_host_credentials("two.test", "u2", "p2", settings)
    settings = remove_host_credentials("one.test", settings)
    assert list_http_auth_hosts(settings) == ["two.test"]


def test_origin_for_url() -> None:
    assert origin_for_url("https://stage.example.com/path") == "https://stage.example.com"
    assert origin_for_url("http://localhost:8080/x") == "http://localhost:8080"


def test_playwright_http_credentials_scoped_to_site() -> None:
    settings = dict(DEFAULTS)
    settings["http_auth"] = {
        "stage.example.com": {"username": "qa", "password": "pw"},
        "other.example.com": {"username": "other", "password": "x"},
    }
    creds = playwright_http_credentials("https://stage.example.com/", settings)
    assert creds == {
        "username": "qa",
        "password": "pw",
        "origin": "https://stage.example.com",
    }
    other = playwright_http_credentials("https://other.example.com/app", settings)
    assert other["username"] == "other"
    assert other["origin"] == "https://other.example.com"


def test_store_and_read_host_credentials() -> None:
    settings = dict(DEFAULTS)
    settings = store_host_credentials("stage.example.com", "qa", "pw", settings)
    username, password = credentials_for_host("stage.example.com", settings)
    assert username == "qa"
    assert password == "pw"


def test_host_from_url() -> None:
    assert host_from_url("https://Stage.Example.COM/x") == "stage.example.com"
