"""Weighted progress for portable update phases."""

from __future__ import annotations

from enum import Enum


class UpdatePhase(str, Enum):
    DOWNLOAD = "download"
    VERIFY = "verify"
    EXTRACT = "extract"
    STAGE = "stage"
    LAUNCH = "launch"


PHASE_WEIGHTS: dict[UpdatePhase, int] = {
    UpdatePhase.DOWNLOAD: 70,
    UpdatePhase.VERIFY: 2,
    UpdatePhase.EXTRACT: 13,
    UpdatePhase.STAGE: 13,
    UpdatePhase.LAUNCH: 2,
}

PHASE_LABELS_RU: dict[UpdatePhase, str] = {
    UpdatePhase.DOWNLOAD: "Скачивание…",
    UpdatePhase.VERIFY: "Проверка файла…",
    UpdatePhase.EXTRACT: "Распаковка…",
    UpdatePhase.STAGE: "Подготовка к установке…",
    UpdatePhase.LAUNCH: "Перезапуск…",
}


def phase_offset(phase: UpdatePhase) -> int:
    offset = 0
    for item in UpdatePhase:
        if item == phase:
            break
        offset += PHASE_WEIGHTS[item]
    return offset


def weighted_percent(phase: UpdatePhase, current: int, total: int) -> int:
    if total <= 0:
        if phase == UpdatePhase.LAUNCH:
            return 99
        return phase_offset(phase) + PHASE_WEIGHTS[phase] // 2
    fraction = min(1.0, max(0.0, current / total))
    return min(99, phase_offset(phase) + int(PHASE_WEIGHTS[phase] * fraction))


def format_bytes(size: int) -> str:
    if size < 1024:
        return f"{size} Б"
    megabytes = size / (1024 * 1024)
    if megabytes < 10:
        return f"{megabytes:.1f} МБ"
    return f"{megabytes:.0f} МБ"
