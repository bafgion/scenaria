"""Tests for data-table and variable help topics."""

from __future__ import annotations

from app.help_topics import (
    GUIDE_CATEGORY,
    format_guide_help,
    guide_by_id,
    list_guide_topics,
)


def test_list_guide_topics_data_category() -> None:
    topics = list_guide_topics(category=GUIDE_CATEGORY)
    assert len(topics) >= 3
    labels = {topic.label for topic in topics}
    assert "Таблица примеров (Структура сценария)" in labels
    assert "Наборы параметров (.params.json)" in labels
    assert "Переменные {{имя}}" in labels


def test_list_guide_topics_search_outline() -> None:
    topics = list_guide_topics(query="структура сценария")
    assert topics
    assert topics[0].id == "outline-examples"


def test_format_guide_help_contains_example_table() -> None:
    topic = guide_by_id("outline-examples")
    assert topic is not None
    html_text = format_guide_help(topic)
    assert "Структура сценария" in html_text
    assert "Примеры:" in html_text
    assert "Данные и таблицы" in html_text


def test_params_json_topic_documents_filename() -> None:
    topic = guide_by_id("params-json")
    assert topic is not None
    assert ".params.json" in topic.description
    assert "cases" in topic.example
