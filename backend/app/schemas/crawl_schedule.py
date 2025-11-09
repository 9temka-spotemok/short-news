"""
Pydantic schemas for crawl schedule management.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field, validator

from app.models import CrawlMode, CrawlScope


class CrawlScheduleBase(BaseModel):
    """Shared fields for crawl schedule operations."""

    mode: CrawlMode = Field(default=CrawlMode.ALWAYS_UPDATE, description="Crawl behaviour mode")
    frequency_seconds: int = Field(default=900, ge=60, le=24 * 60 * 60, description="Frequency in seconds")
    jitter_seconds: int = Field(default=300, ge=0, le=12 * 60 * 60, description="Jitter applied to schedule")
    max_retries: int = Field(default=3, ge=0, le=10, description="Maximum retry attempts")
    retry_backoff_seconds: int = Field(default=60, ge=0, le=60 * 60, description="Backoff delay for retries")
    enabled: bool = Field(default=True, description="Whether schedule is active")
    priority: int = Field(default=0, ge=-10, le=10, description="Scheduling priority")
    metadata: dict = Field(default_factory=dict, description="Additional schedule metadata")


class CrawlScheduleUpdateRequest(CrawlScheduleBase):
    """Request payload for creating/updating crawl schedules."""

    run_window_start: Optional[datetime] = Field(
        default=None,
        description="Optional UTC start time constraint",
    )
    run_window_end: Optional[datetime] = Field(
        default=None,
        description="Optional UTC end time constraint",
    )

    @validator("run_window_end")
    def validate_run_window(cls, value, values):
        start = values.get("run_window_start")
        if value and start and value <= start:
            raise ValueError("run_window_end must be greater than run_window_start")
        return value


class CrawlScheduleResponse(CrawlScheduleBase):
    """Response schema for crawl schedules."""

    id: UUID
    scope: CrawlScope
    scope_value: str
    run_window_start: Optional[datetime]
    run_window_end: Optional[datetime]
    last_applied_at: Optional[datetime]

    class Config:
        from_attributes = True


