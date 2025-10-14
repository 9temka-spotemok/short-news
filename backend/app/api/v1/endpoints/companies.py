"""
Companies endpoints
"""

from typing import Optional, List
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from loguru import logger

from app.core.database import get_db
from app.models.company import Company

router = APIRouter()


@router.get("/")
async def get_companies(
    search: Optional[str] = Query(None, description="Search companies by name"),
    limit: int = Query(100, ge=1, le=200, description="Number of companies to return"),
    offset: int = Query(0, ge=0, description="Number of companies to skip"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get list of companies with optional search
    """
    logger.info(f"Companies request: search={search}, limit={limit}, offset={offset}")
    
    try:
        # Build query
        query = select(Company).order_by(Company.name)
        
        # Apply search filter
        if search:
            query = query.where(Company.name.ilike(f"%{search}%"))
        
        # Apply pagination
        query = query.limit(limit).offset(offset)
        
        # Execute query
        result = await db.execute(query)
        companies = result.scalars().all()
        
        # Get total count
        count_query = select(func.count(Company.id))
        if search:
            count_query = count_query.where(Company.name.ilike(f"%{search}%"))
        
        total_result = await db.execute(count_query)
        total = total_result.scalar()
        
        # Convert to response format
        items = [
            {
                "id": str(company.id),
                "name": company.name,
                "website": company.website,
                "description": company.description,
                "category": company.category,
                "logo_url": company.logo_url
            }
            for company in companies
        ]
        
        return {
            "items": items,
            "total": total,
            "limit": limit,
            "offset": offset
        }
        
    except Exception as e:
        logger.error(f"Failed to get companies: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve companies")


@router.get("/{company_id}")
async def get_company(
    company_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get a specific company by ID
    """
    logger.info(f"Get company: {company_id}")
    
    try:
        from uuid import UUID
        
        # Parse UUID
        try:
            uuid_obj = UUID(company_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid company ID format")
        
        # Get company
        result = await db.execute(
            select(Company).where(Company.id == uuid_obj)
        )
        company = result.scalar_one_or_none()
        
        if not company:
            raise HTTPException(status_code=404, detail="Company not found")
        
        return {
            "id": str(company.id),
            "name": company.name,
            "website": company.website,
            "description": company.description,
            "category": company.category,
            "logo_url": company.logo_url,
            "twitter_handle": company.twitter_handle,
            "github_org": company.github_org,
            "created_at": company.created_at.isoformat() if company.created_at else None,
            "updated_at": company.updated_at.isoformat() if company.updated_at else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get company: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve company")





