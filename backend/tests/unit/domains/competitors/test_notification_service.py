from __future__ import annotations

from datetime import datetime, timezone
from typing import Callable
from uuid import uuid4

import pytest
from sqlalchemy import delete, select

from app.domains.competitors.services.notification_service import (
    CompetitorNotificationService,
)
from app.models import (
    ChangeNotificationStatus,
    ChangeProcessingStatus,
    Company,
    CompetitorChangeEvent,
)
from app.models.notification_channels import (
    NotificationChannel,
    NotificationChannelType,
    NotificationEvent,
    NotificationPriority,
    NotificationSubscription,
    NotificationType,
)
from app.models.notifications import NotificationSettings
from app.models.preferences import UserPreferences
from app.models.user import User
from app.models.news import SourceType


@pytest.mark.asyncio
async def test_dispatch_change_event_creates_notification_event(async_session):
    company, user = await _setup_company_and_user(async_session)
    await _enable_notifications(async_session, user, company)

    event = CompetitorChangeEvent(
        company_id=company.id,
        source_type=SourceType.NEWS_SITE,
        change_summary="Price increased",
        changed_fields=[{"plan": "Pro", "field": "price", "previous": 49, "current": 59}],
        raw_diff={"updated_plans": [{"plan": "Pro"}]},
        detected_at=datetime.now(timezone.utc),
        processing_status=ChangeProcessingStatus.SUCCESS,
        notification_status=ChangeNotificationStatus.PENDING,
    )
    async_session.add(event)
    await async_session.commit()
    await async_session.refresh(event)

    service = CompetitorNotificationService(async_session)
    dispatched = await service.dispatch_change_event(event)

    await async_session.refresh(event)
    assert dispatched == 1
    assert event.notification_status == ChangeNotificationStatus.SENT

    result = await async_session.execute(select(NotificationEvent))
    events = result.scalars().all()
    assert len(events) == 1
    notification_event = events[0]
    assert notification_event.user_id == user.id
    assert notification_event.notification_type == NotificationType.PRICING_CHANGE
    assert notification_event.payload["company_id"] == str(company.id)
    assert notification_event.payload["event_id"] == str(event.id)


@pytest.mark.asyncio
async def test_dispatch_change_event_skips_without_watchers(async_session):
    company, _ = await _setup_company_and_user(async_session)

    event = CompetitorChangeEvent(
        company_id=company.id,
        source_type=SourceType.NEWS_SITE,
        change_summary="No watchers",
        changed_fields=[{"plan": "Starter", "field": "storage", "previous": "10GB", "current": "20GB"}],
        raw_diff={"updated_plans": [{"plan": "Starter"}]},
        detected_at=datetime.now(timezone.utc),
        processing_status=ChangeProcessingStatus.SUCCESS,
        notification_status=ChangeNotificationStatus.PENDING,
    )
    async_session.add(event)
    await async_session.commit()
    await async_session.refresh(event)

    service = CompetitorNotificationService(async_session)
    dispatched = await service.dispatch_change_event(event)

    await async_session.refresh(event)
    assert dispatched == 0
    assert event.notification_status == ChangeNotificationStatus.SKIPPED

    result = await async_session.execute(select(NotificationEvent))
    assert result.scalars().all() == []


async def _setup_company_and_user(async_session):
    # Ensure clean slate between tests to avoid cross-test subscriptions.
    for model in (
        NotificationEvent,
        NotificationSubscription,
        NotificationChannel,
        NotificationSettings,
        UserPreferences,
        Company,
        User,
    ):
        await async_session.execute(delete(model))
    await async_session.commit()

    company = Company(name=f"Acme Analytics {uuid4()}", website="https://acme.example")
    user = User(
        email=f"watcher-{uuid4()}@example.com",
        password_hash="not-used",
        is_active=True,
        is_verified=True,
    )
    async_session.add_all([company, user])
    await async_session.commit()
    await async_session.refresh(company)
    await async_session.refresh(user)
    return company, user


async def _enable_notifications(async_session, user: User, company: Company) -> None:
    settings = NotificationSettings(
        user_id=user.id,
        enabled=True,
        notification_types={NotificationType.PRICING_CHANGE.value: True},
    )
    preferences = UserPreferences(
        user_id=user.id,
        subscribed_companies=[company.id],
        interested_categories=[],
        keywords=[],
    )
    channel = NotificationChannel(
        user_id=user.id,
        channel_type=NotificationChannelType.EMAIL,
        destination=user.email,
        metadata_json={},
        is_verified=True,
    )
    async_session.add_all([settings, preferences, channel])
    await async_session.commit()
    await async_session.refresh(channel)

    subscription = NotificationSubscription(
        user_id=user.id,
        channel_id=channel.id,
        notification_type=NotificationType.PRICING_CHANGE,
        enabled=True,
        min_priority=NotificationPriority.MEDIUM,
        filters={},
    )
    async_session.add(subscription)
    await async_session.commit()


