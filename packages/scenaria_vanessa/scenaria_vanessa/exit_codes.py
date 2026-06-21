"""Vanessa Automation process exit codes."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ExitCodeInfo:
    code: int
    label: str
    success: bool
    tone: str


EXIT_CODES: dict[int, ExitCodeInfo] = {
    0: ExitCodeInfo(0, "Нет ошибок выполнения", True, "success"),
    1: ExitCodeInfo(1, "Есть упавшие тесты", False, "error"),
    2: ExitCodeInfo(2, "Ошибка контекста / клиента тестирования", False, "error"),
    3: ExitCodeInfo(3, "Нет сценариев для выполнения", False, "warning"),
    4: ExitCodeInfo(4, "Тихая установка VanessaExt не удалась", False, "error"),
}


def describe_exit_code(code: int) -> ExitCodeInfo:
    return EXIT_CODES.get(code, ExitCodeInfo(code, f"Неизвестный код {code}", False, "error"))


def is_run_success(code: int, *, treat_empty_as_success: bool = False) -> bool:
    if code == 0:
        return True
    if code == 1:
        return False
    if code == 3 and treat_empty_as_success:
        return True
    return False
