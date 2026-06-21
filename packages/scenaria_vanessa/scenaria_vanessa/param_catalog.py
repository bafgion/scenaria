"""Catalog of commonly used Vanessa Automation JSON parameters."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

ParamType = Literal["bool", "string", "path", "string_list", "int"]


@dataclass(frozen=True)
class ParamSpec:
    ru: str
    en: str
    type: ParamType
    group: str
    description: str = ""


COMMON_PARAMS: tuple[ParamSpec, ...] = (
    ParamSpec("КаталогПроекта", "projectpath", "path", "paths", "Корень проекта VA"),
    ParamSpec("КаталогФич", "featurepath", "path", "features", "Каталог с .feature"),
    ParamSpec("СписокФичДляВыполнения", "FeaturesToRun", "string_list", "features", "Абсолютные пути к .feature"),
    ParamSpec("СписокСценариевДляВыполнения", "scenariofilter", "string_list", "features", "Имена сценариев"),
    ParamSpec("СписокТеговОтбор", "filtertags", "string_list", "tags", "Теги include (@smoke)"),
    ParamSpec("СписокТеговИсключение", "ignoretags", "string_list", "tags", "Теги exclude"),
    ParamSpec("КаталогИнструментов", "toolsPath", "path", "paths", "Каталог обработки VA"),
    ParamSpec("ДелатьОтчетВФорматеjUnit", "junitreport", "bool", "reports", "JUnit отчёт"),
    ParamSpec("КаталогВыгрузкиJUnit", "junitpath", "path", "reports", "Каталог JUnit XML"),
    ParamSpec("ДелатьОтчетВФорматеАллюр", "allurereport", "bool", "reports", "Allure отчёт"),
    ParamSpec("КаталогВыгрузкиAllure", "allurepath", "path", "reports", "Каталог Allure"),
    ParamSpec(
        "ВыгружатьСтатусВыполненияСценариевВФайл",
        "statusreport",
        "bool",
        "reports",
        "Файл статуса прогона",
    ),
    ParamSpec(
        "ПутьКФайлуДляВыгрузкиСтатусаВыполненияСценариев",
        "statuspath",
        "path",
        "reports",
        "Путь к status.log",
    ),
    ParamSpec("ДанныеКлиентовТестирования", "TestingClientData", "string", "clients", "Клиенты тестирования"),
)

RU_TO_EN = {spec.ru: spec.en for spec in COMMON_PARAMS}
EN_TO_RU = {spec.en: spec.ru for spec in COMMON_PARAMS}


def normalize_bool(value: Any, *, style: str = "ru_string") -> Any:
    """Convert truthy/falsey values to VA-friendly representation."""
    if isinstance(value, bool):
        if style == "python":
            return value
        if style == "en_string":
            return "true" if value else "false"
        return "Истина" if value else "Ложь"
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"true", "истина", "1", "yes", "да"}:
            return normalize_bool(True, style=style)
        if lowered in {"false", "ложь", "0", "no", "нет"}:
            return normalize_bool(False, style=style)
        return value
    return normalize_bool(bool(value), style=style)


def detect_bool_style(sample: dict[str, Any]) -> str:
    for key in ("ДелатьОтчетВФорматеjUnit", "junitreport"):
        if key not in sample:
            continue
        raw = sample[key]
        if isinstance(raw, bool):
            return "python"
        if isinstance(raw, str) and raw in {"true", "false"}:
            return "en_string"
        return "ru_string"
    return "ru_string"
