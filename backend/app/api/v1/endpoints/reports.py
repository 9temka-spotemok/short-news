"""
Reports endpoints
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, Body, Response
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from loguru import logger
from uuid import UUID

from app.core.database import get_db
from app.api.dependencies import get_current_user
from app.models import User, Report, ReportStatus, Company
from app.models.news import NewsItem, NewsCategory, SourceType
from app.domains.reports.repositories import ReportRepository
from app.tasks.reports import generate_company_report

router = APIRouter()


class ReportCreateRequest(BaseModel):
    """Request model for report creation"""
    query: str = Field(..., min_length=1, max_length=500, description="Company name or URL query")


class ReportCreateResponse(BaseModel):
    """Response model for report creation"""
    report_id: str
    status: str
    created_at: str


class ReportStatusResponse(BaseModel):
    """Response model for report status"""
    status: str
    error: Optional[str] = None


class CategoryStats(BaseModel):
    """Category statistics"""
    category: str
    technicalCategory: str
    count: int


class SourceStats(BaseModel):
    """Source statistics"""
    url: str
    type: str
    count: int


class PricingInfo(BaseModel):
    """Pricing information"""
    description: Optional[str] = None
    news: Optional[List[dict]] = None


class CompetitorInfo(BaseModel):
    """Competitor information"""
    company: dict
    similarity_score: float
    common_categories: List[str]
    reason: str


class ReportResponse(BaseModel):
    """Full report response"""
    id: str
    query: str
    status: str
    company_id: Optional[str] = None
    company: Optional[dict] = None
    categories: Optional[List[CategoryStats]] = None
    news: Optional[List[dict]] = None
    sources: Optional[List[SourceStats]] = None
    pricing: Optional[PricingInfo] = None
    competitors: Optional[List[CompetitorInfo]] = None
    created_at: str
    completed_at: Optional[str] = None


class ReportsListResponse(BaseModel):
    """Response model for reports list"""
    items: List[ReportResponse]
    total: int
    limit: int
    offset: int


@router.post("/create", response_model=ReportCreateResponse)
async def create_report(
    request: ReportCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new report with quick analysis.
    Сразу выполняет быстрый анализ и сохраняет результаты в report_data.
    
    Request: { "query": "openai.com" }
    Response: { 
        "report_id": "uuid", 
        "status": "ready",
        "created_at": "2025-01-XX..."
    }
    
    Примечание: Логика статусов (processing, ready, error) сохранена для будущего
    full report через Celery task.
    """
    logger.info(f"Creating report for user {current_user.id} with query: {request.query}")
    
    try:
        report_repo = ReportRepository(db)
        report = None
        
        # Попытаться выполнить быстрый анализ
        try:
            # Импортируем функцию inline чтобы избежать циклических импортов
            from app.api.v1.endpoints.companies import _generate_quick_analysis_data
            
            # Генерируем данные быстрого анализа (включая конкурентов по умолчанию)
            try:
                report_data = await _generate_quick_analysis_data(db, request.query, include_competitors=True, user_id=current_user.id)
            except Exception as analysis_error:
                # Логируем детали ошибки анализа
                logger.error(f"Error in _generate_quick_analysis_data for query '{request.query}': {analysis_error}", exc_info=True)
                # Если это ValueError (компания не найдена), пробрасываем дальше
                if isinstance(analysis_error, ValueError):
                    raise
                # Для других ошибок создаем error report
                raise Exception(f"Failed to generate analysis data: {str(analysis_error)}") from analysis_error
            # Извлечь company_id безопасно
            company_id_str = report_data.pop("company_id", None)
            company_id = None
            if company_id_str:
                try:
                    # Убеждаемся что это валидный UUID
                    if isinstance(company_id_str, str):
                        company_id = UUID(company_id_str)
                    elif isinstance(company_id_str, UUID):
                        company_id = company_id_str
                    else:
                        logger.warning(f"Invalid company_id type: {type(company_id_str)}, value: {company_id_str}")
                        company_id = None
                except (ValueError, TypeError, AttributeError) as e:
                    logger.warning(f"Invalid company_id format: {company_id_str}: {e}")
                    company_id = None
            
            # Создать отчёт со статусом READY и сохранить данные
            try:
                # Очистить report_data от не-JSON-сериализуемых объектов
                import json
                try:
                    # Проверяем, что данные сериализуемы
                    json.dumps(report_data, default=str)
                except (TypeError, ValueError) as json_error:
                    logger.warning(f"Report data contains non-serializable objects, cleaning: {json_error}")
                    # Очищаем от не-сериализуемых объектов
                    def clean_for_json(obj):
                        if isinstance(obj, dict):
                            return {k: clean_for_json(v) for k, v in obj.items()}
                        elif isinstance(obj, list):
                            return [clean_for_json(item) for item in obj]
                        elif isinstance(obj, (datetime,)):
                            return obj.isoformat() if hasattr(obj, 'isoformat') else str(obj)
                        elif hasattr(obj, '__dict__'):
                            return str(obj)
                        else:
                            return obj
                    report_data = clean_for_json(report_data)
                
                # Подготовить данные для создания отчёта
                create_data = {
                    "user_id": current_user.id,
                    "query": request.query,
                    "status": ReportStatus.READY,
                }
                # Добавляем company_id только если он валидный
                if company_id is not None:
                    create_data["company_id"] = company_id
                
                logger.debug(f"Creating report with data: user_id={current_user.id}, query={request.query}, company_id={company_id}")
                report = await report_repo.create(create_data)
                
                # Сохранить данные отчёта в report_data
                # Передаем company_id только если он не None
                update_kwargs = {
                    "report_id": str(report.id),
                    "report_data": report_data,
                    "status": ReportStatus.READY,
                    "completed_at": datetime.now(timezone.utc)
                }
                if company_id is not None:
                    update_kwargs["company_id"] = company_id
                
                updated_report = await report_repo.update_report_data(**update_kwargs)
                
                if not updated_report:
                    logger.error(f"update_report_data returned None for report {report.id}")
                    raise Exception("Failed to update report data")
                
                await db.commit()
                logger.info(f"Created ready report {report.id} with quick analysis data")
            except Exception as db_error:
                logger.error(f"Database error while creating report: {db_error}", exc_info=True)
                await db.rollback()
                # Более детальное сообщение об ошибке
                error_msg = str(db_error)
                if "dbapi" in error_msg.lower() or "sqlalchemy" in error_msg.lower():
                    error_msg = f"Database error: {error_msg}"
                raise Exception(f"Database error: {error_msg}") from db_error
            
        except ValueError as e:
            # Компания не найдена - создаём отчёт со статусом ERROR
            logger.warning(f"Company not found for query '{request.query}': {e}")
            if report is None:
                report = await report_repo.create({
                    "user_id": current_user.id,
                    "query": request.query,
                    "status": ReportStatus.ERROR,
                    "error_message": str(e),
                })
                await db.commit()
                logger.info(f"Created error report {report.id} - company not found")
            
        except Exception as e:
            # Другая ошибка при анализе
            logger.error(f"Failed to generate quick analysis for query '{request.query}': {e}", exc_info=True)
            if report is None:
                try:
                    report = await report_repo.create({
                        "user_id": current_user.id,
                        "query": request.query,
                        "status": ReportStatus.ERROR,
                        "error_message": f"Failed to analyze company: {str(e)}",
                    })
                    await db.commit()
                    logger.info(f"Created error report {report.id} - analysis failed")
                except Exception as create_error:
                    logger.error(f"Failed to create error report: {create_error}", exc_info=True)
                    await db.rollback()
                    raise HTTPException(status_code=500, detail=f"Failed to create report: {str(e)}")
        
        if report is None:
            raise HTTPException(status_code=500, detail="Failed to create report: no report was created")
        
        return ReportCreateResponse(
            report_id=str(report.id),
            status=report.status.value,
            created_at=report.created_at.isoformat()
        )
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        # Логируем полную информацию об ошибке
        error_message = str(e)
        logger.error(f"Failed to create report for query '{request.query}': {error_message}", exc_info=True)
        
        # Убеждаемся что детали ошибки передаются в ответе
        detail_message = f"Failed to create report: {error_message}"
        raise HTTPException(status_code=500, detail=detail_message)


@router.get("/{report_id}/status", response_model=ReportStatusResponse)
async def get_report_status(
    report_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Check report status.
    
    Response: { 
        "status": "processing" | "ready" | "error",
        "error": null | "error message"
    }
    """
    try:
        report_uuid = UUID(report_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid report ID format")
    
    report_repo = ReportRepository(db)
    report = await report_repo.get_by_id(report_uuid)
    
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    
    # Check ownership
    if report.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    return ReportStatusResponse(
        status=report.status.value,
        error=report.error_message
    )


@router.get("/{report_id}", response_model=ReportResponse)
async def get_report(
    report_id: str,
    include_competitors: bool = Query(False, description="Include competitors data (may be slow)"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get full report data (only for status='ready').
    
    Response: {
        "id": "uuid",
        "query": "openai.com",
        "status": "ready",
        "company": {...},
        "categories": [...],
        "news": [...],
        "sources": [...],
        "pricing": {...},
        "created_at": "...",
        "completed_at": "..."
    }
    """
    try:
        report_uuid = UUID(report_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid report ID format")
    
    report_repo = ReportRepository(db)
    # ПРАВИЛЬНО: фильтруем по user_id в SQL запросе (безопасно - всегда возвращает 404 для недоступных)
    report = await report_repo.get_by_id(report_uuid, user_id=current_user.id, include_relations=True)
    
    if not report:
        # Всегда возвращаем 404 для недоступных ресурсов (безопасность)
        raise HTTPException(status_code=404, detail="Report not found")
    
    # If not ready, return basic info
    if report.status != ReportStatus.READY:
        return ReportResponse(
            id=str(report.id),
            query=report.query,
            status=report.status.value,
            company_id=str(report.company_id) if report.company_id else None,
            created_at=report.created_at.isoformat(),
            completed_at=report.completed_at.isoformat() if report.completed_at else None
        )
    
    # Сначала проверяем report_data из БД
    if report.report_data:
        logger.info(f"Returning report {report_id} data from report_data field")
        report_data = report.report_data
        
        # Преобразовать categories
        categories = None
        if report_data.get("categories"):
            try:
                categories = [CategoryStats(**cat) for cat in report_data.get("categories", [])]
            except Exception as e:
                logger.warning(f"Failed to parse categories: {e}")
                categories = None
        
        # Преобразовать sources
        sources = None
        if report_data.get("sources"):
            try:
                sources = [SourceStats(**src) for src in report_data.get("sources", [])]
            except Exception as e:
                logger.warning(f"Failed to parse sources: {e}")
                sources = None
        
        # Преобразовать pricing
        pricing = None
        if report_data.get("pricing"):
            try:
                pricing = PricingInfo(**report_data["pricing"])
            except Exception as e:
                logger.warning(f"Failed to parse pricing: {e}")
                pricing = None
        
        # Преобразовать competitors
        competitors = None
        if report_data.get("competitors"):
            try:
                competitors = [CompetitorInfo(**comp) for comp in report_data.get("competitors", [])]
            except Exception as e:
                logger.warning(f"Failed to parse competitors: {e}")
                competitors = None
        
        # Формируем ответ из сохранённых данных
        return ReportResponse(
            id=str(report.id),
            query=report.query,
            status=report.status.value,
            company_id=str(report.company_id) if report.company_id else None,
            company=report_data.get("company"),
            categories=categories,
            news=report_data.get("news"),
            sources=sources,
            pricing=pricing.dict() if pricing else None,
            competitors=[c.dict() for c in competitors] if competitors else None,
            created_at=report.created_at.isoformat(),
            completed_at=report.completed_at.isoformat() if report.completed_at else None
        )
    
    # Fallback: собираем данные динамически (для старых отчётов без report_data)
    logger.info(f"Report {report_id} has no report_data, loading dynamically")
    company = None
    categories = []
    sources = []
    news_items = []
    pricing_info = None
    competitors = []
    
    if report.company_id:
        # Load company
        result = await db.execute(
            select(Company).where(Company.id == report.company_id)
        )
        company_obj = result.scalar_one_or_none()
        
        if company_obj:
            company = {
                "id": str(company_obj.id),
                "name": company_obj.name,
                "website": company_obj.website,
                "description": company_obj.description,
                "logo_url": company_obj.logo_url,
                "category": company_obj.category,
            }
            
            # Load news items (только последние 5 для быстрого отчёта)
            result = await db.execute(
                select(NewsItem)
                .where(NewsItem.company_id == company_obj.id)
                .order_by(NewsItem.published_at.desc())
                .limit(5)  # Только 5 последних новостей для быстрого отчёта
            )
            news_items_db = result.scalars().all()
            
            # Count categories
            category_counts = {}
            for news in news_items_db:
                if news.category:
                    # Безопасное извлечение значения категории (может быть enum или строка)
                    cat_key = news.category.value if hasattr(news.category, 'value') else str(news.category)
                    category_counts[cat_key] = category_counts.get(cat_key, 0) + 1
            
            categories = [
                CategoryStats(
                    category=cat,
                    technicalCategory=cat,
                    count=count
                )
                for cat, count in category_counts.items()
            ]
            
            # Count sources
            source_counts = {}
            for news in news_items_db:
                source_url = news.source_url
                # Безопасное извлечение значения source_type (может быть enum или строка)
                if news.source_type:
                    source_type = news.source_type.value if hasattr(news.source_type, 'value') else str(news.source_type)
                else:
                    source_type = "blog"
                
                # Extract base URL
                from urllib.parse import urlparse
                try:
                    parsed = urlparse(source_url)
                    base_url = f"{parsed.scheme}://{parsed.netloc}"
                except Exception:
                    base_url = source_url
                
                if base_url not in source_counts:
                    source_counts[base_url] = {
                        "url": base_url,
                        "type": source_type,
                        "count": 0
                    }
                source_counts[base_url]["count"] += 1
            
            sources = [
                SourceStats(**data)
                for data in source_counts.values()
            ]
            
            # Format news items (только 5 последних)
            news_items = [
                {
                    "id": str(news.id),
                    "title": news.title,
                    "summary": news.summary,
                    "source_url": news.source_url,
                    "category": (news.category.value if hasattr(news.category, 'value') else str(news.category)) if news.category else None,
                    "published_at": news.published_at.isoformat() if news.published_at else None,
                    "created_at": news.created_at.isoformat() if news.created_at else None,
                }
                for news in news_items_db[:5]  # Только 5 последних новостей
            ]
            
            # Extract pricing info
            if company_obj.description:
                description_lower = company_obj.description.lower()
                if any(keyword in description_lower for keyword in ['pricing', 'price', '$', 'cost', 'plan']):
                    pricing_news = [
                        news for news in news_items
                        if news.get("category") == "pricing_change" or
                        any(keyword in (news.get("title", "") + " " + (news.get("summary", ""))).lower()
                            for keyword in ['price', 'pricing', '$', 'cost', 'plan'])
                    ][:10]
                    
                    pricing_info = PricingInfo(
                        description=company_obj.description,
                        news=pricing_news if pricing_news else None
                    )
            
            # Получить конкурентов (только если запрошено, т.к. это медленная операция)
            if include_competitors:
                try:
                    from app.services.competitor_service import CompetitorAnalysisService
                    from datetime import timedelta
                    competitor_service = CompetitorAnalysisService(db)
                    date_from = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=30)
                    date_to = datetime.now(timezone.utc).replace(tzinfo=None)
                    
                    logger.info(f"Loading competitors for company {company_obj.id} (this may take time...)")
                    suggestions_list = await competitor_service.suggest_competitors(
                        company_obj.id,
                        limit=5,  # Только 5 конкурентов для быстрого отчёта
                        date_from=date_from,
                        date_to=date_to
                    )
                    if suggestions_list:
                        competitors = [
                            CompetitorInfo(
                                company=suggestion["company"],
                                similarity_score=suggestion["similarity_score"],
                                common_categories=suggestion["common_categories"],
                                reason=suggestion["reason"]
                            )
                            for suggestion in suggestions_list[:5]
                        ]
                        logger.info(f"Loaded {len(competitors)} competitors for company {company_obj.id}")
                except Exception as e:
                    logger.error(f"Failed to get competitors for company {company_obj.id}: {e}", exc_info=True)
                    # Не прерываем возврат отчёта из-за ошибки конкурентов
                    # Просто оставляем competitors пустым списком
    
    # Формируем ответ из динамически собранных данных
    return ReportResponse(
        id=str(report.id),
        query=report.query,
        status=report.status.value,
        company_id=str(report.company_id) if report.company_id else None,
        company=company,
        categories=categories if categories else None,
        news=news_items if news_items else None,
        sources=sources if sources else None,
        pricing=pricing_info.dict() if pricing_info else None,
        competitors=[c.dict() for c in competitors] if competitors else None,
        created_at=report.created_at.isoformat(),
        completed_at=report.completed_at.isoformat() if report.completed_at else None
    )


@router.get("/", response_model=ReportsListResponse)
async def get_reports(
    limit: int = Query(20, ge=1, le=100, description="Number of reports to return"),
    offset: int = Query(0, ge=0, description="Number of reports to skip"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get list of user's reports with pagination.
    
    Response: {
        "items": [...],
        "total": 10,
        "limit": 10,
        "offset": 0
    }
    """
    try:
        report_repo = ReportRepository(db)
        
        # Get reports
        reports = await report_repo.get_by_user(
            str(current_user.id),
            limit=limit,
            offset=offset
        )
        
        # Get total count
        result = await db.execute(
            select(func.count(Report.id)).where(Report.user_id == current_user.id)
        )
        total = result.scalar_one() or 0
        
        # Format response - только базовые поля для списка
        items = []
        for report in reports:
            try:
                # Безопасная обработка полей отчёта
                status_value = report.status.value if hasattr(report.status, 'value') else str(report.status)
                created_at_str = report.created_at.isoformat() if report.created_at else datetime.now(timezone.utc).isoformat()
                completed_at_str = report.completed_at.isoformat() if report.completed_at else None
                company_id_str = str(report.company_id) if report.company_id else None
                
                items.append(ReportResponse(
                    id=str(report.id),
                    query=report.query or "",
                    status=status_value,
                    company_id=company_id_str,
                    company=None,  # Не загружаем полные данные в списке
                    categories=None,
                    news=None,
                    sources=None,
                    pricing=None,
                    competitors=None,
                    created_at=created_at_str,
                    completed_at=completed_at_str
                ))
            except Exception as e:
                logger.warning(f"Failed to format report {report.id}: {e}", exc_info=True)
                # Пропускаем проблемный отчёт, но продолжаем обработку остальных
                continue
        
        return ReportsListResponse(
            items=items,
            total=total,
            limit=limit,
            offset=offset
        )
    except Exception as e:
        logger.error(f"Failed to get reports for user {current_user.id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get reports: {str(e)}")


@router.delete("/{report_id}", status_code=204)
async def delete_report(
    report_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a report.
    
    Returns 204 No Content on success.
    """
    try:
        report_uuid = UUID(report_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid report ID format")
    
    report_repo = ReportRepository(db)
    report = await report_repo.get_by_id(report_uuid)
    
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    
    # Check ownership
    if report.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    try:
        await db.delete(report)
        await db.commit()
        logger.info(f"Report {report_id} deleted by user {current_user.id}")
        return Response(status_code=204)
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to delete report {report_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to delete report: {str(e)}")

