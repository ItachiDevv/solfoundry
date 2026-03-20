"""Notification system API router.

Endpoints
---------
- ``GET  /api/notifications``                      -- paginated list with unread count
- ``GET  /api/notifications/{id}``                 -- single notification detail
- ``PATCH /api/notifications/{id}/read``           -- mark one as read
- ``POST  /api/notifications/read-all``            -- mark all as read for a user
- ``POST  /api/notifications``                     -- create (internal / webhook use)
- ``DELETE /api/notifications/{id}``               -- delete a notification
- ``GET  /api/notifications/count/unread``         -- lightweight badge count
- ``GET  /api/notifications/preferences/{user_id}``  -- email prefs
- ``PATCH /api/notifications/preferences/{user_id}`` -- update email prefs

Rate-limiting consideration
---------------------------
Production deployments should add a rate-limit middleware (e.g. ``slowapi``)
on the ``POST`` and ``PATCH`` routes.  Suggested defaults: 60 req/min per
user for reads, 20 req/min for writes.  The MVP omits this to keep the
dependency footprint minimal.
"""

from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from app.models.notification import (
    NotificationCreate,
    NotificationListResponse,
    NotificationPreferences,
    NotificationPreferencesUpdate,
    NotificationResponse,
    NotificationType,
)
from app.services import notification_service

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


# ---------------------------------------------------------------------------
# List / query
# ---------------------------------------------------------------------------


@router.get("", response_model=NotificationListResponse)
async def list_notifications(
    user_id: str = Query(
        ..., min_length=1, max_length=100, description="User to fetch notifications for"
    ),
    unread_only: bool = Query(False, description="Return only unread notifications"),
    type: Optional[NotificationType] = Query(
        None, description="Filter by notification type"
    ),
    skip: int = Query(0, ge=0, description="Pagination offset"),
    limit: int = Query(20, ge=1, le=100, description="Page size (max 100)"),
):
    """Return paginated notifications for a user, newest-first.

    The ``unread_count`` in the response reflects the **global** unread
    total, regardless of any filters or pagination applied.
    """
    return notification_service.list_notifications(
        user_id=user_id,
        unread_only=unread_only,
        notification_type=type,
        skip=skip,
        limit=limit,
    )


@router.get("/count/unread")
async def get_unread_count(
    user_id: str = Query(
        ..., min_length=1, max_length=100, description="User ID"
    ),
):
    """Lightweight endpoint for badge counters -- returns only the unread count."""
    count = notification_service.get_unread_count(user_id)
    return {"user_id": user_id, "unread_count": count}


# ---------------------------------------------------------------------------
# Single item
# ---------------------------------------------------------------------------


@router.get("/{notification_id}", response_model=NotificationResponse)
async def get_notification(notification_id: str):
    """Retrieve a single notification by ID."""
    n = notification_service.get_notification(notification_id)
    if n is None:
        raise HTTPException(status_code=404, detail="Notification not found")
    return n


# ---------------------------------------------------------------------------
# Mutations
# ---------------------------------------------------------------------------


@router.post("", response_model=NotificationResponse, status_code=201)
async def create_notification(data: NotificationCreate):
    """Create a new notification (typically called by internal services or webhooks).

    Input validation is handled by the ``NotificationCreate`` model:
    ``user_id`` and ``message`` must be non-empty and within size limits.
    """
    return notification_service.create_notification(data)


@router.patch("/{notification_id}/read", response_model=NotificationResponse)
async def mark_notification_read(
    notification_id: str,
    user_id: str = Query(
        ..., min_length=1, max_length=100, description="User ID (owner of the notification)"
    ),
):
    """Mark a single notification as read.  Idempotent."""
    result = notification_service.mark_as_read(notification_id, user_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Notification not found")
    return result


@router.post("/read-all")
async def mark_all_read(
    user_id: str = Query(
        ..., min_length=1, max_length=100, description="User whose notifications to mark read"
    ),
):
    """Mark every unread notification for the given user as read."""
    count = notification_service.mark_all_as_read(user_id)
    return {"updated": count}


@router.delete("/{notification_id}", status_code=204)
async def delete_notification(
    notification_id: str,
    user_id: str = Query(
        ..., min_length=1, max_length=100, description="User ID (owner of the notification)"
    ),
):
    """Delete a notification.  Returns 404 if it does not exist or is not owned by the user."""
    if not notification_service.delete_notification(notification_id, user_id):
        raise HTTPException(status_code=404, detail="Notification not found")


# ---------------------------------------------------------------------------
# Preferences
# ---------------------------------------------------------------------------


@router.get("/preferences/{user_id}", response_model=NotificationPreferences)
async def get_preferences(user_id: str):
    """Return email notification preferences for a user (defaults if unset)."""
    return notification_service.get_preferences(user_id)


@router.patch("/preferences/{user_id}", response_model=NotificationPreferences)
async def update_preferences(user_id: str, data: NotificationPreferencesUpdate):
    """Partially update email notification preferences for a user."""
    return notification_service.update_preferences(user_id, data)
