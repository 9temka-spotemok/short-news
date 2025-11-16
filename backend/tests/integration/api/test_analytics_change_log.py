import pytest
from datetime import datetime, timedelta, timezone

from app.models import SourceType
from tests.utils.analytics_builders import create_change_event, create_company


@pytest.mark.asyncio
async def test_change_log_pagination(async_client, async_session):
    company = await create_company(async_session, name="CursorTech")
    now = datetime.now(timezone.utc)

    # Create three events in descending order
    for offset in range(3):
        await create_change_event(
            async_session,
            company_id=company.id,
            detected_at=now - timedelta(minutes=offset),
            summary=f"Change #{offset}",
        )

    params = {
        "company_id": str(company.id),
        "limit": 2,
        "source_types": [SourceType.NEWS_SITE.value],
    }

    response = await async_client.get("/api/v2/analytics/change-log", params=params)
    assert response.status_code == 200

    payload = response.json()
    assert payload["total"] == 3
    assert len(payload["events"]) == 2
    assert payload["events"][0]["change_summary"] == "Change #0"
    assert payload["next_cursor"] is not None

    next_response = await async_client.get(
        "/api/v2/analytics/change-log",
        params={
            "company_id": str(company.id),
            "limit": 2,
            "cursor": payload["next_cursor"],
        },
    )
    assert next_response.status_code == 200

    next_payload = next_response.json()
    assert next_payload["total"] == 3
    assert len(next_payload["events"]) == 1
    assert next_payload["events"][0]["change_summary"] == "Change #2"
    assert next_payload["next_cursor"] is None


