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
    ALLOWED_ORIGIN_REGEX: Optional[str] = Field(default=None, description="Regex for allowed CORS origins (e.g., https://.*\\.netlify\\.app)")
    
    @field_validator('ALLOWED_HOSTS', mode='before')
    @classmethod
    def validate_allowed_hosts(cls, v):
        """Validate ALLOWED_HOSTS field to handle JSON string inputs"""
        if isinstance(v, str):
            try:
                import json
                return json.loads(v)
            except json.JSONDecodeError:
                # If not JSON, treat as comma-separated string
                return [host.strip() for host in v.split(',')]
        return v
    
    @field_validator(
        'SCRAPER_HEADLESS_ENABLED',
        'SCRAPER_SNAPSHOTS_ENABLED',
        'SCRAPER_DETAIL_ENRICHMENT_ENABLED',
        'ENABLE_ANALYTICS_V2',
        'ENABLE_KNOWLEDGE_GRAPH',
        'CELERY_METRICS_ENABLED',
        'CELERY_METRICS_EXPOSE_SERVER',
        'CELERY_OTEL_ENABLED',
        mode='before',
    )
    @classmethod
    def validate_bool_flags(cls, v):
        """Allow boolean flags to be passed as strings"""
        if isinstance(v, str):
            return v.lower() in ('true', '1', 'yes', 'on')
        return bool(v)

    @field_validator('CELERY_METRICS_DURATION_BUCKETS', mode='before')
    @classmethod
    def validate_metrics_buckets(cls, v):
        """Allow providing histogram buckets as comma-separated string."""
        if isinstance(v, str):
            return [float(item.strip()) for item in v.split(',') if item.strip()]
        return v
    
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
    
    # Frontend URLs for Telegram bot buttons
    FRONTEND_BASE_URL: str = Field(default="http://localhost:5173", description="Frontend base URL")
    FRONTEND_SETTINGS_URL: str = Field(default="http://localhost:5173/settings", description="Frontend settings URL")
    FRONTEND_DIGEST_SETTINGS_URL: str = Field(default="http://localhost:5173/settings/digest", description="Frontend digest settings URL")
    
    # Celery
    CELERY_BROKER_URL: str = Field(default="redis://localhost:6379/0", description="Celery broker URL")
    CELERY_RESULT_BACKEND: str = Field(default="redis://localhost:6379/0", description="Celery result backend URL")
    CELERY_DEDUP_TTL_SECONDS: int = Field(default=900, description="TTL for Celery task deduplication locks (seconds)")
    CELERY_METRICS_ENABLED: bool = Field(default=True, description="Enable Prometheus metrics for Celery workers")
    CELERY_METRICS_EXPOSE_SERVER: bool = Field(default=True, description="Expose embedded Prometheus HTTP server")
    CELERY_METRICS_HOST: str = Field(default="0.0.0.0", description="Host for Celery Prometheus exporter")
    CELERY_METRICS_PORT: int = Field(default=9464, description="Port for Celery Prometheus exporter")
    CELERY_METRICS_NAMESPACE: str = Field(default="shot_news", description="Prometheus namespace for Celery metrics")
    CELERY_METRICS_DURATION_BUCKETS: List[float] = Field(
        default_factory=lambda: [0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0],
        description="Histogram buckets for Celery task duration in seconds",
    )
    CELERY_OTEL_ENABLED: bool = Field(
        default=False,
        description="Forward Celery metrics via OpenTelemetry when configured",
    )
    
    # Feature flags
    ENABLE_ANALYTICS_V2: bool = Field(default=True, description="Expose API v2 analytics endpoints")
    ENABLE_KNOWLEDGE_GRAPH: bool = Field(default=True, description="Enable analytics knowledge graph processing")
    
    # Scraping
    SCRAPER_USER_AGENT: str = Field(
        default="shot-news-bot/1.0 (+https://shot-news.com/bot)",
        description="User agent for web scrapers"
    )
    SCRAPER_DELAY: float = Field(default=5.0, description="Delay between requests in seconds")
    SCRAPER_TIMEOUT: int = Field(default=30, description="Request timeout in seconds")
    SCRAPER_MAX_RETRIES: int = Field(default=3, description="Default number of retry attempts for scraper HTTP requests")
    SCRAPER_RETRY_BACKOFF: float = Field(default=1.5, description="Exponential backoff multiplier for scraper retries")
    SCRAPER_RATE_LIMIT_REQUESTS: int = Field(default=6, description="Requests allowed per host within rate limit window")
    SCRAPER_RATE_LIMIT_PERIOD: float = Field(default=60.0, description="Rate limit window in seconds for host throttling")
    SCRAPER_CONFIG_PATH: Optional[str] = Field(default=None, description="Path to YAML/JSON scraper configuration file")
    SCRAPER_HEADLESS_ENABLED: bool = Field(default=False, description="Enable headless browser fallback for protected sources")
    SCRAPER_PROXY_URL: Optional[str] = Field(default=None, description="HTTP proxy URL for scraper fallback requests")
    SCRAPER_SNAPSHOTS_ENABLED: bool = Field(default=True, description="Persist raw HTML snapshots for scraped pages")
    SCRAPER_SNAPSHOT_DIR: str = Field(default="storage/raw_snapshots", description="Directory to store raw HTML snapshots")
    SCRAPER_DETAIL_ENRICHMENT_ENABLED: bool = Field(
        default=True,
        description="Fetch article detail page during ingestion to enrich title/summary",
    )
    
    # Rate Limiting
    RATE_LIMIT_REQUESTS: int = Field(default=100, description="Rate limit requests per minute")
    
    # Subscription settings
    DISABLE_SUBSCRIPTION_CHECK: bool = Field(
        default=False,
        description="Disable subscription checks in development (allows unlimited access)"
    )
    SUBSCRIPTION_DEV_USERS: List[str] = Field(
        default_factory=lambda: [],
        description="List of email addresses that should have unlimited trial access (comma-separated or JSON array)"
    )
    
    @field_validator('SUBSCRIPTION_DEV_USERS', mode='before')
    @classmethod
    def validate_dev_users(cls, v):
        """Validate SUBSCRIPTION_DEV_USERS field to handle JSON string or comma-separated inputs"""
        if isinstance(v, str):
            try:
                import json
                return json.loads(v)
            except json.JSONDecodeError:
                # If not JSON, treat as comma-separated string
                return [email.strip() for email in v.split(',') if email.strip()]
        return v
    
    # Logging
    LOG_LEVEL: str = Field(default="INFO", description="Log level")
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# Create settings instance
settings = Settings()
