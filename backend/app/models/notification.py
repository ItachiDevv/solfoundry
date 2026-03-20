"""Notification data models and enums.

Defines the notification schema for the SolFoundry notification system.
Notification types cover the full bounty lifecycle: claim, PR submission,
review completion, payout, expiry, and rank changes.

Persistence strategy (MVP -> Production)
-----------------------------------------
MVP:  In-memory dict store (``NotificationDB`` as a Pydantic model) --
      sufficient for single-process dev/testing and CI.
Prod: Migrate ``NotificationDB`` to a SQLAlchemy ORM model backed by
      PostgreSQL.  The column layout below maps 1-to-1 to the planned
      ``notifications`` table::

          id         UUID  PRIMARY KEY  DEFAULT uuid_generate_v4()
          user_id    VARCHAR(100)  NOT NULL  INDEX
          type       VARCHAR(50)   NOT NULL  INDEX
          message    TEXT          NOT NULL
          read       BOOLEAN       DEFAULT FALSE
          bounty_id  VARCHAR(100)  NULLABLE
          metadata   JSONB         DEFAULT '{}'
          created_at TIMESTAMPTZ   DEFAULT now()

      Add a Redis pub/sub channel (``notifications:{user_id}``) for
      WebSocket fan-out across multiple server processes.
"""

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator


class NotificationType(str, Enum):
    """All supported notification event types.

    Each type corresponds to a distinct lifecycle event in the bounty
    pipeline.  New types should be added here and registered in the
    email subject map (``email_service._SUBJECT_MAP``).
    """

    BOUNTY_CLAIMED = "bounty_claimed"
    PR_SUBMITTED = "pr_submitted"
    REVIEW_COMPLETE = "review_complete"
    PAYOUT_SENT = "payout_sent"
    BOUNTY_EXPIRED = "bounty_expired"
    RANK_CHANGED = "rank_changed"


class NotificationDB(BaseModel):
    """In-memory notification record.

    In production, this will be replaced by a SQLAlchemy ORM model
    mapped to a PostgreSQL ``notifications`` table.  The field names
    are intentionally kept identical so the service layer migration
    requires only a session-query swap.
    """

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    type: NotificationType
    message: str
    read: bool = False
    user_id: str
    bounty_id: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class NotificationCreate(BaseModel):
    """Payload for creating a notification (internal use / webhook callers).

    Input validation ensures that ``user_id`` and ``message`` are
    non-empty and within reasonable size limits.
    """

    type: NotificationType
    message: str = Field(
        ..., min_length=1, max_length=2000, description="Human-readable notification message"
    )
    user_id: str = Field(
        ..., min_length=1, max_length=100, description="Target user identifier"
    )
    bounty_id: Optional[str] = Field(
        None, max_length=100, description="Related bounty ID"
    )
    metadata: dict[str, Any] = Field(default_factory=dict, description="Extra payload data")

    @field_validator("user_id")
    @classmethod
    def user_id_not_blank(cls, v: str) -> str:
        """Reject whitespace-only user IDs."""
        if not v.strip():
            raise ValueError("user_id must not be blank")
        return v.strip()

    @field_validator("message")
    @classmethod
    def message_not_blank(cls, v: str) -> str:
        """Reject whitespace-only messages."""
        if not v.strip():
            raise ValueError("message must not be blank")
        return v


class NotificationResponse(BaseModel):
    """Single notification returned by the API."""

    id: str
    type: NotificationType
    message: str
    read: bool
    user_id: str
    bounty_id: Optional[str] = None
    metadata: dict[str, Any] = {}
    created_at: datetime


class NotificationListResponse(BaseModel):
    """Paginated notification list with unread count.

    ``unread_count`` reflects the global unread total for the user,
    regardless of any filters or pagination applied to ``items``.
    """

    items: list[NotificationResponse]
    total: int
    unread_count: int
    skip: int
    limit: int


class NotificationPreferences(BaseModel):
    """User notification preferences (email delivery settings).

    When ``email_enabled`` is True and ``email_address`` is set, the
    system will attempt to send emails for notification types listed in
    ``email_types`` via the Resend API.
    """

    email_enabled: bool = False
    email_address: Optional[str] = None
    email_types: list[NotificationType] = Field(
        default_factory=lambda: list(NotificationType)
    )


class NotificationPreferencesUpdate(BaseModel):
    """Payload for partially updating notification preferences.

    Only fields included in the request body are updated; omitted
    fields retain their current values.
    """

    email_enabled: Optional[bool] = None
    email_address: Optional[str] = Field(
        None, max_length=320, description="Email address for notifications"
    )
    email_types: Optional[list[NotificationType]] = None
