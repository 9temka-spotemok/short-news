"""
Competitor analysis endpoints
"""

from typing import List, Optional
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, Body
from pydantic import BaseModel
from loguru import logger

from app.api.dependencies import get_current_user, get_competitor_facade
from app.models import (
    User,
    NewsTopic,
    SentimentLabel,
    SourceType,
    ChangeProcessingStatus,
)
from app.domains.competitors import CompetitorFacade
from app.schemas.competitor_events import CompetitorChangeEventSchema
from app.core.access_control import check_company_access
from app.core.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()


class CompareRequest(BaseModel):
    """Request model for company comparison"""
    company_ids: List[str]
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    name: Optional[str] = None

@router.post("/compare")
async def compare_companies(
    request_data: dict = Body(...),
    current_user: User = Depends(get_current_user),
    facade: CompetitorFacade = Depends(get_competitor_facade),
    db: AsyncSession = Depends(get_db),
):
    """
    Compare multiple companies
    
    Request body:
    {
        "company_ids": ["uuid1", "uuid2", "uuid3"],
        "date_from": "2025-01-01",  // optional
        "date_to": "2025-01-31",     // optional
        "name": "Q1 2025 Comparison" // optional
    }
    
    ВАЖНО: Все company_ids должны принадлежать пользователю (user_id).
    """
    logger.info(f"Compare companies request from user {current_user.id}")
    logger.info(f"Request data: {request_data}")
    logger.info(f"Request type: {type(request_data)}")
    
    try:
        # Extract data from request
        company_ids = request_data.get('company_ids', [])
        date_from_str = request_data.get('date_from')
        date_to_str = request_data.get('date_to')
        name = request_data.get('name')
        topics_raw = request_data.get('topics', [])
        sentiments_raw = request_data.get('sentiments', [])
        source_types_raw = request_data.get('source_types', [])
        min_priority = request_data.get('min_priority')
        
        logger.info(f"Company IDs: {company_ids}")
        logger.info(f"Company IDs type: {type(company_ids)}")
        
        # Validate input
        if not isinstance(company_ids, list):
            raise HTTPException(status_code=400, detail="company_ids must be a list")
        
        if len(company_ids) < 2:
            raise HTTPException(status_code=400, detail="At least 2 companies required for comparison")
        
        if len(company_ids) > 5:
            raise HTTPException(status_code=400, detail="Maximum 5 companies can be compared at once")
        
        # ВАЛИДАЦИЯ: проверяем доступ к каждой компании (user_id)
        unauthorized_ids = []
        for company_id in company_ids:
            try:
                company = await check_company_access(company_id, current_user, db)
                if not company:
                    unauthorized_ids.append(company_id)
            except (ValueError, TypeError) as e:
                logger.warning(f"Invalid company ID format: {company_id}, error: {e}")
                unauthorized_ids.append(company_id)
        
        if unauthorized_ids:
            raise HTTPException(
                status_code=403,
                detail=f"Access denied: You don't have access to some of the requested companies. "
                       f"Unauthorized company IDs: {unauthorized_ids}"
            )
        
        # Validate UUIDs
        import uuid as uuid_lib
        for company_id in company_ids:
            try:
                uuid_lib.UUID(company_id)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid company ID format: {company_id}")
        
        # Parse dates
        if date_from_str:
            try:
                date_from = datetime.fromisoformat(date_from_str.replace('Z', '+00:00')).replace(tzinfo=None)
            except ValueError as e:
                logger.error(f"Invalid date_from format: {date_from_str}, error: {e}")
                raise HTTPException(status_code=400, detail=f"Invalid date_from format: {date_from_str}")
        else:
            date_from = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=30)  # Default: last 30 days
        
        if date_to_str:
            try:
                date_to = datetime.fromisoformat(date_to_str.replace('Z', '+00:00')).replace(tzinfo=None)
            except ValueError as e:
                logger.error(f"Invalid date_to format: {date_to_str}, error: {e}")
                raise HTTPException(status_code=400, detail=f"Invalid date_to format: {date_to_str}")
        else:
            date_to = datetime.now(timezone.utc).replace(tzinfo=None)
        
        logger.info(f"Parsed dates: from={date_from}, to={date_to}")

        filters: Optional[dict] = None

        try:
            topics = [NewsTopic(topic) for topic in topics_raw] if topics_raw else []
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=f"Invalid topic filter: {exc}")

        try:
            sentiments = [SentimentLabel(sentiment) for sentiment in sentiments_raw] if sentiments_raw else []
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=f"Invalid sentiment filter: {exc}")

        try:
            sources = [SourceType(source) for source in source_types_raw] if source_types_raw else []
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=f"Invalid source_type filter: {exc}")

        if topics or sentiments or sources or min_priority is not None:
            filters = {
                "topics": topics,
                "sentiments": sentiments,
                "source_types": sources,
                "min_priority": float(min_priority) if min_priority is not None else None,
            }
 
        # Perform comparison
        comparison_data = await facade.compare_companies(
            company_ids=company_ids,
            date_from=date_from,
            date_to=date_to,
            user_id=str(current_user.id),
            comparison_name=name,
            filters=filters
        )
        
        return comparison_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error comparing companies: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to compare companies: {str(e)}")


@router.get("/comparisons")
async def get_user_comparisons(
    limit: int = 10,
    current_user: User = Depends(get_current_user),
    facade: CompetitorFacade = Depends(get_competitor_facade),
):
    """
    Get user's saved comparisons
    """
    logger.info(f"Get comparisons for user {current_user.id}")
    
    try:
        comparisons = await facade.get_user_comparisons(str(current_user.id), limit)
        
        return {
            "comparisons": comparisons,
            "total": len(comparisons)
        }
        
    except Exception as e:
        logger.error(f"Error fetching comparisons: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch comparisons")


@router.get("/comparisons/{comparison_id}")
async def get_comparison(
    comparison_id: str,
    current_user: User = Depends(get_current_user),
    facade: CompetitorFacade = Depends(get_competitor_facade),
):
    """
    Get specific comparison details
    """
    logger.info(f"Get comparison {comparison_id} for user {current_user.id}")
    
    try:
        comparison = await facade.get_comparison(comparison_id, str(current_user.id))
        
        if not comparison:
            raise HTTPException(status_code=404, detail="Comparison not found")
        
        return comparison
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching comparison: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch comparison")


@router.delete("/comparisons/{comparison_id}")
async def delete_comparison(
    comparison_id: str,
    current_user: User = Depends(get_current_user),
    facade: CompetitorFacade = Depends(get_competitor_facade),
):
    """
    Delete a comparison
    """
    logger.info(f"Delete comparison {comparison_id} for user {current_user.id}")
    
    try:
        success = await facade.delete_comparison(comparison_id, str(current_user.id))
        
        if not success:
            raise HTTPException(status_code=404, detail="Comparison not found")
        
        return {"status": "success", "message": "Comparison deleted"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting comparison: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete comparison")


@router.get("/activity/{company_id}")
async def get_company_activity(
    company_id: str,
    days: int = 30,
    current_user: User = Depends(get_current_user),
    facade: CompetitorFacade = Depends(get_competitor_facade),
    db: AsyncSession = Depends(get_db),
):
    """
    Get activity metrics for a specific company.
    
    ВАЖНО: Проверяет, что компания принадлежит пользователю (user_id).
    """
    logger.info(f"Get activity for company {company_id} from user {current_user.id}")
    
    try:
        # Проверка доступа: компания должна принадлежать пользователю
        company = await check_company_access(company_id, current_user, db)
        if not company:
            # Всегда возвращаем 404 для недоступных ресурсов (безопасность)
            raise HTTPException(status_code=404, detail="Company not found")
        
        import uuid as uuid_lib
        
        date_from = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=days)
        date_to = datetime.now(timezone.utc).replace(tzinfo=None)
        
        company_uuid = uuid_lib.UUID(company_id)
        
        metrics = await facade.build_company_activity(
            company_uuid,
            date_from=date_from,
            date_to=date_to,
            top_news_limit=10,
        )
        
        return {
            "company_id": company_id,
            "period_days": days,
            "date_from": date_from.isoformat(),
            "date_to": date_to.isoformat(),
            "metrics": {
                "news_volume": metrics["news_volume"],
                "category_distribution": metrics["category_distribution"],
                "activity_score": metrics["activity_score"],
                "daily_activity": metrics["daily_activity"],
                "top_news": metrics["top_news"],
            }
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid company ID: {e}")
    except Exception as e:
        logger.error(f"Error fetching company activity: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch company activity")


@router.get("/suggest/{company_id}")
async def suggest_competitors(
    company_id: str,
    limit: int = 5,
    days: int = 30,
    current_user: User = Depends(get_current_user),
    facade: CompetitorFacade = Depends(get_competitor_facade),
    db: AsyncSession = Depends(get_db),
):
    """
    Автоматически подобрать конкурентов
    
    Query params:
        limit: сколько конкурентов вернуть (default: 5, max: 10)
        days: за какой период анализировать (default: 30)
    
    ВАЖНО: Проверяет, что компания принадлежит пользователю (user_id).
    """
    try:
        # Проверка доступа: компания должна принадлежать пользователю
        company = await check_company_access(company_id, current_user, db)
        if not company:
            # Всегда возвращаем 404 для недоступных ресурсов (безопасность)
            raise HTTPException(status_code=404, detail="Company not found")
        
        import uuid as uuid_lib
        
        company_uuid = uuid_lib.UUID(company_id)
        
        date_from = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=days)
        date_to = datetime.now(timezone.utc).replace(tzinfo=None)
        
        suggestions = await facade.suggest_competitors(
            company_id=company_uuid,
            limit=min(limit, 10),
            date_from=date_from,
            date_to=date_to
        )
        
        return {
            "company_id": company_id,
            "period_days": days,
            "suggestions": suggestions
        }
        
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid company ID")
    except Exception as e:
        logger.error(f"Error suggesting competitors: {e}")
        raise HTTPException(status_code=500, detail="Failed to suggest competitors")


@router.post("/themes")
async def analyze_themes(
    request_data: dict = Body(...),
    current_user: User = Depends(get_current_user),
    facade: CompetitorFacade = Depends(get_competitor_facade),
):
    """
    Анализ новостных тем для списка компаний
    
    Body:
        {
            "company_ids": ["uuid1", "uuid2", "uuid3"],
            "date_from": "2025-01-01",  // optional
            "date_to": "2025-01-31"     // optional
        }
    """
    try:
        import uuid as uuid_lib
        
        # Извлекаем данные из request_data
        company_ids = request_data.get("company_ids", [])
        date_from_str = request_data.get("date_from")
        date_to_str = request_data.get("date_to")
        
        # Валидация company_ids
        if not isinstance(company_ids, list):
            raise HTTPException(status_code=400, detail="company_ids must be a list")
        
        company_uuids = []
        for company_id in company_ids:
            try:
                company_uuids.append(uuid_lib.UUID(company_id))
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid company ID: {company_id}")
        
        # Парсинг дат
        if date_from_str:
            date_from_dt = datetime.fromisoformat(date_from_str).replace(tzinfo=None)
        else:
            date_from_dt = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=30)
            
        if date_to_str:
            date_to_dt = datetime.fromisoformat(date_to_str).replace(tzinfo=None)
        else:
            date_to_dt = datetime.now(timezone.utc).replace(tzinfo=None)
        
        # Анализ тем
        themes_data = await facade.analyze_news_themes(
            company_ids=company_uuids,
            date_from=date_from_dt,
            date_to=date_to_dt
        )
        
        return themes_data
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid date format: {e}")
    except Exception as e:
        logger.error(f"Error analyzing themes: {e}")
        raise HTTPException(status_code=500, detail="Failed to analyze themes")


@router.get("/changes/{company_id}")
async def list_change_events(
    company_id: str,
    limit: int = 20,
    status: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    facade: CompetitorFacade = Depends(get_competitor_facade),
):
    try:
        import uuid as uuid_lib

        company_uuid = uuid_lib.UUID(company_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid company ID")

    status_filter: Optional[ChangeProcessingStatus] = None
    if status:
        try:
            status_filter = ChangeProcessingStatus(status)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid status filter")

    events = await facade.list_change_events_payload(
        company_uuid,
        limit=max(1, min(limit, 100)),
        status=status_filter,
    )

    payload = [
        CompetitorChangeEventSchema.model_validate(event).model_dump()
        for event in events
    ]

    return {"events": payload, "total": len(payload)}


@router.post("/changes/{event_id}/recompute")
async def recompute_change_event(
    event_id: str,
    current_user: User = Depends(get_current_user),
    facade: CompetitorFacade = Depends(get_competitor_facade),
):
    try:
        import uuid as uuid_lib

        event_uuid = uuid_lib.UUID(event_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid event ID")

    event = await facade.recompute_change_event(event_uuid)

    if not event:
        raise HTTPException(status_code=404, detail="Change event not found")

    data = await facade.fetch_change_event_payload(event.id)
    if not data:
        data = {
            "id": event.id,
            "company_id": event.company_id,
            "source_type": event.source_type,
            "change_summary": event.change_summary,
            "changed_fields": event.changed_fields or [],
            "raw_diff": event.raw_diff or {},
            "detected_at": event.detected_at,
            "processing_status": event.processing_status,
            "notification_status": event.notification_status,
            "current_snapshot": None,
            "previous_snapshot": None,
        }
    schema = CompetitorChangeEventSchema.model_validate(data)
    return schema.model_dump()


@router.post("/ingest-pricing")
async def ingest_pricing_page_endpoint(
    request_data: dict = Body(...),
    current_user: User = Depends(get_current_user),
):
    """
    Запустить парсинг pricing страницы конкурента
    
    Body:
    {
        "company_id": "uuid",
        "source_url": "https://example.com/pricing",
        "source_type": "news_site"  // optional, default: "news_site"
    }
    """
    from app.tasks.competitors import ingest_pricing_page
    import uuid as uuid_lib
    
    company_id = request_data.get("company_id")
    source_url = request_data.get("source_url")
    source_type_str = request_data.get("source_type", "news_site")
    
    if not company_id or not source_url:
        raise HTTPException(
            status_code=400,
            detail="company_id and source_url are required"
        )
    
    try:
        company_uuid = uuid_lib.UUID(company_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid company_id format")
    
    try:
        source_type = SourceType(source_type_str)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid source_type: {source_type_str}. Must be one of: {[e.value for e in SourceType]}"
        )
    
    try:
        task = ingest_pricing_page.delay(
            company_id=company_id,
            source_url=source_url,
            source_type=source_type.value
        )
        logger.info(
            f"User {current_user.id} queued pricing ingestion for company {company_id} from {source_url}"
        )
        return {
            "status": "queued",
            "task_id": task.id,
            "message": "Pricing page ingestion queued",
            "company_id": company_id,
            "source_url": source_url
        }
    except Exception as e:
        logger.error(f"Failed to queue pricing ingestion: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to queue pricing ingestion: {str(e)}"
        )