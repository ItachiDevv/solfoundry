"""Notification API endpoints."""

from fastapi import APIRouter, HTTPException, Query

from app.models.notification import (
    NotificationListResponse,
    NotificationPreferences,
    NotificationPreferencesUpdate,
    NotificationResponse,
)
from app.services import notification_service

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


@router.get("", response_model=NotificationListResponse)
async def list_notifications(
    user_id: str = Query(..., description="User ID to fetch notifications for"),
    unread_only: bool = Query(False, description="Only return unread notifications"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
):
    """Get paginated notifications for a user, with unread count."""
    return notification_service.list_notifications(
        user_id=user_id, unread_only=unread_only, skip=skip, limit=limit,
    )


@router.patch("/{notification_id}/read", response_model=NotificationResponse)
async def mark_notification_read(
    notification_id: str,
    user_id: str = Query(..., description="User ID (owner of the notification)"),
):
    """Mark a single notification as read."""
    result = notification_service.mark_as_read(notification_id, user_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Notification not found")
    return result


@router.post("/read-all")
async def mark_all_read(
    user_id: str = Query(..., description="User ID"),
):
    """Mark all notifications as read for a user."""
    count = notification_service.mark_all_as_read(user_id)
    return {"updated": count}


@router.get("/{notification_id}", response_model=NotificationResponse)
async def get_notification(notification_id: str):
    """Get a single notification by ID."""
    n = notification_service.get_notification(notification_id)
    if n is None:
        raise HTTPException(status_code=404, detail="Notification not found")
    return n


@router.delete("/{notification_id}", status_code=204)
async def delete_notification(
    notification_id: str,
    user_id: str = Query(..., description="User ID (owner of the notification)"),
):
    """Delete a notification."""
    if not notification_service.delete_notification(notification_id, user_id):
        raise HTTPException(status_code=404, detail="Notification not found")


@router.get("/count/unread")
async def get_unread_count(
    user_id: str = Query(..., description="User ID"),
):
    """Get unread notification count for a user."""
    count = notification_service.get_unread_count(user_id)
    return {"unread_count": count}


@router.get("/preferences/{user_id}", response_model=NotificationPreferences)
async def get_preferences(user_id: str):
    """Get notification preferences for a user."""
    return notification_service.get_preferences(user_id)


@router.patch("/preferences/{user_id}", response_model=NotificationPreferences)
async def update_preferences(user_id: str, data: NotificationPreferencesUpdate):
    """Update notification preferences for a user."""
    return notification_service.update_preferences(user_id, data)
