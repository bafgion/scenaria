"""Shared Chromium launch settings for recorder and player."""

BROWSER_LAUNCH_ARGS = [
    "--disable-dev-shm-usage",
    "--no-first-run",
    "--no-default-browser-check",
    "--disable-extensions",
    "--start-maximized",
]

# Follow the real browser window size when the user resizes or maximizes.
BROWSER_CONTEXT_OPTIONS = {"viewport": None, "no_viewport": True}
