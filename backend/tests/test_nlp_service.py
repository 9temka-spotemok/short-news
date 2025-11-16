import math
from datetime import datetime, timedelta, timezone

import pytest

from app.models.news import NewsTopic, SentimentLabel
from app.services.nlp_service import HeuristicNLPProvider


@pytest.fixture()
def provider() -> HeuristicNLPProvider:
    return HeuristicNLPProvider()


def test_classify_topic_detects_finance(provider: HeuristicNLPProvider) -> None:
    text = "Acme Corp announces a new Series B funding round led by major investors"
    assert provider.classify_topic(text) == NewsTopic.FINANCE


def test_classify_topic_uses_fallback_when_unknown(provider: HeuristicNLPProvider) -> None:
    text = "Completely unrelated text without known keywords"
    assert provider.classify_topic(text, fallback="technology") == NewsTopic.TECHNOLOGY


def test_sentiment_counts_positive_and_negative(provider: HeuristicNLPProvider) -> None:
    text = "Great launch with improved performance but minor downtime incident"
    assert provider.sentiment(text) == SentimentLabel.MIXED


def test_extract_keywords_filters_stopwords(provider: HeuristicNLPProvider) -> None:
    text = "Our platform launch introduces optimized workflows for analytics teams"
    keywords = provider.extract_keywords(text, limit=5)
    extracted = {word for word, _ in keywords}
    assert "launch" in extracted
    assert "platform" in extracted
    assert "the" not in extracted


def test_compute_priority_combines_signals(provider: HeuristicNLPProvider) -> None:
    published_at = datetime.now(timezone.utc) - timedelta(hours=2)
    score = provider.compute_priority(
        title="Major funding announcement", published_at=published_at, topic=NewsTopic.FINANCE
    )
    assert 0.1 <= score <= 1.0
    assert math.isclose(score, min(score, 1.0))


def test_compute_priority_older_news_decreases_score(provider: HeuristicNLPProvider) -> None:
    recent = provider.compute_priority(
        title="Company roadmap update", published_at=datetime.now(timezone.utc), topic=NewsTopic.OTHER
    )
    older = provider.compute_priority(
        title="Company roadmap update",
        published_at=datetime.now(timezone.utc) - timedelta(days=20),
        topic=NewsTopic.OTHER,
    )
    assert older < recent


def test_summarise_limits_sentences(provider: HeuristicNLPProvider) -> None:
    text = "One. Two. Three. Four."
    summary = provider.summarise(text, max_sentences=2)
    assert summary.count(".") <= 2
