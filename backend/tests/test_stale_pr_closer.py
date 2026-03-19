"""Tests for the stale PR closer script."""

import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone, timedelta
import json
import sys
import os

# Add the .github/scripts directory to the path for import
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".github", "scripts"))

import stale_pr_closer


@pytest.fixture(autouse=True)
def mock_env(monkeypatch):
    monkeypatch.setenv("GITHUB_REPOSITORY", "SolFoundry/solfoundry")
    monkeypatch.setenv("GH_TOKEN", "test-token")


class TestGetOpenPRsWithLabel:
    @patch("stale_pr_closer.requests.get")
    def test_returns_prs_with_label(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = [
            {
                "number": 1,
                "title": "Test PR",
                "labels": [{"name": "changes-requested"}],
                "user": {"login": "alice"},
            },
            {
                "number": 2,
                "title": "Other PR",
                "labels": [{"name": "bug"}],
                "user": {"login": "bob"},
            },
        ]
        # Second call returns empty (end pagination)
        mock_empty = MagicMock()
        mock_empty.status_code = 200
        mock_empty.json.return_value = []
        mock_get.side_effect = [mock_resp, mock_empty]

        prs = stale_pr_closer.get_open_prs_with_label("changes-requested")
        assert len(prs) == 1
        assert prs[0]["number"] == 1

    @patch("stale_pr_closer.requests.get")
    def test_handles_api_error(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_get.return_value = mock_resp

        prs = stale_pr_closer.get_open_prs_with_label("changes-requested")
        assert prs == []


class TestLabelAppliedAt:
    @patch("stale_pr_closer.requests.get")
    def test_finds_label_event(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = [
            {
                "event": "labeled",
                "label": {"name": "changes-requested"},
                "created_at": "2026-03-16T10:00:00Z",
            },
        ]
        mock_get.return_value = mock_resp

        dt = stale_pr_closer.label_applied_at(1, "changes-requested")
        assert dt is not None
        assert dt.year == 2026

    @patch("stale_pr_closer.requests.get")
    def test_returns_none_when_not_found(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = [
            {"event": "labeled", "label": {"name": "bug"}, "created_at": "2026-03-16T10:00:00Z"},
        ]
        mock_get.return_value = mock_resp

        dt = stale_pr_closer.label_applied_at(1, "changes-requested")
        assert dt is None


class TestLatestCommitDate:
    @patch("stale_pr_closer.requests.get")
    def test_returns_last_commit_date(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = [
            {"commit": {"committer": {"date": "2026-03-15T10:00:00Z"}}},
            {"commit": {"committer": {"date": "2026-03-17T10:00:00Z"}}},
        ]
        mock_get.return_value = mock_resp

        dt = stale_pr_closer.latest_commit_date(1)
        assert dt is not None
        assert dt.day == 17

    @patch("stale_pr_closer.requests.get")
    def test_returns_none_for_no_commits(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = []
        mock_get.return_value = mock_resp

        dt = stale_pr_closer.latest_commit_date(1)
        assert dt is None


class TestClosePR:
    @patch("stale_pr_closer.requests.patch")
    @patch("stale_pr_closer.requests.post")
    def test_posts_comment_and_closes(self, mock_post, mock_patch):
        mock_post.return_value = MagicMock(status_code=201)
        mock_patch.return_value = MagicMock(status_code=200)

        stale_pr_closer.close_pr(42, "Closing due to inactivity")

        # Should make 2 POST calls (comment + label) and 1 PATCH (close)
        assert mock_post.call_count == 2
        assert mock_patch.call_count == 1

        # Verify the close call
        close_call = mock_patch.call_args
        assert "closed" in str(close_call)


class TestNotifyTelegram:
    @patch("stale_pr_closer.requests.post")
    def test_sends_notification(self, mock_post, monkeypatch):
        monkeypatch.setenv("SOLFOUNDRY_TELEGRAM_BOT_TOKEN", "test-bot-token")
        monkeypatch.setenv("SOLFOUNDRY_TELEGRAM_CHAT_ID", "12345")
        mock_post.return_value = MagicMock(status_code=200)

        stale_pr_closer.notify_telegram([{
            "number": 1, "title": "Test PR", "author": "alice",
            "url": "https://github.com/test/1", "stale_hours": 80,
        }])

        mock_post.assert_called_once()
        call_json = mock_post.call_args.kwargs.get("json") or mock_post.call_args[1].get("json")
        assert "Stale PR Auto-Closer" in call_json["text"]

    @patch("stale_pr_closer.requests.post")
    def test_skips_when_no_telegram(self, mock_post, monkeypatch):
        monkeypatch.delenv("SOLFOUNDRY_TELEGRAM_BOT_TOKEN", raising=False)
        monkeypatch.delenv("SOLFOUNDRY_TELEGRAM_CHAT_ID", raising=False)
        stale_pr_closer.notify_telegram([{"number": 1}])
        mock_post.assert_not_called()

    def test_skips_empty_list(self, monkeypatch):
        monkeypatch.setenv("SOLFOUNDRY_TELEGRAM_BOT_TOKEN", "test")
        monkeypatch.setenv("SOLFOUNDRY_TELEGRAM_CHAT_ID", "123")
        # Should not raise
        stale_pr_closer.notify_telegram([])
