from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional, Sequence
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    ChangeNotificationStatus,
    ChangeProcessingStatus,
    Company,
    CompetitorChangeEvent,
    NewsItem,
)
from app.models.analytics import (
    AnalyticsPeriod,
    CompanyAnalyticsSnapshot,
    ImpactComponent,
    ImpactComponentType,
    AnalyticsGraphEdge,
    AnalyticsEntityType,
    RelationshipType,
    UserReportPreset,
)
from app.models.news import NewsCategory, NewsTopic, SentimentLabel, SourceType
from app.models.preferences import (
    UserPreferences,
    NotificationFrequency,
    DigestFrequency,
    DigestFormat,
)


async def create_company(
    session: AsyncSession,
    *,
    name: str = "Acme Analytics",
    website: str = "https://example.com",
) -> Company:
    unique_suffix = uuid4().hex[:8]
    company = Company(name=f"{name}-{unique_suffix}", website=f"{website.rstrip('/')}/{unique_suffix}")
    session.add(company)
    await session.commit()
    await session.refresh(company)
    return company


async def create_news_item(
    session: AsyncSession,
    *,
    company_id: UUID,
    title: str,
    summary: str = "Summary",
    content: str = "Content",
    source_url: Optional[str] = None,
    source_type: SourceType = SourceType.BLOG,
    category: NewsCategory = NewsCategory.PRODUCT_UPDATE,
    sentiment: SentimentLabel = SentimentLabel.POSITIVE,
    topic: Optional[NewsTopic] = NewsTopic.PRODUCT,
    priority_score: float = 0.8,
    published_at: Optional[datetime] = None,
) -> NewsItem:
    news = NewsItem(
        title=title,
        summary=summary,
        content=content,
        source_url=source_url or f"https://example.com/{title.replace(' ', '-').lower()}",
        source_type=source_type,
        category=category,
        sentiment=sentiment,
        topic=topic,
        priority_score=priority_score,
        company_id=company_id,
        published_at=published_at or datetime.now(timezone.utc),
    )
    session.add(news)
    await session.commit()
    await session.refresh(news)
    return news


async def create_change_event(
    session: AsyncSession,
    *,
    company_id: UUID,
    detected_at: Optional[datetime] = None,
    summary: str = "Price increased",
) -> CompetitorChangeEvent:
    event = CompetitorChangeEvent(
        company_id=company_id,
        source_type=SourceType.NEWS_SITE,
        change_summary=summary,
        changed_fields=[
            {
                "plan": "Pro",
                "field": "price",
                "previous": 49.0,
                "current": 59.0,
                "previous_currency": "USD",
                "current_currency": "USD",
            }
        ],
        raw_diff={"updated_plans": [{"plan": "Pro"}]},
        detected_at=detected_at or datetime.now(timezone.utc),
        processing_status=ChangeProcessingStatus.SUCCESS,
        notification_status=ChangeNotificationStatus.PENDING,
    )
    session.add(event)
    await session.commit()
    await session.refresh(event)
    return event


async def create_snapshot(
    session: AsyncSession,
    *,
    company_id: UUID,
    period_start: datetime,
    period: AnalyticsPeriod = AnalyticsPeriod.DAILY,
    impact_score: float = 4.2,
) -> CompanyAnalyticsSnapshot:
    snapshot = CompanyAnalyticsSnapshot(
        company_id=company_id,
        period_start=period_start,
        period_end=period_start + timedelta(days=1),
        period=period,
        news_total=3,
        news_positive=2,
        news_negative=0,
        news_neutral=1,
        news_average_sentiment=0.6,
        news_average_priority=0.75,
        pricing_changes=1,
        feature_updates=1,
        funding_events=0,
        impact_score=impact_score,
        innovation_velocity=1.1,
        trend_delta=0.5,
        metric_breakdown={"news_volume": 3},
    )
    session.add(snapshot)
    await session.flush()

    component = ImpactComponent(
        snapshot_id=snapshot.id,
        company_id=company_id,
        component_type=ImpactComponentType.NEWS_SIGNAL,
        weight=0.25,
        score_contribution=impact_score * 0.25,
        metadata_json={"details": "Generated via builder"},
    )
    session.add(component)
    await session.commit()
    await session.refresh(snapshot)
    return snapshot


async def create_graph_edge(
    session: AsyncSession,
    *,
    company_id: UUID,
    source_entity_type: AnalyticsEntityType = AnalyticsEntityType.COMPANY,
    target_entity_type: AnalyticsEntityType = AnalyticsEntityType.NEWS_ITEM,
    relationship_type: RelationshipType = RelationshipType.CORRELATED_WITH,
    source_entity_id: Optional[UUID] = None,
    target_entity_id: Optional[UUID] = None,
    confidence: float = 0.85,
    weight: float = 1.0,
) -> AnalyticsGraphEdge:
    edge = AnalyticsGraphEdge(
        company_id=company_id,
        source_entity_type=source_entity_type,
        source_entity_id=source_entity_id or uuid4(),
        target_entity_type=target_entity_type,
        target_entity_id=target_entity_id or uuid4(),
        relationship_type=relationship_type,
        confidence=confidence,
        weight=weight,
        metadata_json={"source": "builder"},
    )
    session.add(edge)
    await session.commit()
    await session.refresh(edge)
    return edge


async def create_user_preferences(
    session: AsyncSession,
    *,
    user_id: UUID,
    subscribed_companies: Optional[Sequence[UUID]] = None,
    interested_categories: Optional[Sequence[NewsCategory]] = None,
    keywords: Optional[Sequence[str]] = None,
    notification_frequency: NotificationFrequency = NotificationFrequency.DAILY,
    digest_enabled: bool = True,
    digest_frequency: DigestFrequency = DigestFrequency.WEEKLY,
    digest_format: DigestFormat = DigestFormat.SHORT,
    telegram_enabled: bool = False,
    timezone: str = "UTC",
    week_start_day: int = 1,
) -> UserPreferences:
    preferences = UserPreferences(
        user_id=user_id,
        subscribed_companies=list(subscribed_companies or []),
        interested_categories=list(interested_categories or []),
        keywords=list(keywords or []),
        notification_frequency=notification_frequency.value,
        digest_enabled=digest_enabled,
        digest_frequency=digest_frequency.value,
        digest_format=digest_format.value,
        digest_custom_schedule={"time": "09:00", "days": [1, 3, 5], "timezone": timezone},
        telegram_enabled=telegram_enabled,
        telegram_digest_mode="all",
        timezone=timezone,
        week_start_day=week_start_day,
    )
    session.add(preferences)
    await session.commit()
    await session.refresh(preferences)
    return preferences


async def create_report_preset(
    session: AsyncSession,
    *,
    user_id: UUID,
    companies: Optional[Sequence[UUID]] = None,
    name: str = "AI Weekly Digest",
    description: str = "Autogenerated preset for testing",
    filters: Optional[dict] = None,
    visualization_config: Optional[dict] = None,
    is_favorite: bool = False,
) -> UserReportPreset:
    preset = UserReportPreset(
        user_id=user_id,
        name=name,
        description=description,
        companies=list(companies or []),
        filters=filters or {"source_types": ["blog"]},
        visualization_config=visualization_config or {"default_chart": "impact"},
        is_favorite=is_favorite,
    )
    session.add(preset)
    await session.commit()
    await session.refresh(preset)
    return preset

