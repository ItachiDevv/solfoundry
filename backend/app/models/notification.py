"""Notification models and enums."""

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class NotificationType(str, Enum):
    """All supported notification types."""
    BOUNTY_CLAIMED = "bounty_claimed"
    PR_SUBMITTED = "pr_submitted"
    REVIEW_COMPLETE = "review_complete"
    PAYOUT_SENT = "payout_sent"
    BOUNTY_EXPIRED = "bounty_expired"
    RANK_CHANGED = "rank_changed"


class NotificationDB(BaseModel):
    """In-memory notification record."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    type: NotificationType
    message: str
    read: bool = False
    user_id: str
    bounty_id: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class NotificationCreate(BaseModel):
    """Payload for creating a notification (internal use)."""
    type: NotificationType
    message: str
    user_id: str
    bounty_id: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class NotificationResponse(BaseModel):
    """Single notification response."""
    id: str
    type: NotificationType
    message: str
    read: bool
    user_id: str
    bounty_id: Optional[str] = None
    metadata: dict[str, Any] = {}
    created_at: datetime


class NotificationListResponse(BaseModel):
    """Paginated notification list with unread count."""
    items: list[NotificationResponse]
    total: int
    unread_count: int
    skip: int
    limit: int


class NotificationPreferences(BaseModel):
    """User notification preferences."""
    email_enabled: bool = False
    email_address: Optional[str] = None
    email_types: list[NotificationType] = Field(
        default_factory=lambda: list(NotificationType)
    )


class NotificationPreferencesUpdate(BaseModel):
    """Payload for updating notification preferences."""
    email_enabled: Optional[bool] = None
    email_address: Optional[str] = None
    email_types: Optional[list[NotificationType]] = None
