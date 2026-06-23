"""Autocomplete snippets cover parser step phrases."""

from __future__ import annotations

from app.gherkin_snippets import STEP_SNIPPETS, completions_for_line


def test_completions_include_tab_steps() -> None:
    _, _, matches = completions_for_line("\tИ переключаюсь", len("\tИ переключаюсь"))
    labels = {snippet.label for snippet in matches}
    assert "переключаюсь на вкладку" in labels
    assert "переключаюсь на вкладку с url" in labels
    assert "переключаюсь на вкладку 2" in labels
    assert "переключаюсь на первую вкладку" in labels

    _, _, close_matches = completions_for_line("\tИ закрываю", len("\tИ закрываю"))
    close_labels = {snippet.label for snippet in close_matches}
    assert "закрываю текущую вкладку" in close_labels


def test_step_snippets_have_action_tags() -> None:
    import re

    pattern = re.compile(r"action:\s*\w+", re.IGNORECASE)
    missing = [snippet.label for snippet in STEP_SNIPPETS if not pattern.search(snippet.description)]
    assert not missing, f"Snippets without action tag: {missing}"
