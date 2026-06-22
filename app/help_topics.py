"""Non-step help topics: data tables, parameter sets, variables."""

from __future__ import annotations

import html
from dataclasses import dataclass

GUIDE_CATEGORY = "data"

GUIDE_CATEGORY_LABELS: dict[str, str] = {
    "all": "Все",
    "data": "Данные и таблицы",
}


@dataclass(frozen=True)
class GuideTopic:
    id: str
    label: str
    category: str
    description: str
    example: str
    details: tuple[str, ...] = ()
    insert_text: str | None = None
    keywords: str = ""


_OUTLINE_TEMPLATE = (
    "Функционал: Авторизация\n"
    "Структура сценария: Вход с разными учётками\n"
    "\tДопустим открыт \"<url>\"\n"
    "\tИ ввожу \"<login>\" в \"#email\"\n"
    "\tИ ввожу \"<password>\" в \"#password\"\n"
    "\tИ нажимаю \"button[type=submit]\"\n"
    "\n"
    "Примеры:\n"
    "  | url              | login       | password |\n"
    "  | https://a.test   | user@a.ru   | pass1    |\n"
    "  | https://b.test   | user@b.ru   | pass2    |"
)

_PARAMS_JSON_EXAMPLE = (
    "{\n"
    '  "cases": [\n'
    "    {\n"
    '      "label": "админ",\n'
    '      "variables": {\n'
    '        "login": "admin@test.ru",\n'
    '        "password": "secret"\n'
    "      }\n"
    "    },\n"
    "    {\n"
    '      "label": "гость",\n'
    '      "variables": {\n'
    '        "login": "guest@test.ru",\n'
    '        "password": "guest"\n'
    "      }\n"
    "    }\n"
    "  ]\n"
    "}"
)

GUIDE_TOPICS: tuple[GuideTopic, ...] = (
    GuideTopic(
        id="outline-examples",
        label="Таблица примеров (Структура сценария)",
        category=GUIDE_CATEGORY,
        description=(
            "Один шаблон сценария и таблица данных: каждая строка «Примеры» — отдельный прогон. "
            "В шагах используйте плейсхолдеры <имя_колонки>; имена колонок совпадают с заголовками таблицы."
        ),
        example=_OUTLINE_TEMPLATE,
        details=(
            "Вместо «Сценарий:» укажите «Структура сценария:».",
            "После шагов добавьте блок «Примеры:» и pipe-таблицу (строки начинаются с |).",
            "При пакетном прогоне Scenaria выполнит сценарий столько раз, сколько строк в таблице.",
            "В каталоге у файла отображается бейдж «N прим.».",
        ),
        insert_text=_OUTLINE_TEMPLATE,
        keywords="структура сценария примеры outline examples таблица данные placeholder",
    ),
    GuideTopic(
        id="params-json",
        label="Наборы параметров (.params.json)",
        category=GUIDE_CATEGORY,
        description=(
            "Внешний JSON рядом с .feature: несколько наборов переменных без таблицы в Gherkin. "
            "Имя файла: <сценарий>.params.json (например login.params.json для login.feature)."
        ),
        example=_PARAMS_JSON_EXAMPLE,
        details=(
            "В шагах подставляйте значения как {{login}}, {{password}} и т.д.",
            "Каждый объект в cases — один прогон; поле label попадает в название кейса в отчёте.",
            "Можно комбинировать с «Структура сценария»: сначала разворачиваются примеры, затем наборы из JSON.",
            "В каталоге у файла отображается бейдж «N пар.».",
        ),
        keywords="params json параметры наборы variables пар",
    ),
    GuideTopic(
        id="scenario-variables",
        label="Переменные {{имя}}",
        category=GUIDE_CATEGORY,
        description=(
            "Значения на время одного прогона: запомнить текст, поле или URL и использовать в следующих шагах. "
            "Переменные окружения: {{env:ИМЯ}} (например {{env:SCENARIA_EMAIL_CODE}} для OTP в headless)."
        ),
        example=(
            '\tИ запоминаю текст "user@test.ru" как "login"\n'
            '\tИ ввожу "{{login}}" в "#email"\n'
            '\tИ запоминаю URL как "profile_url"'
        ),
        details=(
            "Шаги «запоминаю текст … как …», «запоминаю значение поля … как …», «запоминаю URL как …».",
            "Неизвестная переменная при прогоне останавливает сценарий с понятной ошибкой.",
            "В цикле «для каждого …» переменная из variable доступна во вложенных шагах как {{имя}}.",
        ),
        keywords="переменные remember запоминаю env подстановка",
    ),
)


def list_guide_topics(
    *,
    query: str = "",
    category: str = "all",
) -> list[GuideTopic]:
    needle = query.strip().lower()
    result: list[GuideTopic] = []
    for topic in GUIDE_TOPICS:
        if category != "all" and topic.category != category:
            continue
        if needle:
            haystack = " ".join(
                (topic.label, topic.description, topic.example, topic.keywords, topic.category)
            ).lower()
            if needle not in haystack:
                continue
        result.append(topic)
    return result


def guide_by_id(topic_id: str) -> GuideTopic | None:
    for topic in GUIDE_TOPICS:
        if topic.id == topic_id:
            return topic
    return None


def format_guide_help(topic: GuideTopic) -> str:
    category_label = GUIDE_CATEGORY_LABELS.get(topic.category, topic.category)
    description = html.escape(topic.description)
    example = html.escape(topic.example)

    details_block = ""
    if topic.details:
        items = "".join(f"<li>{html.escape(line)}</li>" for line in topic.details)
        details_block = (
            '<section class="block">'
            '<div class="block-title">Как это работает</div>'
            f"<ul class=\"detail-list\">{items}</ul>"
            "</section>"
        )

    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
body {{
  margin: 0;
  padding: 4px 2px 12px 2px;
  font-family: "Segoe UI", sans-serif;
  font-size: 10pt;
  color: #cccccc;
  background-color: transparent;
}}
p, div, span, code, pre, ul, li, header, section {{
  background-color: transparent;
}}
.header {{
  margin-bottom: 14px;
  padding-bottom: 12px;
  border-bottom: 1px solid #3c3c3c;
}}
.title {{
  font-size: 18pt;
  font-weight: 600;
  color: #ffffff;
  letter-spacing: 0.02em;
}}
.meta {{
  margin-top: 8px;
}}
.badge {{
  display: inline;
  margin-right: 8px;
  padding: 1px 8px;
  border-radius: 4px;
  font-size: 8pt;
  font-weight: 600;
  color: #858585;
  background: transparent;
  border: 1px solid #454545;
}}
.desc {{
  margin: 0;
  line-height: 1.45;
  color: #cccccc;
}}
.block {{
  margin-top: 14px;
}}
.block-title {{
  font-size: 8pt;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: #858585;
  margin-bottom: 8px;
}}
.detail-list {{
  margin: 0;
  padding-left: 18px;
  line-height: 1.45;
  color: #cccccc;
}}
.detail-list li {{
  margin-bottom: 6px;
}}
.example-box {{
  margin-top: 4px;
  padding: 0 0 0 10px;
  background-color: transparent;
  border: none;
  border-left: 2px solid #454545;
}}
.example-code {{
  margin: 0;
  font-family: Consolas, "Cascadia Mono", monospace;
  font-size: 10pt;
  line-height: 1.5;
  color: #ce9178;
  white-space: pre-wrap;
  word-break: break-word;
  background-color: transparent;
}}
</style>
</head>
<body>
<header class="header">
  <div class="title">{html.escape(topic.label)}</div>
  <p class="meta">
    <span class="badge">{html.escape(category_label)}</span>
    <span class="badge">справка</span>
  </p>
</header>
<p class="desc">{description}</p>
{details_block}
<section class="block">
  <div class="block-title">Пример</div>
  <div class="example-box">
    <span class="example-code">{example}</span>
  </div>
</section>
</body>
</html>"""
