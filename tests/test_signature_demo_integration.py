"""Integration test: signature demo HTML page + draw_signature step."""

from __future__ import annotations

from pathlib import Path

import pytest
from playwright.sync_api import sync_playwright

from app.gherkin_ru import gherkin_to_steps
from app.paths import configure_playwright_browsers
from app.player import run_scenario_on_page

pytestmark = pytest.mark.integration


FIXTURE_HTML = Path(__file__).resolve().parent / "fixtures" / "signature_demo.html"
FIXTURE_FEATURE = Path(__file__).resolve().parent / "fixtures" / "signature_demo.feature"


def _file_url(path: Path) -> str:
    return path.resolve().as_uri()


@pytest.fixture(scope="module")
def signature_demo_url() -> str:
    assert FIXTURE_HTML.is_file(), f"Missing demo page: {FIXTURE_HTML}"
    return _file_url(FIXTURE_HTML)


def test_signature_demo_feature_file_parses() -> None:
    assert FIXTURE_FEATURE.is_file(), f"Missing feature file: {FIXTURE_FEATURE}"
    text = FIXTURE_FEATURE.read_text(encoding="utf-8")
    steps = gherkin_to_steps(text)
    actions = [step["action"] for step in steps]
    assert actions == [
        "goto",
        "wait_for",
        "draw_signature",
        "click",
        "assert_visible",
        "close_browser",
    ]
    assert steps[0]["action"] == "goto"
    assert steps[0]["url"].endswith("signature_demo.html")


def test_signature_demo_page(signature_demo_url: str) -> None:
    configure_playwright_browsers()
    scenario = {
        "name": "Демо ПЭП",
        "startUrl": signature_demo_url,
        "steps": [
            {"action": "goto", "url": signature_demo_url},
            {"action": "wait_for", "selector": "canvas#signature-canvas"},
            {"action": "draw_signature", "selector": "canvas#signature-canvas"},
            {"action": "click", "selector": "button#next-btn"},
            {"action": "assert_visible", "selector": "#success.visible"},
            {"action": "close_browser"},
        ],
    }
    logs: list[str] = []
    closed = False

    def on_close() -> None:
        nonlocal closed
        closed = True
        browser.close()

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page()
        result = run_scenario_on_page(
            page,
            scenario,
            logs.append,
            highlight=False,
            on_close_browser=on_close,
        )
        assert closed
        browser.close()

    assert result["success"], result.get("message", "\n".join(logs))
