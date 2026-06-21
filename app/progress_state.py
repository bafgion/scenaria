"""Unified progress reporting for long-running IDE operations."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ProgressState:
    task_id: str
    label: str
    current: int
    total: int
    cancellable: bool = False

    @property
    def active(self) -> bool:
        return self.total > 0

    @property
    def fraction(self) -> float:
        if self.total <= 0:
            return 0.0
        return max(0.0, min(1.0, self.current / self.total))

    def step_label(self) -> str:
        if self.total > 0:
            return f"{self.label} ({self.current}/{self.total})"
        return self.label
