"""Tests for the notification system.

Covers CRUD operations, pagination, filtering, edge cases (non-existent
users, large notification volumes, concurrent mark-as-read, ownership
checks), input validation on all endpoints, email service, preferences,
and the high-level send_notification helper.
"""

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
    """Reset the in-memory store between every test."""
    _reset_stores()
    yield
    _reset_stores()


def _create_notification(
    user_id=USER_ID,
    ntype=NotificationType.BOUNTY_CLAIMED,
    message="Test notification",
    bounty_id="bounty-1",
    metadata=None,
):
    result = notification_service.create_notification(NotificationCreate(
        type=ntype, message=message, user_id=user_id, bounty_id=bounty_id,
        metadata=metadata or {},
    ))
    return result.model_dump(mode="json")


# ===================================================================
# CREATE (via POST endpoint)
# ===================================================================


class TestCreateNotification:
    def test_create_via_api(self):
        r = client.post("/api/notifications", json={
            "type": "bounty_claimed", "message": "Claimed!", "user_id": USER_ID,
        })
        assert r.status_code == 201
        data = r.json()
        assert data["user_id"] == USER_ID
        assert data["type"] == "bounty_claimed"
        assert data["read"] is False
        assert "id" in data
        assert "created_at" in data

    def test_create_all_types_via_api(self):
        for ntype in NotificationType:
            r = client.post("/api/notifications", json={
                "type": ntype.value, "message": f"Test {ntype.value}", "user_id": USER_ID,
            })
            assert r.status_code == 201, f"Failed for type {ntype.value}"

    def test_create_with_metadata(self):
        meta = {"pr_url": "https://github.com/org/repo/pull/42", "score": 8.5}
        r = client.post("/api/notifications", json={
            "type": "review_complete", "message": "Review done",
            "user_id": USER_ID, "metadata": meta,
        })
        assert r.status_code == 201
        assert r.json()["metadata"] == meta

    def test_create_without_bounty_id(self):
        r = client.post("/api/notifications", json={
            "type": "rank_changed", "message": "You ranked up!", "user_id": USER_ID,
        })
        assert r.status_code == 201
        assert r.json()["bounty_id"] is None

    def test_create_for_nonexistent_user(self):
        """Notifications can target users who haven't created a profile yet."""
        r = client.post("/api/notifications", json={
            "type": "bounty_claimed", "message": "Claimed!",
            "user_id": "ghost-user-999",
        })
        assert r.status_code == 201
        assert r.json()["user_id"] == "ghost-user-999"

    def test_create_missing_user_id(self):
        r = client.post("/api/notifications", json={
            "type": "bounty_claimed", "message": "hello",
        })
        assert r.status_code == 422

    def test_create_blank_user_id(self):
        r = client.post("/api/notifications", json={
            "type": "bounty_claimed", "message": "hello", "user_id": "   ",
        })
        assert r.status_code == 422

    def test_create_empty_message(self):
        r = client.post("/api/notifications", json={
            "type": "bounty_claimed", "message": "", "user_id": USER_ID,
        })
        assert r.status_code == 422

    def test_create_blank_message(self):
        r = client.post("/api/notifications", json={
            "type": "bounty_claimed", "message": "   ", "user_id": USER_ID,
        })
        assert r.status_code == 422

    def test_create_invalid_type(self):
        r = client.post("/api/notifications", json={
            "type": "invalid_type", "message": "hello", "user_id": USER_ID,
        })
        assert r.status_code == 422

    def test_create_user_id_too_long(self):
        r = client.post("/api/notifications", json={
            "type": "bounty_claimed", "message": "hello", "user_id": "x" * 101,
        })
        assert r.status_code == 422

    def test_create_message_too_long(self):
        r = client.post("/api/notifications", json={
            "type": "bounty_claimed", "message": "x" * 2001, "user_id": USER_ID,
        })
        assert r.status_code == 422


# ===================================================================
# LIST / QUERY
# ===================================================================


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

    def test_list_newest_first(self):
        n1 = _create_notification(message="first")
        n2 = _create_notification(message="second")
        r = client.get("/api/notifications", params={"user_id": USER_ID})
        items = r.json()["items"]
        assert items[0]["id"] == n2["id"]
        assert items[1]["id"] == n1["id"]

    def test_list_pagination(self):
        for i in range(5):
            _create_notification(message=f"Notification {i}")
        r = client.get("/api/notifications", params={"user_id": USER_ID, "skip": 1, "limit": 2})
        assert r.status_code == 200
        data = r.json()
        assert len(data["items"]) == 2
        assert data["total"] == 5

    def test_list_pagination_second_page(self):
        for i in range(15):
            _create_notification(message=f"notif-{i}")
        r = client.get("/api/notifications", params={"user_id": USER_ID, "skip": 10, "limit": 10})
        assert len(r.json()["items"]) == 5  # only 5 remaining

    def test_list_unread_only(self):
        n1 = _create_notification(message="First")
        _create_notification(message="Second")
        notification_service.mark_as_read(n1["id"], USER_ID)
        r = client.get("/api/notifications", params={"user_id": USER_ID, "unread_only": True})
        assert r.status_code == 200
        data = r.json()
        assert data["total"] == 1
        assert data["unread_count"] == 1

    def test_list_filter_by_type(self):
        _create_notification(ntype=NotificationType.BOUNTY_CLAIMED)
        _create_notification(ntype=NotificationType.PAYOUT_SENT, message="Payout sent")
        r = client.get("/api/notifications", params={
            "user_id": USER_ID, "type": "payout_sent",
        })
        assert r.json()["total"] == 1
        assert r.json()["items"][0]["type"] == "payout_sent"

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

    def test_list_limit_too_large(self):
        r = client.get("/api/notifications", params={"user_id": USER_ID, "limit": 101})
        assert r.status_code == 422

    def test_list_negative_skip(self):
        r = client.get("/api/notifications", params={"user_id": USER_ID, "skip": -1})
        assert r.status_code == 422

    def test_list_for_nonexistent_user(self):
        """Querying notifications for an unknown user returns empty, not 404."""
        r = client.get("/api/notifications", params={"user_id": "nobody"})
        assert r.status_code == 200
        assert r.json()["total"] == 0


# ===================================================================
# GET SINGLE
# ===================================================================


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


# ===================================================================
# MARK AS READ
# ===================================================================


class TestMarkAsRead:
    def test_mark_single_read(self):
        n = _create_notification()
        r = client.patch(
            f"/api/notifications/{n['id']}/read",
            params={"user_id": USER_ID},
        )
        assert r.status_code == 200
        assert r.json()["read"] is True

    def test_mark_read_idempotent(self):
        """Marking the same notification read twice succeeds both times."""
        n = _create_notification()
        r1 = client.patch(f"/api/notifications/{n['id']}/read", params={"user_id": USER_ID})
        r2 = client.patch(f"/api/notifications/{n['id']}/read", params={"user_id": USER_ID})
        assert r1.status_code == 200
        assert r2.status_code == 200
        assert r2.json()["read"] is True

    def test_mark_read_not_found(self):
        r = client.patch("/api/notifications/nonexistent/read", params={"user_id": USER_ID})
        assert r.status_code == 404

    def test_mark_read_wrong_user(self):
        """Ownership check: user B cannot mark user A's notification as read."""
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

    def test_mark_all_read_skips_already_read(self):
        n = _create_notification()
        _create_notification()
        notification_service.mark_as_read(n["id"], USER_ID)
        r = client.post("/api/notifications/read-all", params={"user_id": USER_ID})
        assert r.json()["updated"] == 1  # only the unread one

    def test_mark_all_read_no_notifications(self):
        """Calling mark-all-read with no notifications returns 0, not an error."""
        r = client.post("/api/notifications/read-all", params={"user_id": "nobody"})
        assert r.status_code == 200
        assert r.json()["updated"] == 0

    def test_mark_all_read_missing_user_id(self):
        r = client.post("/api/notifications/read-all")
        assert r.status_code == 422


# ===================================================================
# DELETE
# ===================================================================


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
        """Ownership check: user B cannot delete user A's notification."""
        n = _create_notification(user_id=USER_ID)
        r = client.delete(
            f"/api/notifications/{n['id']}",
            params={"user_id": USER_ID_2},
        )
        assert r.status_code == 404

    def test_delete_removes_from_listing(self):
        n = _create_notification()
        client.delete(f"/api/notifications/{n['id']}", params={"user_id": USER_ID})
        listing = client.get("/api/notifications", params={"user_id": USER_ID})
        assert listing.json()["total"] == 0

    def test_delete_then_mark_read_returns_404(self):
        n = _create_notification()
        client.delete(f"/api/notifications/{n['id']}", params={"user_id": USER_ID})
        r = client.patch(f"/api/notifications/{n['id']}/read", params={"user_id": USER_ID})
        assert r.status_code == 404


# ===================================================================
# UNREAD COUNT
# ===================================================================


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

    def test_unread_count_for_unknown_user(self):
        r = client.get("/api/notifications/count/unread", params={"user_id": "nobody"})
        assert r.json()["unread_count"] == 0

    def test_unread_count_includes_user_id(self):
        r = client.get("/api/notifications/count/unread", params={"user_id": USER_ID})
        assert r.json()["user_id"] == USER_ID

    def test_unread_count_missing_user_id(self):
        r = client.get("/api/notifications/count/unread")
        assert r.status_code == 422


# ===================================================================
# NOTIFICATION TYPES
# ===================================================================


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


# ===================================================================
# PREFERENCES
# ===================================================================


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


# ===================================================================
# SERVICE LAYER DIRECT TESTS
# ===================================================================


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

    def test_list_with_type_filter(self):
        _create_notification(ntype=NotificationType.BOUNTY_CLAIMED)
        _create_notification(ntype=NotificationType.PAYOUT_SENT, message="Paid")
        _create_notification(ntype=NotificationType.PAYOUT_SENT, message="Paid 2")
        result = notification_service.list_notifications(
            USER_ID, notification_type=NotificationType.PAYOUT_SENT,
        )
        assert result.total == 2
        assert all(item.type == NotificationType.PAYOUT_SENT for item in result.items)


# ===================================================================
# EMAIL SERVICE
# ===================================================================


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


# ===================================================================
# SEND NOTIFICATION (high-level helper)
# ===================================================================


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


# ===================================================================
# EDGE CASES
# ===================================================================


class TestEdgeCases:
    def test_large_notification_volume(self):
        """Create 200 notifications and verify pagination handles it."""
        for i in range(200):
            _create_notification(message=f"Notification #{i}")
        r = client.get(
            "/api/notifications", params={"user_id": USER_ID, "skip": 0, "limit": 100}
        )
        data = r.json()
        assert data["total"] == 200
        assert len(data["items"]) == 100
        assert data["unread_count"] == 200

    def test_concurrent_mark_as_read_idempotent(self):
        """Simulates two 'concurrent' mark-read calls on the same notification."""
        n = _create_notification()
        nid = n["id"]
        r1 = client.patch(f"/api/notifications/{nid}/read", params={"user_id": USER_ID})
        r2 = client.patch(f"/api/notifications/{nid}/read", params={"user_id": USER_ID})
        assert r1.status_code == 200
        assert r2.status_code == 200
        assert r1.json()["read"] is True
        assert r2.json()["read"] is True

    def test_special_characters_in_message(self):
        msg = 'Bounty "Super <script>alert(1)</script>" claimed by user & co.'
        n = _create_notification(message=msg)
        assert n["message"] == msg

    def test_unicode_in_message(self):
        msg = "Bounty claimed! \u2728\U0001f680"
        n = _create_notification(message=msg)
        assert n["message"] == msg

    def test_empty_metadata_default(self):
        n = _create_notification()
        assert n["metadata"] == {}

    def test_unread_count_in_list_is_global(self):
        """unread_count in list response reflects ALL unread, not just the filtered page."""
        for i in range(10):
            _create_notification(message=f"n-{i}")
        # Mark first 3 as read via service
        listing = client.get("/api/notifications", params={"user_id": USER_ID, "limit": 100})
        for item in listing.json()["items"][:3]:
            notification_service.mark_as_read(item["id"], USER_ID)
        # Query with small limit -- unread_count should still be 7
        r = client.get("/api/notifications", params={"user_id": USER_ID, "limit": 2})
        assert r.json()["unread_count"] == 7

    def test_notification_for_nonexistent_user_returns_empty_list(self):
        """A user with zero notifications gets an empty list, not a 404."""
        r = client.get("/api/notifications", params={"user_id": "nonexistent-user-xyz"})
        assert r.status_code == 200
        assert r.json()["total"] == 0
        assert r.json()["unread_count"] == 0

    def test_mixed_type_filter_with_unread_only(self):
        """Combining type filter and unread_only works correctly."""
        _create_notification(ntype=NotificationType.BOUNTY_CLAIMED, message="c1")
        n2 = _create_notification(ntype=NotificationType.PAYOUT_SENT, message="p1")
        _create_notification(ntype=NotificationType.PAYOUT_SENT, message="p2")
        notification_service.mark_as_read(n2["id"], USER_ID)
        r = client.get("/api/notifications", params={
            "user_id": USER_ID, "type": "payout_sent", "unread_only": True,
        })
        assert r.json()["total"] == 1
        assert r.json()["items"][0]["message"] == "p2"

    def test_create_and_immediately_list(self):
        """Notification appears in listing immediately after creation."""
        r = client.post("/api/notifications", json={
            "type": "pr_submitted", "message": "PR #42 submitted",
            "user_id": USER_ID, "bounty_id": "b-99",
        })
        assert r.status_code == 201
        nid = r.json()["id"]
        listing = client.get("/api/notifications", params={"user_id": USER_ID})
        assert any(item["id"] == nid for item in listing.json()["items"])
