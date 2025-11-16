"""
Ingestion service for the news domain.

Handles creation and update flows. For now it is a thin wrapper around the
legacy NewsService logic; responsibilities will be migrated here iteratively.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Any, Optional
from uuid import UUID

import httpx
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func
from bs4 import BeautifulSoup

from app.core.exceptions import NewsServiceError, ValidationError
from app.core.config import settings
from app.utils.datetime_utils import parse_iso_datetime, to_naive_utc
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
    _DETAIL_FETCH_TIMEOUT = 10.0
    _MIN_SUMMARY_LENGTH = 40

    def __post_init__(self) -> None:
        self._repo = NewsRepository(self.session)
        self._company_repo = CompanyRepository(self.session)

    async def create_news_item(self, data: Dict[str, Any]) -> NewsItem:
        try:
            data = await self._enrich_from_detail_page(data)
            logger.debug("Validating news payload")
            validated = await self._validate_news_data(data)
            logger.debug("Payload validated | %s", validated)
            existing = await self._repo.fetch_by_url(validated["source_url"])
            if existing:
                logger.debug("Existing news found for URL %s", validated["source_url"])
                setattr(existing, "_was_created", False)
                return existing

            logger.debug("Creating news item instance")
            news_item = NewsItem(**validated)
            self.session.add(news_item)
            logger.debug("Flushing new news item")
            await self.session.flush()
            logger.debug("Updating search vector")
            await self._update_search_vector(news_item)
            logger.debug("Committing new news item")
            await self.session.commit()
            await self.session.refresh(news_item)
            try:
                await self.session.refresh(
                    news_item,
                    attribute_names=["company", "keywords", "activities"],
                )
            except Exception:
                logger.debug(
                    "Skipping relationship refresh for news item %s",
                    news_item.id,
                )
            logger.debug("News item committed and refreshed")
            setattr(news_item, "_was_created", True)
            return news_item
        except ValidationError:
            raise
        except Exception as exc:
            await self.session.rollback()
            logger.exception("Failed to create news item")
            import traceback
            traceback.print_exc()
            raise NewsServiceError(f"Failed to create news item: {exc}") from exc

    async def _enrich_from_detail_page(self, data: Dict[str, Any]) -> Dict[str, Any]:
        if not settings.SCRAPER_DETAIL_ENRICHMENT_ENABLED:
            return data

        url = data.get("source_url")
        if not url:
            return data

        timeout_seconds = min(
            max(1.0, self._DETAIL_FETCH_TIMEOUT),
            float(settings.SCRAPER_TIMEOUT),
        )
        try:
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(timeout_seconds),
                headers={"User-Agent": settings.SCRAPER_USER_AGENT},
                follow_redirects=True,
            ) as client:
                response = await client.get(str(url))
            if response.status_code != 200 or not response.text:
                logger.debug(
                    "Detail enrichment skipped for %s due to status %s",
                    url,
                    response.status_code,
                )
                return data
        except httpx.HTTPError as exc:
            logger.debug("Detail enrichment failed for %s: %s", url, exc)
            return data

        soup = BeautifulSoup(response.text, "html.parser")

        title = self._extract_detail_title(soup)
        if title:
            data["title"] = title

        summary = data.get("summary") or ""
        if len(summary.strip()) < self._MIN_SUMMARY_LENGTH:
            description = self._extract_detail_description(soup)
            if description:
                data["summary"] = description[:400]

        return data

    @staticmethod
    def _extract_detail_title(soup: BeautifulSoup) -> Optional[str]:
        selectors = [
            'meta[property="og:title"]',
            'meta[name="og:title"]',
            'meta[name="twitter:title"]',
            'meta[property="twitter:title"]',
            'meta[name="title"]',
            'meta[property="title"]',
            "h1",
            "title",
        ]
        return NewsIngestionService._extract_text_from_selectors(soup, selectors)

    @staticmethod
    def _extract_detail_description(soup: BeautifulSoup) -> Optional[str]:
        selectors = [
            'meta[property="og:description"]',
            'meta[name="og:description"]',
            'meta[name="twitter:description"]',
            'meta[property="twitter:description"]',
            'meta[name="description"]',
            'meta[property="description"]',
        ]
        return NewsIngestionService._extract_text_from_selectors(soup, selectors)

    @staticmethod
    def _extract_text_from_selectors(soup: BeautifulSoup, selectors: Any) -> Optional[str]:
        for selector in selectors:
            tag = soup.select_one(selector)
            if not tag:
                continue
            if tag.name == "meta":
                value = tag.get("content")
            else:
                value = tag.get_text(strip=True)
            if value:
                return value.strip()
        return None

    async def update_news_item(
        self,
        news_id: str,
        data: Dict[str, Any],
    ) -> Optional[NewsItem]:
        try:
            news_uuid = UUID(str(news_id))
            news_item = await self._repo.fetch_by_id(news_uuid)
            if not news_item:
                return None

            for key, value in data.items():
                if hasattr(news_item, key):
                    normalised = await self._normalise_update_field(key, value)
                    setattr(news_item, key, normalised)

            await self.session.commit()
            await self.session.refresh(news_item)
            try:
                await self.session.refresh(
                    news_item,
                    attribute_names=["company", "keywords", "activities"],
                )
            except Exception:
                logger.debug(
                    "Skipping relationship refresh during update for news item %s",
                    news_item.id,
                )
            return news_item
        except Exception as exc:
            await self.session.rollback()
            raise NewsServiceError(f"Failed to update news item: {exc}") from exc

    async def delete_news_item(self, news_id: str) -> bool:
        try:
            news_uuid = UUID(str(news_id))
            news_item = await self._repo.fetch_by_id(news_uuid)
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

            source_url = result.get("source_url")
            if source_url is not None:
                result["source_url"] = str(source_url)

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

            published_at = result.get("published_at")
            if isinstance(published_at, str):
                parsed = parse_iso_datetime(published_at)
                result["published_at"] = to_naive_utc(parsed)
            else:
                result["published_at"] = to_naive_utc(published_at)

            return result
        except Exception as exc:
            raise ValidationError(f"Invalid news data: {exc}") from exc

    async def _normalise_update_field(self, key: str, value: Any) -> Any:
        if key == "source_url" and value is not None:
            return str(value)
        if key == "source_type" and value is not None:
            return SourceType(value) if not isinstance(value, SourceType) else value
        if key == "category" and value is not None:
            return NewsCategory(value) if not isinstance(value, NewsCategory) else value
        if key == "topic" and value is not None:
            return NewsTopic(value) if not isinstance(value, NewsTopic) else value
        if key == "sentiment" and value is not None:
            return SentimentLabel(value) if not isinstance(value, SentimentLabel) else value
        if key == "company_id" and value is not None:
            if isinstance(value, UUID):
                return value
            if isinstance(value, str):
                try:
                    return UUID(value)
                except ValueError:
                    company = await self._company_repo.fetch_by_name(value)
                    return company.id if company else None
            return None
        if key == "published_at" and value is not None:
            if isinstance(value, str):
                value = parse_iso_datetime(value)
            if isinstance(value, datetime):
                return to_naive_utc(value)
            return None
        return value

    async def _update_search_vector(self, news_item: NewsItem) -> None:
        search_text = f"{news_item.title} {news_item.content or ''} {news_item.summary or ''}"
        bind = getattr(self.session, "bind", None)
        dialect_name = getattr(getattr(bind, "dialect", None), "name", None)
        if dialect_name == "sqlite":
            news_item.search_vector = search_text
        else:
            news_item.search_vector = func.to_tsvector("english", search_text)



