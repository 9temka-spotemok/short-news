"""
SQLAlchemy repositories for competitor intelligence domain.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from loguru import logger
from sqlalchemy import and_, desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from sqlalchemy import select

from app.models import Company, CompetitorComparison


@dataclass
class CompetitorRepository:
    """Low-level data access for competitor entities."""

    session: AsyncSession

    async def fetch_companies(self, company_ids: List[str]) -> List[Company]:
        """Load companies by their UUID strings."""
        uuids: List[uuid.UUID] = []
        for company_id in company_ids:
            try:
                uuids.append(uuid.UUID(company_id))
            except ValueError as exc:
                logger.error("Invalid company ID format: %s", company_id)
                raise ValueError(f"Invalid company ID format: {company_id}") from exc

        result = await self.session.execute(
            select(Company).where(Company.id.in_(uuids))
        )
        companies = list(result.scalars().all())

        found_ids = {str(company.id) for company in companies}
        missing = set(company_ids) - found_ids
        if missing:
            logger.warning("Companies not found: %s", missing)

        return companies

    async def list_user_comparisons(
        self,
        user_id: str,
        limit: int,
    ) -> List[Dict[str, Any]]:
        """Return lightweight information about stored comparisons."""
        result = await self.session.execute(
            select(CompetitorComparison)
            .where(CompetitorComparison.user_id == uuid.UUID(user_id))
            .order_by(desc(CompetitorComparison.created_at))
            .limit(limit)
        )
        comparisons = result.scalars().all()

        return [
            {
                "id": str(comparison.id),
                "name": comparison.name,
                "company_ids": [str(cid) for cid in comparison.company_ids],
                "date_from": comparison.date_from.isoformat(),
                "date_to": comparison.date_to.isoformat(),
                "created_at": comparison.created_at.isoformat(),
            }
            for comparison in comparisons
        ]

    async def get_comparison(
        self,
        comparison_id: str,
        user_id: str,
    ) -> Optional[CompetitorComparison]:
        """Fetch a stored comparison belonging to a given user."""
        result = await self.session.execute(
            select(CompetitorComparison).where(
                and_(
                    CompetitorComparison.id == uuid.UUID(comparison_id),
                    CompetitorComparison.user_id == uuid.UUID(user_id),
                )
            )
        )
        return result.scalar_one_or_none()

    async def delete_comparison(
        self,
        comparison_id: str,
        user_id: str,
    ) -> bool:
        """Remove a comparison if it belongs to the user."""
        comparison = await self.get_comparison(comparison_id, user_id)
        if not comparison:
            return False

        await self.session.delete(comparison)
        await self.session.commit()
        return True

    async def save_comparison(
        self,
        *,
        user_id: str,
        company_ids: List[str],
        date_from: datetime,
        date_to: datetime,
        name: Optional[str],
        metrics: Dict[str, Any],
    ) -> CompetitorComparison:
        """Persist comparison snapshot."""
        comparison = CompetitorComparison(
            id=uuid.uuid4(),
            user_id=uuid.UUID(user_id),
            company_ids=[uuid.UUID(cid) for cid in company_ids],
            date_from=date_from,
            date_to=date_to,
            name=name or f"Comparison {datetime.now(timezone.utc).strftime('%Y-%m-%d')}",
            metrics=metrics,
            created_at=datetime.now(timezone.utc).replace(tzinfo=None),
            updated_at=datetime.now(timezone.utc).replace(tzinfo=None),
        )

        self.session.add(comparison)
        await self.session.commit()
        await self.session.refresh(comparison)
        logger.info("Comparison saved: %s", comparison.id)
        return comparison

    async def upsert_company(self, data: Dict[str, Any]) -> None:
        """Create or update a company record."""
        result = await self.session.execute(
            select(Company).where(Company.name == data["name"])
        )
        existing = result.scalar_one_or_none()
        if existing:
            updated_fields = {
                "website": data.get("website") or existing.website,
                "description": data.get("description") or existing.description,
                "category": data.get("category") or existing.category,
                "twitter_handle": data.get("twitter_handle") or existing.twitter_handle,
                "github_org": data.get("github_org") or existing.github_org,
                "logo_url": data.get("logo_url") or existing.logo_url,
            }
            for key, value in updated_fields.items():
                setattr(existing, key, value)
            await self.session.commit()
            return

        # Создаем глобальную компанию-конкурента (user_id=None)
        # Конкуренты являются общими для всех пользователей, не привязаны к конкретному пользователю
        company = Company(
            name=data["name"],
            website=data.get("website"),
            description=data.get("description"),
            category=data.get("category"),
            twitter_handle=data.get("twitter_handle"),
            github_org=data.get("github_org"),
            logo_url=data.get("logo_url"),
            user_id=None  # Глобальная компания-конкурент
        )
        self.session.add(company)
        await self.session.commit()

