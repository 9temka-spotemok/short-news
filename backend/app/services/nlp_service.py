"""
NLP service layer for news processing (topics, sentiment, summaries, keywords).
"""

from __future__ import annotations

import asyncio
import re
import uuid
from collections import Counter
from datetime import datetime, timezone
from typing import List, Optional, Sequence

from loguru import logger
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.keyword import NewsKeyword
from app.models.news import NewsItem, NewsTopic, SentimentLabel


def _normalize_text(parts: Sequence[str]) -> str:
    return " ".join(filter(None, (part.strip() for part in parts if part)))


class HeuristicNLPProvider:
    """Lightweight heuristics for topic classification, sentiment analysis and keyword extraction."""

    TOPIC_KEYWORDS = [
        (("funding", "seed", "series a", "series b", "ipo", "investment"), NewsTopic.FINANCE),
        (("launch", "introducing", "release", "feature", "update", "roadmap"), NewsTopic.PRODUCT),
        (("security", "breach", "vulnerability", "patch", "compliance"), NewsTopic.SECURITY),
        (("api", "sdk", "integration", "partner", "partnership"), NewsTopic.MARKET),
        (("performance", "benchmark", "speed", "latency", "scaling"), NewsTopic.TECHNOLOGY),
        (("research", "paper", "arxiv", "publication", "benchmark"), NewsTopic.RESEARCH),
        (("event", "conference", "webinar", "community"), NewsTopic.COMMUNITY),
        (("hire", "hires", "team", "leadership", "cso", "ceo", "cto"), NewsTopic.TALENT),
        (("regulation", "compliance", "policy", "legal", "governance"), NewsTopic.REGULATION),
        (("market", "customer", "growth", "traction"), NewsTopic.MARKET),
        (("strategy", "vision", "mission", "initiative"), NewsTopic.STRATEGY),
    ]

    POSITIVE_WORDS = {
        "best",
        "improved",
        "faster",
        "secure",
        "efficient",
        "optimised",
        "optimized",
        "growth",
        "success",
        "great",
        "positive",
        "win",
        "winner",
        "benefit",
        "enable",
        "leading",
        "strong",
        "accelerate",
    }
    NEGATIVE_WORDS = {
        "bug",
        "breach",
        "incident",
        "failure",
        "slow",
        "delay",
        "issue",
        "problem",
        "negative",
        "lawsuit",
        "regression",
        "attack",
        "downtime",
        "outage",
        "risk",
        "warning",
        "critical",
        "vulnerability",
    }

    STOPWORDS = {
        "the",
        "and",
        "that",
        "with",
        "from",
        "this",
        "have",
        "been",
        "will",
        "into",
        "about",
        "your",
        "their",
        "after",
        "before",
        "were",
        "there",
        "over",
        "under",
        "between",
        "through",
        "major",
        "minor",
        "very",
        "much",
        "more",
        "also",
        "many",
        "most",
        "such",
        "other",
        "only",
        "where",
        "when",
        "while",
        "because",
        "since",
        "until",
        "within",
        "without",
    }

    SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")
    WORD_RE = re.compile(r"[a-zA-Z][a-zA-Z\-]{3,}")

    def classify_topic(self, text: str, fallback: Optional[str] = None) -> Optional[NewsTopic]:
        text_lower = text.lower()
        for keywords, topic in self.TOPIC_KEYWORDS:
            if any(keyword in text_lower for keyword in keywords):
                return topic
        if fallback and fallback != "other":
            try:
                return NewsTopic(fallback)
            except ValueError:
                return None
        return None

    def sentiment(self, text: str) -> SentimentLabel:
        text_lower = text.lower()
        positive_hits = sum(word in text_lower for word in self.POSITIVE_WORDS)
        negative_hits = sum(word in text_lower for word in self.NEGATIVE_WORDS)

        if positive_hits > negative_hits and positive_hits > 0:
            return SentimentLabel.POSITIVE
        if negative_hits > positive_hits and negative_hits > 0:
            return SentimentLabel.NEGATIVE
        if positive_hits and negative_hits:
            return SentimentLabel.MIXED
        return SentimentLabel.NEUTRAL

    def summarise(self, text: str, max_sentences: int = 3) -> str:
        sentences = self.SENTENCE_SPLIT_RE.split(text.strip())
        if not sentences:
            return ""
        summary = " ".join(sentences[:max_sentences])
        return summary.strip()

    def extract_keywords(self, text: str, limit: int = 8) -> List[tuple[str, float]]:
        words = [word.lower() for word in self.WORD_RE.findall(text)]
        filtered = [word for word in words if word not in self.STOPWORDS and len(word) > 3]
        if not filtered:
            return []
        frequencies = Counter(filtered)
        max_freq = max(frequencies.values())
        keywords = [
            (word, round(freq / max_freq, 3))
            for word, freq in frequencies.most_common(limit)
        ]
        return keywords

    def compute_priority(self, title: str, published_at: datetime, topic: Optional[NewsTopic]) -> float:
        score = 0.45
        title_lower = title.lower()

        high_impact_words = {
            "launch": 0.18,
            "release": 0.18,
            "funding": 0.22,
            "breach": 0.25,
            "incident": 0.20,
            "acquisition": 0.20,
            "partnership": 0.15,
        }
        for word, bonus in high_impact_words.items():
            if word in title_lower:
                score += bonus

        if topic in {NewsTopic.FINANCE, NewsTopic.SECURITY}:
            score += 0.1
        elif topic == NewsTopic.PRODUCT:
            score += 0.05

        now = datetime.now(timezone.utc)
        published = published_at if published_at.tzinfo else published_at.replace(tzinfo=timezone.utc)
        age_days = (now - published).total_seconds() / 86400
        recency_bonus = max(0.0, 0.25 - min(age_days, 30) * 0.008)
        score += recency_bonus

        return max(0.1, min(score, 1.0))


class NewsNLPPipeline:
    def __init__(self, provider: Optional[HeuristicNLPProvider] = None):
        self.provider = provider or HeuristicNLPProvider()

    async def _get_news(self, session: AsyncSession, news_id: str) -> NewsItem:
        news_uuid = uuid.UUID(str(news_id))
        result = await session.execute(select(NewsItem).where(NewsItem.id == news_uuid))
        news = result.scalar_one_or_none()
        if not news:
            raise ValueError(f"News item {news_id} not found")
        return news

    async def classify_news(self, session: AsyncSession, news_id: str) -> dict:
        news = await self._get_news(session, news_id)
        text = _normalize_text([news.title or "", news.summary or "", news.content or ""])

        category_fallback = None
        if news.category:
            category_fallback = news.category.value if hasattr(news.category, "value") else str(news.category)

        topic = self.provider.classify_topic(
            text,
            fallback=category_fallback,
        )
        sentiment = self.provider.sentiment(text)
        priority_score = self.provider.compute_priority(
            news.title or "",
            news.published_at,
            topic,
        )

        news.topic = topic
        news.sentiment = sentiment
        news.priority_score = priority_score
        await session.commit()
        logger.info(
            "Classified news %s | topic=%s sentiment=%s priority=%.2f",
            news_id,
            topic.value if topic else None,
            sentiment.value,
            priority_score,
        )
        return {
            "news_id": news_id,
            "topic": topic.value if topic else None,
            "sentiment": sentiment.value,
            "priority_score": priority_score,
        }

    async def summarise_news(self, session: AsyncSession, news_id: str, force: bool = False) -> dict:
        news = await self._get_news(session, news_id)
        if news.summary and not force:
            logger.info("Summary already present for news %s, skipping", news_id)
            return {"news_id": news_id, "summary": news.summary}

        source_text = news.content or ""
        if not source_text:
            values = [news.summary, news.title]
            source_text = " ".join(filter(None, values))

        summary = self.provider.summarise(source_text)
        if summary:
            news.summary = summary
            await session.commit()
            logger.info("Summary generated for news %s", news_id)
        else:
            logger.info("No summary generated for news %s (empty text)", news_id)

        return {"news_id": news_id, "summary": news.summary or ""}

    async def extract_keywords(self, session: AsyncSession, news_id: str, limit: int = 8) -> dict:
        news = await self._get_news(session, news_id)
        text = _normalize_text([news.title or "", news.summary or "", news.content or ""])
        keywords = self.provider.extract_keywords(text, limit=limit)

        await session.execute(delete(NewsKeyword).where(NewsKeyword.news_id == news.id))
        for keyword, relevance in keywords:
            news_key = NewsKeyword(
                news_id=news.id,
                keyword=keyword,
                relevance_score=float(relevance),
            )
            session.add(news_key)

        await session.commit()
        logger.info("Extracted %d keywords for news %s", len(keywords), news_id)
        return {
            "news_id": news_id,
            "keywords": [{"keyword": word, "relevance": score} for word, score in keywords],
        }


PIPELINE = NewsNLPPipeline()
