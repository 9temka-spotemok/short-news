import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import AsyncIterator

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.celery_app import celery_app
from app.main import app
from app.api.dependencies import get_current_user
from app.core.database import get_db
from app.models import (
    AnalyticsEntityType,
    AnalyticsGraphEdge,
    AnalyticsPeriod,
    Company,
    CompanyAnalyticsSnapshot,
    ImpactComponent,
    ImpactComponentType,
    NewsCategory,
    NewsItem,
    NewsTopic,
    RelationshipType,
    SentimentLabel,
    SourceType,
    User,
)
from app.models.base import BaseModel

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")

if not TEST_DATABASE_URL:
    pytest.skip("TEST_DATABASE_URL is required to run analytics integration tests", allow_module_level=True)

engine = create_async_engine(TEST_DATABASE_URL, future=True)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


@pytest.fixture(scope="session", autouse=True)
async def setup_database() -> AsyncIterator[None]:
    async with engine.begin() as connection:
        await connection.run_sync(BaseModel.metadata.create_all)
    yield
    async with engine.begin() as connection:
        await connection.run_sync(BaseModel.metadata.drop_all)


@pytest.fixture
async def session() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        yield session
        await session.rollback()


@pytest.fixture
async def seeded_context(session: AsyncSession) -> dict:
    primary_id = uuid.uuid4()
    competitor_id = uuid.uuid4()
    user_id = uuid.uuid4()

    user = User(
        id=user_id,
        email="analytics-tester@example.com",
        hashed_password="irrelevant",
        full_name="Analytics Tester",
        is_active=True,
    )
    primary_company = Company(
        id=primary_id,
        name="Analytics Test Primary",
        website="https://primary.example.com",
        category="ai_platform",
    )
    competitor_company = Company(
        id=competitor_id,
        name="Analytics Test Competitor",
        website="https://competitor.example.com",
        category="ai_platform",
    )

    now = datetime.now(timezone.utc)
    news_item = NewsItem(
        company_id=primary_id,
        title="Primary company launches new feature",
        source_url=f"https://primary.example.com/news/{uuid.uuid4()}",
        source_type=SourceType.BLOG,
        category=NewsCategory.PRODUCT_UPDATE,
        priority_score=0.8,
        topic=NewsTopic.PRODUCT,
        sentiment=SentimentLabel.POSITIVE,
        published_at=now - timedelta(days=2),
    )
    snapshot = CompanyAnalyticsSnapshot(
        company_id=primary_id,
        period_start=now - timedelta(days=7),
        period_end=now - timedelta(days=1),
        period=AnalyticsPeriod.DAILY,
        news_total=5,
        news_positive=3,
        news_negative=1,
        news_neutral=1,
        news_average_sentiment=0.65,
        news_average_priority=0.7,
        pricing_changes=1,
        feature_updates=2,
        funding_events=0,
        impact_score=68.5,
        innovation_velocity=42.3,
        trend_delta=0.12,
        metric_breakdown={"signals": 5},
    )
    component = ImpactComponent(
        snapshot=snapshot,
        company_id=primary_id,
        component_type=ImpactComponentType.NEWS_SIGNAL,
        weight=0.6,
        score_contribution=0.4,
        metadata_json={"pricing_changes": 1},
    )
    edge = AnalyticsGraphEdge(
        company_id=primary_id,
        source_entity_type=AnalyticsEntityType.COMPANY,
        source_entity_id=primary_id,
        target_entity_type=AnalyticsEntityType.NEWS_ITEM,
        target_entity_id=uuid.uuid4(),
        relationship_type=RelationshipType.CORRELATED_WITH,
        confidence=0.82,
        weight=1.0,
        metadata_json={"category": "product_update"},
    )

    session.add_all(
        [
            user,
            primary_company,
            competitor_company,
            news_item,
            snapshot,
            component,
            edge,
        ]
    )
    await session.commit()

    return {
        "user_id": user_id,
        "primary_company_id": primary_id,
        "competitor_id": competitor_id,
    }


@pytest.fixture
async def client(session: AsyncSession, seeded_context: dict) -> AsyncIterator[AsyncClient]:
    async def override_get_db() -> AsyncIterator[AsyncSession]:
        async with SessionLocal() as override_session:
            yield override_session

    async def override_current_user() -> User:
        result = await session.execute(select(User).where(User.id == seeded_context["user_id"]))
        user = result.scalar_one()
        return user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_current_user

    previous_eager = celery_app.conf.task_always_eager
    previous_propagate = celery_app.conf.task_eager_propagates
    celery_app.conf.task_always_eager = True
    celery_app.conf.task_eager_propagates = True
    try:
        async with AsyncClient(app=app, base_url="http://testserver") as async_client:
            yield async_client
    finally:
        celery_app.conf.task_always_eager = previous_eager
        celery_app.conf.task_eager_propagates = previous_propagate
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_trigger_recompute_returns_task_id(client: AsyncClient, seeded_context: dict) -> None:
    response = await client.post(
        f"/api/v2/analytics/companies/{seeded_context['primary_company_id']}/recompute",
        params={"period": "daily", "lookback": 30},
    )
    assert response.status_code == 202
    payload = response.json()
    assert payload["status"] == "queued"
    assert payload["task_id"]


@pytest.mark.asyncio
async def test_sync_graph_returns_task_id(client: AsyncClient, seeded_context: dict) -> None:
    now = datetime.now(timezone.utc)
    response = await client.post(
        f"/api/v2/analytics/companies/{seeded_context['primary_company_id']}/graph/sync",
        params={"period_start": now.isoformat(), "period": "daily"},
    )
    assert response.status_code == 202
    payload = response.json()
    assert payload["status"] == "queued"
    assert payload["task_id"]


@pytest.mark.asyncio
async def test_snapshots_endpoint_returns_payload(client: AsyncClient, seeded_context: dict) -> None:
    response = await client.get(
        f"/api/v2/analytics/companies/{seeded_context['primary_company_id']}/snapshots",
        params={"period": "daily", "limit": 10},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["company_id"] == str(seeded_context["primary_company_id"])
    assert payload["snapshots"]


@pytest.mark.asyncio
async def test_export_endpoint_builds_payload(client: AsyncClient, seeded_context: dict) -> None:
    response = await client.post(
        "/api/v2/analytics/export",
        json={
            "subjects": [
                {"subject_type": "company", "reference_id": str(seeded_context["primary_company_id"])},
                {"subject_type": "company", "reference_id": str(seeded_context["competitor_id"])},
            ],
            "period": "daily",
            "lookback": 30,
            "include_series": True,
            "export_format": "json",
            "include": {
                "include_notifications": False,
                "include_presets": False,
            },
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["comparison"]["subjects"]
    assert payload["timeframe"]["period"] == "daily"


@pytest.mark.asyncio
async def test_report_preset_flow(client: AsyncClient, seeded_context: dict) -> None:
    create_response = await client.post(
        "/api/v2/analytics/reports/presets",
        json={
            "name": "Regression preset",
            "companies": [
                str(seeded_context["primary_company_id"]),
                str(seeded_context["competitor_id"]),
            ],
            "filters": {"topics": ["product"]},
            "visualization_config": {"impact_panel": True},
            "is_favorite": True,
        },
    )
    assert create_response.status_code == 201

    list_response = await client.get("/api/v2/analytics/reports/presets")
    assert list_response.status_code == 200
    presets = list_response.json()
    assert any(preset["name"] == "Regression preset" for preset in presets)

