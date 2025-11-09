from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import Field

from app.models import (
    ChangeNotificationStatus,
    ChangeProcessingStatus,
    SourceType,
)
from app.models.base import BaseSchema


class SnapshotReferenceSchema(BaseSchema):
    id: Optional[UUID]
    parser_version: Optional[str]
    raw_snapshot_url: Optional[str]
    extraction_metadata: Dict[str, Any] = Field(default_factory=dict)
    warnings: List[str] = Field(default_factory=list)
    processing_status: ChangeProcessingStatus


class CompetitorChangeEventSchema(BaseSchema):
    id: UUID
    company_id: UUID
    source_type: SourceType
    change_summary: str
    changed_fields: List[Dict[str, Any]] = Field(default_factory=list)
    raw_diff: Dict[str, Any] = Field(default_factory=dict)
    detected_at: datetime
    processing_status: ChangeProcessingStatus
    notification_status: ChangeNotificationStatus
    current_snapshot: Optional[SnapshotReferenceSchema] = None
    previous_snapshot: Optional[SnapshotReferenceSchema] = None

