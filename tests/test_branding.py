from __future__ import annotations

import sys

import pytest
from PySide6.QtWidgets import QApplication

from app.paths import bundled_root
from app.qt.branding import about_text, app_icon, brand_mark_pixmap, branding_dir
from app.qt.theme import BRAND_TAGLINE


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_bundled_root_uses_internal_when_frozen(monkeypatch, tmp_path):
    internal = tmp_path / "_internal"
    internal.mkdir()
    exe = tmp_path / "Scenaria.exe"
    exe.write_text("", encoding="utf-8")
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(exe), raising=False)
    monkeypatch.delattr(sys, "_MEIPASS", raising=False)
    assert bundled_root() == internal


def test_branding_dir_frozen_layout(monkeypatch, tmp_path):
    internal = tmp_path / "_internal" / "assets" / "branding"
    internal.mkdir(parents=True)
    (internal / "app.ico").write_bytes(b"ico")
    exe = tmp_path / "Scenaria.exe"
    exe.write_text("", encoding="utf-8")
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(exe), raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path / "_internal"), raising=False)
    assert branding_dir() == internal


def test_branding_assets_present():
    folder = branding_dir()
    assert folder.is_dir()
    assert (folder / "icon-variant-b-monogram-su.png").is_file()
    assert (folder / "app-icon-mark.png").is_file()
    assert (folder / "app.ico").is_file()


def test_app_icon_loads(qapp):
    icon = app_icon()
    assert not icon.isNull()
    pixmap = icon.pixmap(16, 16)
    assert not pixmap.isNull()
    assert pixmap.width() == 16
    assert pixmap.height() == 16


def test_brand_mark_pixmap(qapp):
    pixmap = brand_mark_pixmap(96)
    assert not pixmap.isNull()
    assert pixmap.width() == 96
    assert pixmap.height() == 96


def test_about_text_uses_brand_constants():
    text = about_text()
    assert BRAND_TAGLINE in text
    assert "автотестов сайтов" in text
