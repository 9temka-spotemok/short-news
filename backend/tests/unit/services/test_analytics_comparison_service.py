from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import uuid4, UUID

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.analytics import (
    ComparisonRequest,
    ComparisonSubjectRequest,
    AnalyticsExportRequest,
    ExportIncludeOptions,
    ComparisonFilters,
)
from app.services.analytics_comparison_service import AnalyticsComparisonService
from app.services.analytics_service import AnalyticsService
from app.services.competitor_service import CompetitorAnalysisService
from app.services.competitor_change_service import CompetitorChangeService
from app.models import User, UserReportPreset


class DummyUser(User):
    """Lightweight substitute for current user fixture."""

    def __init__(self, email: Optional[str] = None) -> None:
        super().__init__(
            email=email or f"analytics-user-{uuid4()}@example.com",
            password_hash="unused",
            is_active=True,
        )


@pytest.mark.asyncio
async def test_build_comparison_basic(monkeypatch, async_session: AsyncSession) -> None:
    service = AnalyticsComparisonService(async_session)
    user = DummyUser()
    async_session.add(user)
    await async_session.commit()
    await async_session.refresh(user)

    company_id = uuid4()
    period = "daily"

    async def fake_get_snapshots(self, company_id: UUID, period: str, lookback: int):
        return []

    async def fake_build_company_metrics(*args, **kwargs):
        return {
            "news_volume": 3,
            "category_distribution": {"product_update": 3},
            "topic_distribution": {"product": 3},
            "sentiment_distribution": {"positive": 2, "neutral": 1},
            "activity_score": 4.5,
            "avg_priority": 0.7,
            "daily_activity": {},
            "top_news": [],
        }

    async def fake_load_change_events(*args, **kwargs):
        return []

    async def fake_load_graph_edges(*args, **kwargs):
        return []

    monkeypatch.setattr(AnalyticsService, "get_snapshots", fake_get_snapshots)
    monkeypatch.setattr(AnalyticsComparisonService, "_load_metrics_for_subject", fake_build_company_metrics)
    async def fake_load_company_map(*args, **kwargs):
        return {}

    monkeypatch.setattr(AnalyticsComparisonService, "_load_change_events", fake_load_change_events)
    monkeypatch.setattr(AnalyticsComparisonService, "_load_graph_edges", fake_load_graph_edges)
    monkeypatch.setattr(AnalyticsComparisonService, "_load_company_map", fake_load_company_map)

    request = ComparisonRequest(
        subjects=[
            ComparisonSubjectRequest(
                subject_type="company",
                reference_id=company_id,
                label="Company A",
            )
        ],
        period=period,
        lookback=30,
        filters=ComparisonFilters(),
        include_series=True,
        include_change_log=False,
        include_knowledge_graph=False,
    )

    response = await service.build_comparison(request, user=user)

    assert response.subjects, "subject summaries should be present"
    assert response.metrics, "metric summaries should be present"
    assert response.period == period


@pytest.mark.asyncio
async def test_build_export_payload(monkeypatch, async_session: AsyncSession) -> None:
    service = AnalyticsComparisonService(async_session)
    user = DummyUser()
    async_session.add(user)
    await async_session.commit()
    await async_session.refresh(user)

    comparison_response = await service.build_comparison(
        ComparisonRequest(
            subjects=[
                ComparisonSubjectRequest(
                    subject_type="company",
                    reference_id=uuid4(),
                    label="Company",
                )
            ],
            period="daily",
            lookback=7,
            filters=ComparisonFilters(),
        ),
        user=user,
    )

    async def fake_build_comparison(*args, **kwargs):
        return comparison_response

    async def fake_notification_settings(user_id: UUID):
        return None

    async def fake_load_presets(user_id: UUID):
        return []

    monkeypatch.setattr(AnalyticsComparisonService, "build_comparison", fake_build_comparison)
    monkeypatch.setattr(AnalyticsComparisonService, "_load_notification_settings", fake_notification_settings)
    monkeypatch.setattr(AnalyticsComparisonService, "_load_user_presets", fake_load_presets)

    export_payload = await service.build_export_payload(
        AnalyticsExportRequest(
            period="daily",
            lookback=7,
            subjects=[
                ComparisonSubjectRequest(
                    subject_type="company",
                    reference_id=uuid4(),
                    label="Company",
                )
            ],
            include=ExportIncludeOptions(
                include_notifications=False,
                include_presets=False,
            ),
            export_format="json",
        ),
        user=user,
    )

    assert export_payload.version.startswith("2.")
    assert export_payload.comparison.period == "daily"
    assert export_payload.export_format == "json"



