"""Backward-compatible re-exports for run variables (T8a-2)."""

from __future__ import annotations

from app.player_context import (
    GENERATOR_ALIASES,
    GENERATOR_GHERKIN_PHRASES,
    GENERATOR_PLAY_LABELS,
    RunContext,
    _checksum_digit,
    generate_address,
    generate_bank_account,
    generate_inn,
    generate_ogrnip,
    generate_phone,
    generator_gherkin_phrase,
    generator_play_log_label,
    normalize_generator_name,
)

__all__ = [
    "GENERATOR_ALIASES",
    "GENERATOR_GHERKIN_PHRASES",
    "GENERATOR_PLAY_LABELS",
    "RunContext",
    "generate_address",
    "generate_bank_account",
    "generate_inn",
    "generate_ogrnip",
    "generate_phone",
    "generator_gherkin_phrase",
    "generator_play_log_label",
    "normalize_generator_name",
    "_checksum_digit",
]
