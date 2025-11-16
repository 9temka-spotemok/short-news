import uuid
from datetime import datetime, timedelta, timezone

from app.models import NewsTopic, SentimentLabel, SourceType, NewsItem
from app.services.competitor_service import CompetitorAnalysisService


def _build_service() -> CompetitorAnalysisService:
    return CompetitorAnalysisService(db=None)  # type: ignore[arg-type]


def test_build_conditions_without_filters_creates_minimal_clauses() -> None:
    service = _build_service()
    company_id = uuid.uuid4()
    now = datetime.now(timezone.utc)
    date_from = (now - timedelta(days=7)).replace(tzinfo=None)
    date_to = now.replace(tzinfo=None)

    conditions = service._build_conditions(company_id, date_from, date_to, filters=None)

    assert len(conditions) == 3
    assert conditions[0].left == NewsItem.company_id
    assert conditions[1].left == NewsItem.published_at
    assert conditions[2].left == NewsItem.published_at


def test_build_conditions_with_filters_adds_expected_clauses() -> None:
    service = _build_service()
    company_id = uuid.uuid4()
    now = datetime.now(timezone.utc)
    date_from = (now - timedelta(days=30)).replace(tzinfo=None)
    date_to = now.replace(tzinfo=None)
    filters = {
        "topics": [NewsTopic.TECHNOLOGY, NewsTopic.SECURITY],
        "sentiments": [SentimentLabel.POSITIVE],
        "source_types": [SourceType.BLOG],
        "min_priority": 0.7,
    }

    conditions = service._build_conditions(company_id, date_from, date_to, filters=filters)

    assert len(conditions) == 7
    topic_clause = conditions[3]
    sentiment_clause = conditions[4]
    source_clause = conditions[5]
    priority_clause = conditions[6]

    assert topic_clause.left == NewsItem.topic
    assert {item.value for item in topic_clause.right.value} == {
        NewsTopic.TECHNOLOGY.value,
        NewsTopic.SECURITY.value,
    }

    assert sentiment_clause.left == NewsItem.sentiment
    assert {item.value for item in sentiment_clause.right.value} == {SentimentLabel.POSITIVE.value}

    assert source_clause.left == NewsItem.source_type
    assert {item.value for item in source_clause.right.value} == {SourceType.BLOG.value}

    assert priority_clause.left == NewsItem.priority_score
    assert float(priority_clause.right.value) == 0.7
