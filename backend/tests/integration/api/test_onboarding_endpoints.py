"""
Integration tests for onboarding API endpoints
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import uuid4

from app.models import OnboardingSession, OnboardingStep, Company


@pytest.mark.asyncio
async def test_start_onboarding(async_client: AsyncClient, async_session: AsyncSession) -> None:
    """Test starting a new onboarding session"""
    response = await async_client.post("/api/v1/onboarding/start")
    
    assert response.status_code == 200
    body = response.json()
    assert "session_token" in body
    assert "session_id" in body
    assert body["current_step"] == OnboardingStep.COMPANY_INPUT.value
    assert len(body["session_token"]) > 0


@pytest.mark.asyncio
async def test_start_onboarding_creates_session(async_client: AsyncClient, async_session: AsyncSession) -> None:
    """Test that starting onboarding creates a session in database"""
    response = await async_client.post("/api/v1/onboarding/start")
    assert response.status_code == 200
    
    body = response.json()
    session_token = body["session_token"]
    
    # Verify session exists in database
    from sqlalchemy import select
    result = await async_session.execute(
        select(OnboardingSession).where(
            OnboardingSession.session_token == session_token
        )
    )
    session = result.scalar_one_or_none()
    
    assert session is not None
    assert session.current_step == OnboardingStep.COMPANY_INPUT


@pytest.mark.asyncio
async def test_analyze_company_for_onboarding(async_client: AsyncClient, async_session: AsyncSession) -> None:
    """Test analyzing a company website for onboarding"""
    # Start onboarding session
    start_response = await async_client.post("/api/v1/onboarding/start")
    assert start_response.status_code == 200
    session_token = start_response.json()["session_token"]
    
    # Analyze company
    analyze_response = await async_client.post(
        "/api/v1/onboarding/company/analyze",
        json={
            "website_url": "https://example.com",
            "session_token": session_token
        }
    )
    
    assert analyze_response.status_code == 200
    body = analyze_response.json()
    assert "company" in body
    assert body["company"]["name"] is not None
    assert body["company"]["website"] is not None
    assert body["current_step"] == OnboardingStep.COMPANY_CARD.value


@pytest.mark.asyncio
async def test_analyze_company_invalid_url(async_client: AsyncClient, async_session: AsyncSession) -> None:
    """Test analyzing company with invalid URL"""
    start_response = await async_client.post("/api/v1/onboarding/start")
    session_token = start_response.json()["session_token"]
    
    response = await async_client.post(
        "/api/v1/onboarding/company/analyze",
        json={
            "website_url": "not-a-valid-url",
            "session_token": session_token
        }
    )
    
    # Should handle gracefully or return error
    assert response.status_code in [400, 422]


@pytest.mark.asyncio
async def test_get_onboarding_company(async_client: AsyncClient, async_session: AsyncSession) -> None:
    """Test getting company data from onboarding session"""
    # Start and analyze
    start_response = await async_client.post("/api/v1/onboarding/start")
    session_token = start_response.json()["session_token"]
    
    await async_client.post(
        "/api/v1/onboarding/company/analyze",
        json={
            "website_url": "https://example.com",
            "session_token": session_token
        }
    )
    
    # Get company data
    response = await async_client.get(
        "/api/v1/onboarding/company",
        params={"session_token": session_token}
    )
    
    assert response.status_code == 200
    body = response.json()
    assert "company" in body
    assert body["company"]["name"] is not None


@pytest.mark.asyncio
async def test_get_onboarding_company_no_session(async_client: AsyncClient) -> None:
    """Test getting company data with invalid session token"""
    response = await async_client.get(
        "/api/v1/onboarding/company",
        params={"session_token": "invalid-token"}
    )
    
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_suggest_competitors_for_onboarding(async_client: AsyncClient, async_session: AsyncSession) -> None:
    """Test suggesting competitors for onboarding"""
    # Start and analyze company
    start_response = await async_client.post("/api/v1/onboarding/start")
    session_token = start_response.json()["session_token"]
    
    await async_client.post(
        "/api/v1/onboarding/company/analyze",
        json={
            "website_url": "https://example.com",
            "session_token": session_token
        }
    )
    
    # Suggest competitors
    response = await async_client.get(
        "/api/v1/onboarding/competitors/suggest",
        params={"session_token": session_token, "limit": 10}
    )
    
    assert response.status_code == 200
    body = response.json()
    assert "competitors" in body
    assert isinstance(body["competitors"], list)
    assert len(body["competitors"]) <= 10


@pytest.mark.asyncio
async def test_replace_competitor_in_onboarding(async_client: AsyncClient, async_session: AsyncSession) -> None:
    """Test replacing a competitor in onboarding"""
    # Start and analyze
    start_response = await async_client.post("/api/v1/onboarding/start")
    session_token = start_response.json()["session_token"]
    
    await async_client.post(
        "/api/v1/onboarding/company/analyze",
        json={
            "website_url": "https://example.com",
            "session_token": session_token
        }
    )
    
    # Get initial competitors
    suggest_response = await async_client.get(
        "/api/v1/onboarding/competitors/suggest",
        params={"session_token": session_token, "limit": 1}
    )
    
    if suggest_response.status_code == 200 and len(suggest_response.json()["competitors"]) > 0:
        competitor_id = suggest_response.json()["competitors"][0]["company"]["id"]
        
        # Replace competitor
        replace_response = await async_client.post(
            "/api/v1/onboarding/competitors/replace",
            json={
                "session_token": session_token,
                "competitor_id_to_replace": competitor_id
            }
        )
        
        assert replace_response.status_code == 200
        body = replace_response.json()
        assert "company" in body
        assert body["company"]["id"] != competitor_id  # Should be different


@pytest.mark.asyncio
async def test_select_competitors_in_onboarding(async_client: AsyncClient, async_session: AsyncSession) -> None:
    """Test selecting competitors in onboarding"""
    # Start and analyze
    start_response = await async_client.post("/api/v1/onboarding/start")
    session_token = start_response.json()["session_token"]
    
    await async_client.post(
        "/api/v1/onboarding/company/analyze",
        json={
            "website_url": "https://example.com",
            "session_token": session_token
        }
    )
    
    # Get competitors
    suggest_response = await async_client.get(
        "/api/v1/onboarding/competitors/suggest",
        params={"session_token": session_token, "limit": 5}
    )
    
    if suggest_response.status_code == 200 and len(suggest_response.json()["competitors"]) > 0:
        competitor_ids = [
            c["company"]["id"] 
            for c in suggest_response.json()["competitors"][:2]  # Select first 2
        ]
        
        # Select competitors
        select_response = await async_client.post(
            "/api/v1/onboarding/competitors/select",
            json={
                "session_token": session_token,
                "selected_competitor_ids": competitor_ids
            }
        )
        
        assert select_response.status_code == 200
        body = select_response.json()
        assert body["status"] == "success"
        assert body["selected_count"] == len(competitor_ids)
        assert body["current_step"] == OnboardingStep.OBSERVATION_SETUP.value


@pytest.mark.asyncio
async def test_setup_observation(async_client: AsyncClient, async_session: AsyncSession) -> None:
    """Test setting up observation for competitors"""
    # Start, analyze, and select competitors
    start_response = await async_client.post("/api/v1/onboarding/start")
    session_token = start_response.json()["session_token"]
    
    await async_client.post(
        "/api/v1/onboarding/company/analyze",
        json={
            "website_url": "https://example.com",
            "session_token": session_token
        }
    )
    
    # Get and select competitors
    suggest_response = await async_client.get(
        "/api/v1/onboarding/competitors/suggest",
        params={"session_token": session_token, "limit": 2}
    )
    
    if suggest_response.status_code == 200 and len(suggest_response.json()["competitors"]) > 0:
        competitor_ids = [
            c["company"]["id"] 
            for c in suggest_response.json()["competitors"]
        ]
        
        await async_client.post(
            "/api/v1/onboarding/competitors/select",
            json={
                "session_token": session_token,
                "selected_competitor_ids": competitor_ids
            }
        )
        
        # Setup observation
        setup_response = await async_client.post(
            "/api/v1/onboarding/observation/setup",
            json={"session_token": session_token}
        )
        
        assert setup_response.status_code == 200
        body = setup_response.json()
        assert "task_id" in body
        assert "status" in body
        assert body["status"] == "processing"


@pytest.mark.asyncio
async def test_get_observation_status(async_client: AsyncClient, async_session: AsyncSession) -> None:
    """Test getting observation setup status"""
    # Setup observation first
    start_response = await async_client.post("/api/v1/onboarding/start")
    session_token = start_response.json()["session_token"]
    
    await async_client.post(
        "/api/v1/onboarding/company/analyze",
        json={
            "website_url": "https://example.com",
            "session_token": session_token
        }
    )
    
    suggest_response = await async_client.get(
        "/api/v1/onboarding/competitors/suggest",
        params={"session_token": session_token, "limit": 1}
    )
    
    if suggest_response.status_code == 200 and len(suggest_response.json()["competitors"]) > 0:
        competitor_ids = [
            c["company"]["id"] 
            for c in suggest_response.json()["competitors"]
        ]
        
        await async_client.post(
            "/api/v1/onboarding/competitors/select",
            json={
                "session_token": session_token,
                "selected_competitor_ids": competitor_ids
            }
        )
        
        setup_response = await async_client.post(
            "/api/v1/onboarding/observation/setup",
            json={"session_token": session_token}
        )
        
        task_id = setup_response.json()["task_id"]
        
        # Get status
        status_response = await async_client.get(
            "/api/v1/onboarding/observation/status",
            params={"task_id": task_id}
        )
        
        assert status_response.status_code == 200
        body = status_response.json()
        assert body["task_id"] == task_id
        assert "status" in body


@pytest.mark.asyncio
async def test_complete_onboarding(async_client: AsyncClient, async_session: AsyncSession) -> None:
    """Test completing onboarding"""
    # Go through full flow
    start_response = await async_client.post("/api/v1/onboarding/start")
    session_token = start_response.json()["session_token"]
    
    await async_client.post(
        "/api/v1/onboarding/company/analyze",
        json={
            "website_url": "https://example.com",
            "session_token": session_token
        }
    )
    
    suggest_response = await async_client.get(
        "/api/v1/onboarding/competitors/suggest",
        params={"session_token": session_token, "limit": 1}
    )
    
    if suggest_response.status_code == 200 and len(suggest_response.json()["competitors"]) > 0:
        competitor_ids = [
            c["company"]["id"] 
            for c in suggest_response.json()["competitors"]
        ]
        
        await async_client.post(
            "/api/v1/onboarding/competitors/select",
            json={
                "session_token": session_token,
                "selected_competitor_ids": competitor_ids
            }
        )
        
        await async_client.post(
            "/api/v1/onboarding/observation/setup",
            json={"session_token": session_token}
        )
        
        # Complete onboarding
        complete_response = await async_client.post(
            "/api/v1/onboarding/complete",
            json={"session_token": session_token}
        )
        
        assert complete_response.status_code == 200
        body = complete_response.json()
        assert body["status"] == "success"
        assert "company_id" in body
        assert "competitor_count" in body













