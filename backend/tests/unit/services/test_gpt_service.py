"""
Unit tests for GPTService
"""

from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from app.services.gpt_service import GPTService


@pytest.fixture
def gpt_service():
    """Create GPTService instance for testing"""
    return GPTService()


@pytest.fixture
def mock_openai_client():
    """Mock OpenAI client"""
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "Test description"
    mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
    return mock_client


@pytest.mark.asyncio
async def test_generate_company_description_with_gpt(gpt_service, mock_openai_client):
    """Test company description generation with GPT"""
    gpt_service.client = mock_openai_client
    
    company_data = {
        "name": "Test Company",
        "website": "https://test.com",
        "category": "SaaS",
        "meta_description": "Test meta description"
    }
    
    description = await gpt_service.generate_company_description(company_data)
    
    assert description == "Test description"
    assert mock_openai_client.chat.completions.create.called
    call_args = mock_openai_client.chat.completions.create.call_args
    assert call_args.kwargs["model"] == gpt_service.model
    assert "messages" in call_args.kwargs


@pytest.mark.asyncio
async def test_generate_company_description_fallback_no_client(gpt_service):
    """Test company description fallback when client is not available"""
    gpt_service.client = None
    
    company_data = {
        "name": "Test Company",
        "website": "https://test.com",
        "category": "SaaS"
    }
    
    description = await gpt_service.generate_company_description(company_data)
    
    assert "Test Company" in description
    assert isinstance(description, str)
    assert len(description) > 0


@pytest.mark.asyncio
async def test_generate_company_description_fallback_on_error(gpt_service, mock_openai_client):
    """Test company description fallback when GPT API fails"""
    mock_openai_client.chat.completions.create = AsyncMock(side_effect=Exception("API Error"))
    gpt_service.client = mock_openai_client
    
    company_data = {
        "name": "Test Company",
        "website": "https://test.com",
        "category": "SaaS"
    }
    
    description = await gpt_service.generate_company_description(company_data)
    
    # Should return fallback description
    assert "Test Company" in description
    assert isinstance(description, str)


@pytest.mark.asyncio
async def test_generate_company_description_uses_meta_description(gpt_service):
    """Test that fallback uses meta_description when available"""
    gpt_service.client = None
    
    company_data = {
        "name": "Test Company",
        "meta_description": "This is a long meta description that should be used as fallback"
    }
    
    description = await gpt_service.generate_company_description(company_data)
    
    assert "This is a long meta description" in description


@pytest.mark.asyncio
async def test_generate_competitor_description_with_gpt(gpt_service, mock_openai_client):
    """Test competitor description generation with GPT"""
    gpt_service.client = mock_openai_client
    
    competitor_data = {
        "name": "Competitor Inc",
        "website": "https://competitor.com",
        "category": "SaaS"
    }
    
    description = await gpt_service.generate_competitor_description(
        competitor_data, 
        "Parent Company"
    )
    
    assert description == "Test description"
    assert mock_openai_client.chat.completions.create.called
    call_args = mock_openai_client.chat.completions.create.call_args
    assert "Parent Company" in str(call_args.kwargs["messages"])


@pytest.mark.asyncio
async def test_generate_competitor_description_fallback_no_client(gpt_service):
    """Test competitor description fallback when client is not available"""
    gpt_service.client = None
    
    competitor_data = {
        "name": "Competitor Inc",
        "website": "https://competitor.com",
        "category": "SaaS"
    }
    
    description = await gpt_service.generate_competitor_description(
        competitor_data,
        "Parent Company"
    )
    
    assert "Competitor Inc" in description
    assert "Parent Company" in description
    assert isinstance(description, str)


@pytest.mark.asyncio
async def test_suggest_industry_signals_with_gpt(gpt_service, mock_openai_client):
    """Test industry signals suggestion with GPT"""
    # Mock response with signals
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "SaaS\nB2B\necommerce"
    mock_openai_client.chat.completions.create = AsyncMock(return_value=mock_response)
    gpt_service.client = mock_openai_client
    
    company_data = {
        "name": "Test Company",
        "website": "https://test.com",
        "category": "SaaS"
    }
    
    signals = await gpt_service.suggest_industry_signals(company_data)
    
    assert isinstance(signals, list)
    assert len(signals) > 0
    assert "SaaS" in signals or "saas" in [s.lower() for s in signals]


@pytest.mark.asyncio
async def test_suggest_industry_signals_fallback_no_client(gpt_service):
    """Test industry signals fallback when client is not available"""
    gpt_service.client = None
    
    company_data = {
        "name": "Test SaaS Company",
        "category": "SaaS"
    }
    
    signals = await gpt_service.suggest_industry_signals(company_data)
    
    assert isinstance(signals, list)
    assert len(signals) > 0
    assert len(signals) <= 5


@pytest.mark.asyncio
async def test_suggest_industry_signals_heuristic_detection(gpt_service):
    """Test heuristic detection of industry signals"""
    gpt_service.client = None
    
    # Test SaaS detection
    company_data = {"name": "Cloud Software Inc", "category": "Technology"}
    signals = await gpt_service.suggest_industry_signals(company_data)
    assert len(signals) > 0
    
    # Test retail detection
    company_data = {"name": "Online Store", "category": "Retail"}
    signals = await gpt_service.suggest_industry_signals(company_data)
    assert len(signals) > 0


@pytest.mark.asyncio
async def test_generate_company_description_short_response_fallback(gpt_service, mock_openai_client):
    """Test fallback when GPT returns too short description"""
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "Short"  # Too short
    mock_openai_client.chat.completions.create = AsyncMock(return_value=mock_response)
    gpt_service.client = mock_openai_client
    
    company_data = {
        "name": "Test Company",
        "website": "https://test.com"
    }
    
    description = await gpt_service.generate_company_description(company_data)
    
    # Should use fallback
    assert "Test Company" in description
    assert len(description) > 10


@pytest.mark.asyncio
async def test_suggest_industry_signals_parsing(gpt_service, mock_openai_client):
    """Test parsing of industry signals from GPT response"""
    # Test with newline-separated signals
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "SaaS\nB2B\necommerce\n# Comment line"
    mock_openai_client.chat.completions.create = AsyncMock(return_value=mock_response)
    gpt_service.client = mock_openai_client
    
    company_data = {"name": "Test Company"}
    signals = await gpt_service.suggest_industry_signals(company_data)
    
    assert isinstance(signals, list)
    assert len(signals) <= 5
    # Comment lines should be filtered out
    assert not any("#" in s for s in signals)













