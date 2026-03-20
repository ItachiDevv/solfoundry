"""In-memory notification service for MVP.

Persistence roadmap
-------------------
This service uses plain ``dict`` objects as its backing stores.  Data is
intentionally **not** persisted across process restarts -- acceptable for
local development, CI pipelines, and single-dyno staging environments.

**Production migration path (PostgreSQL):**

1. Replace ``_notification_store`` with SQLAlchemy async session queries
   against a ``notifications`` table (schema documented in
   ``app.models.notification``).  The column layout already matches 1-to-1.
2. Replace ``_user_preferences`` with a ``notification_preferences`` table
   keyed on ``user_id``.
3. Add a Redis pub/sub channel (``notifications:{user_id}``) so the
   WebSocket layer can fan-out to multiple server processes.
4. Integrate Resend (or any SMTP relay) behind ``send_notification_email``,
   gated on per-user ``email_enabled`` preferences.

Concurrency note
----------------
Python's GIL protects dict mutations from data races within a single
async event loop.  For multi-worker deployments the PostgreSQL migration
is required to guarantee consistency.

Rate-limiting note
------------------
Production deployments should add ``slowapi`` (or equivalent) middleware
on write endpoints.  Sensible defaults: 60 req/min for reads, 20 req/min
for writes per user.
"""

import logging
from typing import Optional

from app.models.notification import (
    NotificationCreate,
    NotificationDB,
    NotificationListResponse,
    NotificationPreferences,
    NotificationPreferencesUpdate,
    NotificationResponse,
    NotificationType,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# In-memory stores (replaced by PostgreSQL in production)
# ---------------------------------------------------------------------------

_notification_store: dict[str, NotificationDB] = {}
_user_preferences: dict[str, NotificationPreferences] = {}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _to_response(n: NotificationDB) -> NotificationResponse:
    """Convert an internal DB record to an API response model."""
    return NotificationResponse(
        id=n.id, type=n.type, message=n.message, read=n.read,
        user_id=n.user_id, bounty_id=n.bounty_id,
        metadata=n.metadata, created_at=n.created_at,
    )


def _get_user_notifications(user_id: str) -> list[NotificationDB]:
    """Return all notifications for a user, sorted newest-first."""
    return sorted(
        [n for n in _notification_store.values() if n.user_id == user_id],
        key=lambda n: n.created_at, reverse=True,
    )


# ---------------------------------------------------------------------------
# CRUD operations
# ---------------------------------------------------------------------------


def create_notification(data: NotificationCreate) -> NotificationResponse:
    """Create a notification and return it.

    Does not raise for unknown ``user_id`` values -- notifications may
    target users who have not yet created a profile.
    """
    notification = NotificationDB(
        type=data.type, message=data.message, user_id=data.user_id,
        bounty_id=data.bounty_id, metadata=data.metadata,
    )
    _notification_store[notification.id] = notification
    logger.info("Notification created: id=%s type=%s user=%s",
                notification.id, notification.type.value, notification.user_id)
    return _to_response(notification)


def get_notification(notification_id: str) -> Optional[NotificationResponse]:
    """Retrieve a single notification by ID, or None if not found."""
    n = _notification_store.get(notification_id)
    return _to_response(n) if n else None


def list_notifications(
    user_id: str,
    unread_only: bool = False,
    notification_type: Optional[NotificationType] = None,
    skip: int = 0,
    limit: int = 20,
) -> NotificationListResponse:
    """Return paginated notifications for a user, newest-first.

    ``unread_count`` in the response always reflects the *global* unread
    total for the user, regardless of pagination or filters applied.
    """
    user_notifications = _get_user_notifications(user_id)
    all_unread = sum(1 for n in user_notifications if not n.read)
    if unread_only:
        user_notifications = [n for n in user_notifications if not n.read]
    if notification_type is not None:
        user_notifications = [
            n for n in user_notifications if n.type == notification_type
        ]
    total = len(user_notifications)
    page = user_notifications[skip: skip + limit]
    return NotificationListResponse(
        items=[_to_response(n) for n in page],
        total=total, unread_count=all_unread, skip=skip, limit=limit,
    )


def mark_as_read(notification_id: str, user_id: str) -> Optional[NotificationResponse]:
    """Mark a single notification as read.  Idempotent.

    Returns None if the notification does not exist or does not belong
    to the given user (ownership check).
    """
    n = _notification_store.get(notification_id)
    if not n or n.user_id != user_id:
        return None
    n.read = True
    return _to_response(n)


def mark_all_as_read(user_id: str) -> int:
    """Mark every unread notification for *user_id* as read.

    Returns the count of notifications that were actually updated
    (already-read notifications are skipped).
    """
    count = 0
    for n in _notification_store.values():
        if n.user_id == user_id and not n.read:
            n.read = True
            count += 1
    return count


def get_unread_count(user_id: str) -> int:
    """Fast unread count for badge counters, without building a full list."""
    return sum(1 for n in _notification_store.values()
               if n.user_id == user_id and not n.read)


def delete_notification(notification_id: str, user_id: str) -> bool:
    """Delete a notification.  Returns False if not found or not owned."""
    n = _notification_store.get(notification_id)
    if not n or n.user_id != user_id:
        return False
    del _notification_store[notification_id]
    return True


# ---------------------------------------------------------------------------
# User preferences
# ---------------------------------------------------------------------------


def get_preferences(user_id: str) -> NotificationPreferences:
    """Return notification preferences for a user (defaults if unset)."""
    return _user_preferences.get(user_id, NotificationPreferences())


def update_preferences(
    user_id: str, data: NotificationPreferencesUpdate,
) -> NotificationPreferences:
    """Partially update notification preferences for a user."""
    prefs = _user_preferences.get(user_id, NotificationPreferences())
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(prefs, key, value)
    _user_preferences[user_id] = prefs
    return prefs


# ---------------------------------------------------------------------------
# High-level send helper (combines create + optional email)
# ---------------------------------------------------------------------------


async def send_notification(
    type: NotificationType, message: str, user_id: str,
    bounty_id: Optional[str] = None, metadata: Optional[dict] = None,
) -> NotificationResponse:
    """Create a notification and optionally send an email.

    This is the primary entry point for internal services (webhooks,
    payout pipeline, review system) to emit notifications.  Email
    delivery is gated on per-user preferences.
    """
    data = NotificationCreate(
        type=type, message=message, user_id=user_id,
        bounty_id=bounty_id, metadata=metadata or {},
    )
    notification = create_notification(data)
    prefs = get_preferences(user_id)
    if prefs.email_enabled and prefs.email_address and type in prefs.email_types:
        from app.services.email_service import send_notification_email
        await send_notification_email(
            to_email=prefs.email_address, notification_type=type,
            message=message, metadata=metadata or {},
        )
    return notification


# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------


def _reset_stores() -> None:
    """Clear all data -- used by test fixtures only."""
    _notification_store.clear()
    _user_preferences.clear()
