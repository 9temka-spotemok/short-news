from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User
from app.models.analytics import AnalyticsPeriod, RelationshipType
from tests.utils.analytics_builders import (
    create_change_event,
    create_company,
    create_graph_edge,
    create_news_item,
    create_snapshot,
    create_user_preferences,
    create_report_preset,
)
from app.models.preferences import NotificationFrequency, DigestFrequency, DigestFormat
from app.models.news import NewsCategory, SentimentLabel, NewsTopic


def _subject_key(company_id) -> str:
    return f"company:{company_id}"


@pytest.mark.asyncio
async def test_build_comparison_overview(
    async_client: AsyncClient,
    async_session: AsyncSession,
) -> None:
    company = await create_company(async_session, name="SignalAI")
    company_id = company.id
    now = datetime.now(timezone.utc).replace(microsecond=0)

    await create_news_item(
        async_session,
        company_id=company_id,
        title="Launches analytics dashboard",
        category=NewsCategory.TECHNICAL_UPDATE,
        sentiment=SentimentLabel.NEUTRAL,
        topic=NewsTopic.TECHNOLOGY,
        published_at=now - timedelta(days=1),
    )
    await create_news_item(
        async_session,
        company_id=company_id,
        title="Raises funding",
        published_at=now - timedelta(days=2),
    )
    await create_snapshot(async_session, company_id=company_id, period_start=now - timedelta(days=3))
    await create_change_event(async_session, company_id=company_id, detected_at=now - timedelta(days=2))
    await create_graph_edge(async_session, company_id=company_id, relationship_type=RelationshipType.CAUSES)

    payload = {
        "subjects": [
            {
                "subject_type": "company",
                "reference_id": str(company_id),
                "label": "SignalAI",
            }
        ],
        "period": AnalyticsPeriod.DAILY.value,
        "lookback": 7,
        "include_series": True,
        "include_change_log": True,
        "include_knowledge_graph": True,
    }

    response = await async_client.post("/api/v2/analytics/comparisons", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert data["subjects"]
    assert data["metrics"]

    subject = data["subjects"][0]
    assert subject["subject_id"] == str(company_id)
    assert subject["company_ids"] == [str(company_id)]

    metrics = data["metrics"][0]
    assert metrics["subject_id"] == str(company_id)
    assert metrics["news_volume"] >= 2
    assert metrics["top_news"], "top_news should reflect ingested news items"

    subject_key = _subject_key(company_id)
    assert subject_key in data["change_log"]
    assert data["change_log"][subject_key]

    series_entry = next((entry for entry in data["series"] if entry["subject_key"] == subject_key), None)
    assert series_entry is not None
    assert series_entry["snapshots"], "impact series should not be empty"

    assert subject_key in data["knowledge_graph"]
    edge = data["knowledge_graph"][subject_key][0]
    assert edge["relationship_type"] == RelationshipType.CAUSES.value


@pytest.mark.asyncio
async def test_build_export_payload(
    async_client: AsyncClient,
    async_session: AsyncSession,
) -> None:
    company = await create_company(async_session, name="InsightAI")
    company_id = company.id
    now = datetime.now(timezone.utc).replace(microsecond=0)
    await create_news_item(
        async_session,
        company_id=company_id,
        title="Releases new API",
        published_at=now - timedelta(days=2),
    )
    await create_snapshot(async_session, company_id=company_id, period_start=now - timedelta(days=1))
    await create_change_event(async_session, company_id=company_id, detected_at=now - timedelta(days=1))

    user_result = await async_session.execute(select(User).order_by(User.created_at.desc()))
    user = user_result.scalars().first()
    assert user is not None, "Test user should exist in session"
    user_id = str(user.id)

    await create_user_preferences(
        async_session,
        user_id=user.id,
        subscribed_companies=[company_id],
        keywords=["ai", "analytics"],
        notification_frequency=NotificationFrequency.WEEKLY,
        digest_enabled=True,
        digest_frequency=DigestFrequency.WEEKLY,
        digest_format=DigestFormat.DETAILED,
    )
    await create_report_preset(
        async_session,
        user_id=user.id,
        companies=[company.id],
        name="Insight Comparison",
        filters={"topics": ["product"]},
        is_favorite=True,
    )

    payload = {
        "subjects": [
            {
                "subject_type": "company",
                "reference_id": str(company_id),
                "label": "InsightAI",
            }
        ],
        "period": AnalyticsPeriod.DAILY.value,
        "lookback": 7,
        "include_series": True,
        "include_change_log": True,
        "include_knowledge_graph": False,
        "include": {
            "include_notifications": True,
            "include_presets": True,
        },
        "export_format": "json",
    }

    response = await async_client.post("/api/v2/analytics/export", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert data["export_format"] == "json"
    subject = data["comparison"]["subjects"][0]
    assert subject["subject_id"] == str(company_id)

    notification_settings = data["notification_settings"]
    assert notification_settings is not None
    assert notification_settings["digest_enabled"] is True
    assert str(company_id) in notification_settings["subscribed_companies"]

    presets = data["presets"]
    assert presets and presets[0]["name"] == "Insight Comparison"
    preset_user_id = presets[0]["user_id"]
    assert preset_user_id == user_id or preset_user_id == {"id": user_id}

