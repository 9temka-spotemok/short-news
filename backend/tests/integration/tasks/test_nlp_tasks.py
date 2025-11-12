from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.domains.news.tasks import (
    classify_news,
    extract_keywords,
    run_in_loop,
    summarise_news,
)
from app.models import NewsItem, NewsKeyword
from app.models.news import NewsCategory, NewsTopic, SentimentLabel, SourceType
from app.services import nlp_service


class DummyProvider:
    def classify_topic(self, text: str, fallback: str | None = None):
        return NewsTopic.PRODUCT

    def sentiment(self, text: str) -> SentimentLabel:
        return SentimentLabel.POSITIVE

    def summarise(self, text: str, max_sentences: int = 3) -> str:
        return "Synthetic summary"

    def extract_keywords(self, text: str, limit: int = 8):
        return [("ai", 1.0), ("launch", 0.7)]

    def compute_priority(
        self,
        title: str,
        published_at: datetime,
        topic: NewsTopic | None,
    ) -> float:
        return 0.9


@pytest.fixture(autouse=True)
def _swap_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    original = nlp_service.PIPELINE.provider
    nlp_service.PIPELINE.provider = DummyProvider()
    yield
    nlp_service.PIPELINE.provider = original


@pytest.fixture(autouse=True)
def _override_session_factory(
    monkeypatch: pytest.MonkeyPatch,
    async_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    from app.domains import news
    from app.domains.news import tasks as news_tasks

    monkeypatch.setattr(news_tasks, "AsyncSessionLocal", async_session_factory)


async def _create_news(session: AsyncSession) -> str:
    news = NewsItem(
        title="AI Launch Event",
        summary="",
        content="We are excited to launch a new AI product.",
        source_url="https://example.com/news-ai-launch",
        source_type=SourceType.BLOG,
        category=NewsCategory.PRODUCT_UPDATE,
        published_at=datetime.now(timezone.utc),
        priority_score=0.5,
    )
    session.add(news)
    await session.commit()
    await session.refresh(news)
    return str(news.id)


@pytest.mark.asyncio
async def test_nlp_pipeline_tasks_end_to_end(
    async_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with async_session_factory() as session:
        news_id = await _create_news(session)

    classify_result = run_in_loop(lambda: classify_news(news_id))
    assert classify_result["topic"] == NewsTopic.PRODUCT.value
    assert classify_result["sentiment"] == SentimentLabel.POSITIVE.value
    assert classify_result["priority_score"] == 0.9

    summary_result = run_in_loop(lambda: summarise_news(news_id, force=True))
    assert summary_result["summary"] == "Synthetic summary"

    keywords_result = run_in_loop(lambda: extract_keywords(news_id, limit=5))
    assert len(keywords_result["keywords"]) == 2

    async with async_session_factory() as session:
        news_uuid = UUID(news_id)
        news = await session.get(NewsItem, news_uuid)
        assert news is not None
        assert news.topic == NewsTopic.PRODUCT
        assert news.sentiment == SentimentLabel.POSITIVE
        assert news.summary == "Synthetic summary"

        rows = await session.execute(
            select(NewsKeyword.keyword, NewsKeyword.relevance_score).where(
                NewsKeyword.news_id == news_uuid
            )
        )
        keywords = [(row[0], row[1]) for row in rows]
        assert ("ai", 1.0) in keywords
        assert ("launch", 0.7) in keywords

