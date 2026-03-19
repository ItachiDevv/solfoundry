"""In-memory notification service for MVP."""

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

_notification_store: dict[str, NotificationDB] = {}
_user_preferences: dict[str, NotificationPreferences] = {}


def _to_response(n: NotificationDB) -> NotificationResponse:
    return NotificationResponse(
        id=n.id, type=n.type, message=n.message, read=n.read,
        user_id=n.user_id, bounty_id=n.bounty_id,
        metadata=n.metadata, created_at=n.created_at,
    )


def _get_user_notifications(user_id: str) -> list[NotificationDB]:
    return sorted(
        [n for n in _notification_store.values() if n.user_id == user_id],
        key=lambda n: n.created_at, reverse=True,
    )


def create_notification(data: NotificationCreate) -> NotificationResponse:
    notification = NotificationDB(
        type=data.type, message=data.message, user_id=data.user_id,
        bounty_id=data.bounty_id, metadata=data.metadata,
    )
    _notification_store[notification.id] = notification
    logger.info("Notification created: id=%s type=%s user=%s",
                notification.id, notification.type.value, notification.user_id)
    return _to_response(notification)


def get_notification(notification_id: str) -> Optional[NotificationResponse]:
    n = _notification_store.get(notification_id)
    return _to_response(n) if n else None


def list_notifications(
    user_id: str, unread_only: bool = False, skip: int = 0, limit: int = 20,
) -> NotificationListResponse:
    user_notifications = _get_user_notifications(user_id)
    all_unread = sum(1 for n in user_notifications if not n.read)
    if unread_only:
        user_notifications = [n for n in user_notifications if not n.read]
    total = len(user_notifications)
    page = user_notifications[skip: skip + limit]
    return NotificationListResponse(
        items=[_to_response(n) for n in page],
        total=total, unread_count=all_unread, skip=skip, limit=limit,
    )


def mark_as_read(notification_id: str, user_id: str) -> Optional[NotificationResponse]:
    n = _notification_store.get(notification_id)
    if not n or n.user_id != user_id:
        return None
    n.read = True
    return _to_response(n)


def mark_all_as_read(user_id: str) -> int:
    count = 0
    for n in _notification_store.values():
        if n.user_id == user_id and not n.read:
            n.read = True
            count += 1
    return count


def get_unread_count(user_id: str) -> int:
    return sum(1 for n in _notification_store.values()
               if n.user_id == user_id and not n.read)


def delete_notification(notification_id: str, user_id: str) -> bool:
    n = _notification_store.get(notification_id)
    if not n or n.user_id != user_id:
        return False
    del _notification_store[notification_id]
    return True


def get_preferences(user_id: str) -> NotificationPreferences:
    return _user_preferences.get(user_id, NotificationPreferences())


def update_preferences(
    user_id: str, data: NotificationPreferencesUpdate,
) -> NotificationPreferences:
    prefs = _user_preferences.get(user_id, NotificationPreferences())
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(prefs, key, value)
    _user_preferences[user_id] = prefs
    return prefs


async def send_notification(
    type: NotificationType, message: str, user_id: str,
    bounty_id: Optional[str] = None, metadata: Optional[dict] = None,
) -> NotificationResponse:
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


def _reset_stores() -> None:
    _notification_store.clear()
    _user_preferences.clear()
