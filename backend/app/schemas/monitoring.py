from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class MonitoringChangeEventSchema(BaseModel):
    """Single monitoring change event."""

    id: UUID
    company_id: UUID
    change_type: str = Field(
        ...,
        description=(
            "High-level change type, typically mapped from raw_diff['type'] "
            "or source_type (e.g. website_structure, marketing_banner, pricing)."
        ),
    )
    change_summary: str = Field(..., description="Human-readable summary of the change.")
    detected_at: datetime = Field(..., description="Timestamp when change was detected.")
    details: Dict[str, Any] = Field(
        default_factory=dict,
        description="Raw diff payload with full change details.",
    )


class MonitoringChangesResponseSchema(BaseModel):
    """
    Response schema for monitoring changes endpoint.

    Example:
    ```json
    {
      "events": [
        {
          "id": "550e8400-e29b-41d4-a716-446655440000",
          "company_id": "660e8400-e29b-41d4-a716-446655440000",
          "change_type": "website_structure",
          "change_summary": "Navigation menu updated - added 'Products' link",
          "detected_at": "2025-01-27T10:30:00Z",
          "details": {
            "type": "website_structure",
            "navigation_changes": {
              "added": ["/products"],
              "removed": []
            }
          }
        }
      ],
      "total": 42,
      "has_more": false
    }
    ```
    """

    events: List[MonitoringChangeEventSchema]
    total: int = Field(..., description="Total number of matching events.")
    has_more: bool = Field(..., description="Whether there are more results.")


class MonitoringChangesFiltersSchema(BaseModel):
    """Filter parameters for monitoring changes endpoint (for documentation only)."""

    company_ids: Optional[List[UUID]] = Field(
        default=None,
        description="Companies to filter by.",
    )
    change_types: Optional[List[str]] = Field(
        default=None,
        description="High-level change types (e.g. website_structure, pricing).",
    )
    date_from: Optional[datetime] = Field(
        default=None,
        description="Start of date range filter.",
    )
    date_to: Optional[datetime] = Field(
        default=None,
        description="End of date range filter.",
    )
    limit: int = Field(50, ge=1, le=500, description="Maximum number of results.")
    offset: int = Field(0, ge=0, description="Pagination offset.")


