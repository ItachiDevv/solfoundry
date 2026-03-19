"""Event log model for webhook event tracking and idempotency."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class EventStatus(str, Enum):
    PENDING = "pending"
    PROCESSED = "processed"
    FAILED = "failed"
    SKIPPED = "skipped"  # duplicate delivery_id


class EventLog(BaseModel):
    """Record of a processed (or attempted) webhook event."""

    delivery_id: str
    event_type: str
    payload_hash: str
    status: EventStatus = EventStatus.PENDING
    error_message: Optional[str] = None
    received_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    processed_at: Optional[datetime] = None


class EventLogResponse(BaseModel):
    delivery_id: str
    event_type: str
    payload_hash: str
    status: str
    error_message: Optional[str] = None
    received_at: datetime
    processed_at: Optional[datetime] = None
