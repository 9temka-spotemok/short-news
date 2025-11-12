"""
Repository helpers for company entities used within the news domain.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.company import Company


@dataclass
class CompanyRepository:
    session: AsyncSession

    async def fetch_by_name(self, name: str) -> Optional[Company]:
        stmt = select(Company).where(Company.name.ilike(f"%{name}%"))
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()





