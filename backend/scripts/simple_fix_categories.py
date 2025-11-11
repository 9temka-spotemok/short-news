"""
Utility script to normalise news categories using SQLAlchemy abstractions.
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path
from typing import List

from sqlalchemy import desc, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.models.company import Company  # noqa: E402
from app.models.news import NewsItem  # noqa: E402


def determine_category(title: str, company: str) -> str:
    """Determine news category based on title content."""
    title_lower = title.lower()

    if any(
        keyword in title_lower
        for keyword in [
            "api",
            "technical",
            "update",
            "improvement",
            "performance",
            "optimization",
            "infrastructure",
            "system",
            "backend",
        ]
    ):
        return "technical_update"

    if any(
        keyword in title_lower
        for keyword in [
            "release",
            "launch",
            "new feature",
            "product",
            "version",
            "announcement",
            "introducing",
        ]
    ):
        return "product_update"

    if any(
        keyword in title_lower
        for keyword in [
            "strategy",
            "partnership",
            "collaboration",
            "acquisition",
            "investment",
            "funding",
            "business",
            "market",
        ]
    ):
        return "strategic_announcement"

    if any(
        keyword in title_lower
        for keyword in [
            "research",
            "paper",
            "study",
            "analysis",
            "findings",
            "publication",
            "journal",
        ]
    ):
        return "research_paper"

    if any(
        keyword in title_lower
        for keyword in [
            "security",
            "safety",
            "privacy",
            "protection",
            "vulnerability",
        ]
    ):
        return "security_update"

    if any(
        keyword in title_lower
        for keyword in [
            "model",
            "gpt",
            "claude",
            "gemini",
            "llama",
            "training",
            "dataset",
            "weights",
        ]
    ):
        return "model_release"

    company_defaults = {
        "OpenAI": "product_update",
        "Anthropic": "product_update",
        "Google": "technical_update",
        "Meta": "product_update",
        "Hugging Face": "technical_update",
        "Mistral AI": "product_update",
        "Cohere": "technical_update",
        "Stability AI": "product_update",
        "Perplexity AI": "product_update",
    }

    return company_defaults.get(company, "product_update")


def _build_database_url() -> str:
    if url := os.getenv("DATABASE_URL"):
        return url

    host = os.getenv("DB_HOST", "postgres")
    port = os.getenv("DB_PORT", "5432")
    database = os.getenv("DB_NAME", "shot_news")
    user = os.getenv("DB_USER", "shot_news")
    password = os.getenv("DB_PASSWORD", "shot_news_dev")
    return f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{database}"


async def fix_categories() -> None:
    engine = create_async_engine(_build_database_url(), future=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    try:
        async with session_factory() as session:
            stmt = (
                select(NewsItem.id, NewsItem.title, Company.name)
                .join(Company, NewsItem.company_id == Company.id, isouter=True)
                .where(or_(NewsItem.category.is_(None), NewsItem.category == "product_update"))
            )
            rows = (await session.execute(stmt)).all()
            print(f"Found {len(rows)} news items to fix")

            updated_count = 0
            for news_id, title, company_name in rows:
                new_category = determine_category(title, company_name or "Unknown")
                await session.execute(
                    update(NewsItem).where(NewsItem.id == news_id).values(category=new_category)
                )
                updated_count += 1
                print(f"Updated: '{title[:50]}...' -> {new_category}")

            await session.commit()
            print(f"✅ Updated {updated_count} news items")

            dist_stmt = (
                select(NewsItem.category, func.count(NewsItem.id).label("count"))
                .where(NewsItem.category.is_not(None))
                .group_by(NewsItem.category)
                .order_by(desc("count"))
            )
            distribution = (await session.execute(dist_stmt)).all()

            print("\nCategory distribution:")
            for category, count in distribution:
                print(f"  {category}: {count}")

    finally:
        await engine.dispose()
            )
            updated_count += 1
            print(f"Updated: '{title[:50]}...' -> {new_category}")

        await session.commit()
        print(f"✅ Updated {updated_count} news items")

        dist_stmt = (
            select(NewsItem.category, func.count(NewsItem.id).label("count"))
            .where(NewsItem.category.is_not(None))
            .group_by(NewsItem.category)
            .order_by(desc("count"))
        )
        distribution = (await session.execute(dist_stmt)).all()

        print("\nCategory distribution:")
        for category, count in distribution:
            print(f"  {category}: {count}")

    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(fix_categories())
