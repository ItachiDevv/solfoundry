"""Tests for the notification system."""

import asyncio
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.notification import NotificationCreate, NotificationType
from app.services import notification_service
from app.services.notification_service import _reset_stores

client = TestClient(app)

USER_ID = "user-test-123"
USER_ID_2 = "user-test-456"


@pytest.fixture(autouse=True)
def clean_store():
    _reset_stores()
    yield
    _reset_stores()


def _create_notification(
    user_id=USER_ID,
    ntype=NotificationType.BOUNTY_CLAIMED,
    message="Test notification",
    bounty_id="bounty-1",
):
    result = notification_service.create_notification(NotificationCreate(
        type=ntype, message=message, user_id=user_id, bounty_id=bounty_id,
    ))
    return result.model_dump(mode="json")


class TestListNotifications:
    def test_empty_list(self):
        r = client.get("/api/notifications", params={"user_id": USER_ID})
        assert r.status_code == 200
        data = r.json()
        assert data["items"] == []
        assert data["total"] == 0
        assert data["unread_count"] == 0

    def test_list_returns_created(self):
        _create_notification()
        _create_notification(message="Second notification")
        r = client.get("/api/notifications", params={"user_id": USER_ID})
        assert r.status_code == 200
        data = r.json()
        assert data["total"] == 2
        assert data["unread_count"] == 2
        assert len(data["items"]) == 2

    def test_list_pagination(self):
        for i in range(5):
            _create_notification(message=f"Notification {i}")
        r = client.get("/api/notifications", params={"user_id": USER_ID, "skip": 1, "limit": 2})
        assert r.status_code == 200
        data = r.json()
        assert len(data["items"]) == 2
        assert data["total"] == 5

    def test_list_unread_only(self):
        n1 = _create_notification(message="First")
        _create_notification(message="Second")
        notification_service.mark_as_read(n1["id"], USER_ID)
        r = client.get("/api/notifications", params={"user_id": USER_ID, "unread_only": True})
        assert r.status_code == 200
        data = r.json()
        assert data["total"] == 1
        assert data["unread_count"] == 1

    def test_list_scoped_to_user(self):
        _create_notification(user_id=USER_ID)
        _create_notification(user_id=USER_ID_2)
        r = client.get("/api/notifications", params={"user_id": USER_ID})
        assert r.status_code == 200
        data = r.json()
        assert data["total"] == 1
        assert data["items"][0]["user_id"] == USER_ID

    def test_list_requires_user_id(self):
        r = client.get("/api/notifications")
        assert r.status_code == 422


class TestMarkAsRead:
    def test_mark_single_read(self):
        n = _create_notification()
        r = client.patch(
            f"/api/notifications/{n['id']}/read",
            params={"user_id": USER_ID},
        )
        assert r.status_code == 200
        assert r.json()["read"] is True

    def test_mark_read_not_found(self):
        r = client.patch("/api/notifications/nonexistent/read", params={"user_id": USER_ID})
        assert r.status_code == 404

    def test_mark_read_wrong_user(self):
        n = _create_notification(user_id=USER_ID)
        r = client.patch(
            f"/api/notifications/{n['id']}/read",
            params={"user_id": USER_ID_2},
        )
        assert r.status_code == 404

    def test_mark_all_read(self):
        _create_notification(message="A")
        _create_notification(message="B")
        _create_notification(message="C")
        r = client.post("/api/notifications/read-all", params={"user_id": USER_ID})
        assert r.status_code == 200
        assert r.json()["updated"] == 3
        r2 = client.get("/api/notifications", params={"user_id": USER_ID})
        assert r2.json()["unread_count"] == 0

    def test_mark_all_read_only_affects_user(self):
        _create_notification(user_id=USER_ID)
        _create_notification(user_id=USER_ID_2)
        r = client.post("/api/notifications/read-all", params={"user_id": USER_ID})
        assert r.json()["updated"] == 1
        assert notification_service.get_unread_count(USER_ID_2) == 1


class TestGetNotification:
    def test_get_existing(self):
        n = _create_notification()
        r = client.get(f"/api/notifications/{n['id']}")
        assert r.status_code == 200
        data = r.json()
        assert data["id"] == n["id"]
        assert data["type"] == NotificationType.BOUNTY_CLAIMED.value
        assert data["message"] == "Test notification"
        assert data["read"] is False
        assert data["user_id"] == USER_ID
        assert data["bounty_id"] == "bounty-1"

    def test_get_not_found(self):
        r = client.get("/api/notifications/nonexistent")
        assert r.status_code == 404


class TestDeleteNotification:
    def test_delete_existing(self):
        n = _create_notification()
        r = client.delete(
            f"/api/notifications/{n['id']}",
            params={"user_id": USER_ID},
        )
        assert r.status_code == 204
        r2 = client.get(f"/api/notifications/{n['id']}")
        assert r2.status_code == 404

    def test_delete_not_found(self):
        r = client.delete("/api/notifications/nonexistent", params={"user_id": USER_ID})
        assert r.status_code == 404

    def test_delete_wrong_user(self):
        n = _create_notification(user_id=USER_ID)
        r = client.delete(
            f"/api/notifications/{n['id']}",
            params={"user_id": USER_ID_2},
        )
        assert r.status_code == 404


class TestUnreadCount:
    def test_unread_count_empty(self):
        r = client.get("/api/notifications/count/unread", params={"user_id": USER_ID})
        assert r.status_code == 200
        assert r.json()["unread_count"] == 0

    def test_unread_count_increments(self):
        _create_notification()
        _create_notification()
        r = client.get("/api/notifications/count/unread", params={"user_id": USER_ID})
        assert r.json()["unread_count"] == 2

    def test_unread_count_decrements_on_read(self):
        n = _create_notification()
        _create_notification()
        notification_service.mark_as_read(n["id"], USER_ID)
        r = client.get("/api/notifications/count/unread", params={"user_id": USER_ID})
        assert r.json()["unread_count"] == 1


class TestNotificationTypes:
    def test_all_types_create_successfully(self):
        for ntype in NotificationType:
            n = _create_notification(ntype=ntype, message=f"Test {ntype.value}")
            assert n["type"] == ntype.value

    def test_notification_fields(self):
        n = _create_notification(
            ntype=NotificationType.PAYOUT_SENT,
            message="Payout of 100 SOL sent", bounty_id="bounty-42",
        )
        assert n["type"] == "payout_sent"
        assert n["bounty_id"] == "bounty-42"
        assert n["created_at"] is not None


class TestPreferences:
    def test_get_default_preferences(self):
        r = client.get(f"/api/notifications/preferences/{USER_ID}")
        assert r.status_code == 200
        data = r.json()
        assert data["email_enabled"] is False
        assert data["email_address"] is None

    def test_update_preferences(self):
        r = client.patch(
            f"/api/notifications/preferences/{USER_ID}",
            json={"email_enabled": True, "email_address": "test@example.com"},
        )
        assert r.status_code == 200
        data = r.json()
        assert data["email_enabled"] is True
        assert data["email_address"] == "test@example.com"

    def test_partial_update_preferences(self):
        client.patch(
            f"/api/notifications/preferences/{USER_ID}",
            json={"email_enabled": True, "email_address": "a@b.com"},
        )
        r = client.patch(
            f"/api/notifications/preferences/{USER_ID}",
            json={"email_address": "new@b.com"},
        )
        assert r.status_code == 200
        data = r.json()
        assert data["email_enabled"] is True
        assert data["email_address"] == "new@b.com"

    def test_update_email_types(self):
        r = client.patch(
            f"/api/notifications/preferences/{USER_ID}",
            json={"email_types": ["bounty_claimed", "payout_sent"]},
        )
        assert r.status_code == 200
        data = r.json()
        assert set(data["email_types"]) == {"bounty_claimed", "payout_sent"}


class TestNotificationService:
    def test_create_returns_response(self):
        result = notification_service.create_notification(NotificationCreate(
            type=NotificationType.REVIEW_COMPLETE, message="Review done",
            user_id=USER_ID, bounty_id="b-1", metadata={"reviewer": "alice"},
        ))
        assert result.type == NotificationType.REVIEW_COMPLETE
        assert result.metadata == {"reviewer": "alice"}

    def test_mark_as_read_idempotent(self):
        n = _create_notification()
        r1 = notification_service.mark_as_read(n["id"], USER_ID)
        assert r1 is not None and r1.read is True
        r2 = notification_service.mark_as_read(n["id"], USER_ID)
        assert r2 is not None and r2.read is True

    def test_mark_all_returns_zero_when_none_unread(self):
        n = _create_notification()
        notification_service.mark_as_read(n["id"], USER_ID)
        count = notification_service.mark_all_as_read(USER_ID)
        assert count == 0


class TestEmailService:
    def test_send_email_skips_without_config(self):
        from app.services.email_service import send_notification_email
        loop = asyncio.new_event_loop()
        result = loop.run_until_complete(
            send_notification_email(
                to_email="test@example.com",
                notification_type=NotificationType.PAYOUT_SENT,
                message="Test",
            )
        )
        loop.close()
        assert result is False

    @patch.dict(
        "os.environ",
        {"RESEND_API_KEY": "re_test_key", "RESEND_FROM_EMAIL": "noreply@solfoundry.dev"},
    )
    def test_send_email_calls_resend(self):
        from app.services.email_service import send_notification_email
        with patch("app.services.email_service.httpx.AsyncClient") as mock_client_cls:
            mock_resp = AsyncMock()
            mock_resp.status_code = 200
            mock_client_instance = AsyncMock()
            mock_client_instance.post.return_value = mock_resp
            mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
            mock_client_instance.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client_instance
            loop = asyncio.new_event_loop()
            result = loop.run_until_complete(
                send_notification_email(
                    to_email="dev@example.com",
                    notification_type=NotificationType.BOUNTY_CLAIMED,
                    message="Bounty claimed!",
                    metadata={"bounty_id": "b-1"},
                )
            )
            loop.close()
            assert result is True
            mock_client_instance.post.assert_called_once()
            call_kwargs = mock_client_instance.post.call_args
            assert "dev@example.com" in call_kwargs.kwargs["json"]["to"]


class TestSendNotification:
    def test_send_notification_creates_and_returns(self):
        loop = asyncio.new_event_loop()
        result = loop.run_until_complete(
            notification_service.send_notification(
                type=NotificationType.RANK_CHANGED,
                message="You moved up to rank 5!",
                user_id=USER_ID, metadata={"new_rank": 5},
            )
        )
        loop.close()
        assert result.type == NotificationType.RANK_CHANGED
        assert result.message == "You moved up to rank 5!"
        assert result.user_id == USER_ID
        r = client.get("/api/notifications", params={"user_id": USER_ID})
        assert r.json()["total"] == 1
