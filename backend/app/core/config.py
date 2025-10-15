"""
Application configuration using Pydantic Settings
"""

from typing import List, Optional, Union
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings"""
    
    # Application
    APP_NAME: str = "AI Competitor Insight Hub"
    VERSION: str = "0.1.0"
    ENVIRONMENT: str = Field(default="development", description="Environment: development, staging, production")
    DEBUG: bool = Field(default=True, description="Debug mode")
    
    @field_validator('DEBUG', mode='before')
    @classmethod
    def validate_debug(cls, v):
        """Validate DEBUG field to handle string inputs"""
        if isinstance(v, str):
            return v.lower() in ('true', '1', 'yes', 'on')
        return bool(v)
    
    # Security
    SECRET_KEY: str = Field(..., description="Secret key for JWT tokens")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=15, description="Access token expiration in minutes")
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=7, description="Refresh token expiration in days")
    
    # CORS
    ALLOWED_HOSTS: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:5173", "http://127.0.0.1:3000", "http://127.0.0.1:5173"],
        description="Allowed CORS origins"
    )
    
    # Database
    DATABASE_URL: str = Field(..., description="PostgreSQL database URL")
    
    # Redis
    REDIS_URL: str = Field(..., description="Redis URL for cache and queues")
    
    # OpenAI API
    OPENAI_API_KEY: Optional[str] = Field(default=None, description="OpenAI API key")
    OPENAI_MODEL: str = Field(default="gpt-4o-mini", description="OpenAI model for classification")
    
    # External APIs
    TWITTER_API_KEY: Optional[str] = Field(default=None, description="Twitter API key")
    TWITTER_API_SECRET: Optional[str] = Field(default=None, description="Twitter API secret")
    TWITTER_ACCESS_TOKEN: Optional[str] = Field(default=None, description="Twitter access token")
    TWITTER_ACCESS_TOKEN_SECRET: Optional[str] = Field(default=None, description="Twitter access token secret")
    
    GITHUB_TOKEN: Optional[str] = Field(default=None, description="GitHub API token")
    
    REDDIT_CLIENT_ID: Optional[str] = Field(default=None, description="Reddit API client ID")
    REDDIT_CLIENT_SECRET: Optional[str] = Field(default=None, description="Reddit API client secret")
    
    # Email
    SENDGRID_API_KEY: Optional[str] = Field(default=None, description="SendGrid API key")
    FROM_EMAIL: str = Field(default="noreply@shot-news.com", description="From email address")
    
    # Telegram
    TELEGRAM_BOT_TOKEN: Optional[str] = Field(default=None, description="Telegram bot token")
    TELEGRAM_CHANNEL_ID: Optional[str] = Field(default=None, description="Telegram channel ID for public digests")
    
    # Celery
    CELERY_BROKER_URL: str = Field(default="redis://localhost:6379/0", description="Celery broker URL")
    CELERY_RESULT_BACKEND: str = Field(default="redis://localhost:6379/0", description="Celery result backend URL")
    
    # Scraping
    SCRAPER_USER_AGENT: str = Field(
        default="shot-news-bot/1.0 (+https://shot-news.com/bot)",
        description="User agent for web scrapers"
    )
    SCRAPER_DELAY: float = Field(default=5.0, description="Delay between requests in seconds")
    SCRAPER_TIMEOUT: int = Field(default=30, description="Request timeout in seconds")
    
    # Rate Limiting
    RATE_LIMIT_REQUESTS: int = Field(default=100, description="Rate limit requests per minute")
    
    # Logging
    LOG_LEVEL: str = Field(default="INFO", description="Log level")
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# Create settings instance
settings = Settings()
