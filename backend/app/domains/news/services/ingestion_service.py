"""
Ingestion service for the news domain.

Handles creation and update flows. For now it is a thin wrapper around the
legacy NewsService logic; responsibilities will be migrated here iteratively.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Any, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func

from app.core.exceptions import NewsServiceError, ValidationError
from app.models.news import (
    NewsItem,
    NewsCategory,
    SourceType,
    NewsTopic,
    SentimentLabel,
    NewsCreateSchema,
)

from ..repositories import NewsRepository, CompanyRepository


@dataclass
class NewsIngestionService:
    session: AsyncSession

    def __post_init__(self) -> None:
        self._repo = NewsRepository(self.session)
        self._company_repo = CompanyRepository(self.session)

    async def create_news_item(self, data: Dict[str, Any]) -> NewsItem:
        try:
            validated = await self._validate_news_data(data)
            existing = await self._repo.fetch_by_url(validated["source_url"])
            if existing:
                return existing

            news_item = NewsItem(**validated)
            self.session.add(news_item)
            await self.session.flush()
            await self._update_search_vector(news_item)
            await self.session.commit()
            await self.session.refresh(news_item)
            return news_item
        except ValidationError:
            raise
        except Exception as exc:
            await self.session.rollback()
            raise NewsServiceError(f"Failed to create news item: {exc}") from exc

    async def update_news_item(
        self,
        news_id: str,
        data: Dict[str, Any],
    ) -> Optional[NewsItem]:
        try:
            news_item = await self._repo.fetch_by_id(news_id)
            if not news_item:
                return None

            for key, value in data.items():
                if hasattr(news_item, key):
                    setattr(news_item, key, value)

            await self.session.commit()
            await self.session.refresh(news_item)
            return news_item
        except Exception as exc:
            await self.session.rollback()
            raise NewsServiceError(f"Failed to update news item: {exc}") from exc

    async def delete_news_item(self, news_id: str) -> bool:
        try:
            news_item = await self._repo.fetch_by_id(news_id)
            if not news_item:
                return False

            await self.session.delete(news_item)
            await self.session.commit()
            return True
        except Exception as exc:
            await self.session.rollback()
            raise NewsServiceError(f"Failed to delete news item: {exc}") from exc

    async def _validate_news_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            validated = NewsCreateSchema(**data)
            result = validated.model_dump()

            source_type = result.get("source_type")
            if isinstance(source_type, str):
                try:
                    result["source_type"] = SourceType(source_type)
                except ValueError:
                    result["source_type"] = SourceType.BLOG

            category = result.get("category")
            if isinstance(category, str):
                try:
                    result["category"] = NewsCategory(category)
                except ValueError:
                    result.pop("category", None)

            topic = result.get("topic")
            if isinstance(topic, str):
                try:
                    result["topic"] = NewsTopic(topic)
                except ValueError:
                    result.pop("topic", None)

            sentiment = result.get("sentiment")
            if isinstance(sentiment, str):
                try:
                    result["sentiment"] = SentimentLabel(sentiment)
                except ValueError:
                    result.pop("sentiment", None)

            company_id = result.get("company_id")
            if company_id:
                if isinstance(company_id, UUID):
                    result["company_id"] = company_id
                elif isinstance(company_id, str):
                    try:
                        result["company_id"] = UUID(company_id)
                    except ValueError:
                        company = await self._company_repo.fetch_by_name(company_id)
                        result["company_id"] = company.id if company else None
                else:
                    result["company_id"] = None

            return result
        except Exception as exc:
            raise ValidationError(f"Invalid news data: {exc}") from exc

    async def _update_search_vector(self, news_item: NewsItem) -> None:
        search_text = f"{news_item.title} {news_item.content or ''} {news_item.summary or ''}"
        news_item.search_vector = func.to_tsvector("english", search_text)


