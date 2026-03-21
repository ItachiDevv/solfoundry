"""Tests for the Leaderboard service -- PostgreSQL migration."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.contributor import ContributorDB
from app.services.contributor_service import _store
from app.services.leaderboard_service import get_leaderboard, invalidate_cache

client = TestClient(app)

# Helper to call service directly (tests structured LeaderboardResponse)
_lb = get_leaderboard


def _seed_contributor(
    username: str,
    display_name: str,
    total_earnings: float = 0.0,
    bounties_completed: int = 0,
    reputation: int = 0,
    skills: list[str] | None = None,
    badges: list[str] | None = None,
) -> ContributorDB:
    """Insert a contributor directly into the in-memory store."""
    db = ContributorDB(
        id=uuid.uuid4(),
        username=username,
        display_name=display_name,
        total_earnings=total_earnings,
        total_bounties_completed=bounties_completed,
        reputation_score=reputation,
        skills=skills or [],
        badges=badges or [],
        avatar_url=f"https://github.com/{username}.png",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    _store[str(db.id)] = db
    return db


@pytest.fixture(autouse=True)
def _clean():
    """Reset store and cache before every test."""
    _store.clear()
    invalidate_cache()
    yield
    _store.clear()
    invalidate_cache()


# ── Basic endpoint tests ─────────────────────────────────────────────────


def test_empty_leaderboard():
    data = _lb()
    assert data.total == 0
    assert data.entries == []
    assert data.top3 == []


def test_single_contributor():
    _seed_contributor(
        "alice", "Alice A", total_earnings=500.0, bounties_completed=3, reputation=80
    )

    data = _lb()
    assert data.total == 1
    assert len(data.entries) == 1
    assert data.entries[0].rank == 1
    assert data.entries[0].username == "alice"
    assert data.entries[0].total_earned == 500.0


def test_ranking_order():
    _seed_contributor("low", "Low Earner", total_earnings=100.0)
    _seed_contributor("mid", "Mid Earner", total_earnings=500.0)
    _seed_contributor("top", "Top Earner", total_earnings=1000.0)

    data = _lb()
    assert data.total == 3
    usernames = [e.username for e in data.entries]
    assert usernames == ["top", "mid", "low"]
    assert data.entries[0].rank == 1
    assert data.entries[2].rank == 3


def test_top3_medals():
    _seed_contributor("gold", "Gold", total_earnings=1000.0)
    _seed_contributor("silver", "Silver", total_earnings=500.0)
    _seed_contributor("bronze", "Bronze", total_earnings=250.0)

    data = _lb()
    assert len(data.top3) == 3
    assert data.top3[0].meta.medal == "\U0001f947"
    assert data.top3[1].meta.medal == "\U0001f948"
    assert data.top3[2].meta.medal == "\U0001f949"


def test_top3_with_fewer_than_3():
    _seed_contributor("solo", "Solo", total_earnings=100.0)

    data = _lb()
    assert len(data.top3) == 1
    assert data.top3[0].meta.medal == "\U0001f947"


# ── Filter tests ─────────────────────────────────────────────────────────


def test_filter_by_category():
    _seed_contributor("fe_dev", "FE Dev", total_earnings=300.0, skills=["frontend"])
    _seed_contributor("be_dev", "BE Dev", total_earnings=600.0, skills=["backend"])

    from app.models.leaderboard import CategoryFilter
    data = _lb(category=CategoryFilter.frontend)
    assert data.total == 1
    assert data.entries[0].username == "fe_dev"


def test_filter_by_tier():
    _seed_contributor("t1_dev", "T1 Dev", total_earnings=200.0, badges=["tier-1"])
    _seed_contributor("t2_dev", "T2 Dev", total_earnings=800.0, badges=["tier-2"])

    from app.models.leaderboard import TierFilter
    data = _lb(tier=TierFilter.t1)
    assert data.total == 1
    assert data.entries[0].username == "t1_dev"


def test_filter_by_period_all():
    _seed_contributor("old", "Old Timer", total_earnings=900.0)

    data = _lb()
    assert data.total == 1
    assert data.period == "all"


# ── Pagination tests ─────────────────────────────────────────────────────


def test_pagination_limit():
    for i in range(5):
        _seed_contributor(f"user{i}", f"User {i}", total_earnings=float(100 * (5 - i)))

    data = _lb(limit=2, offset=0)
    assert data.total == 5
    assert len(data.entries) == 2
    assert data.entries[0].rank == 1


def test_pagination_offset():
    for i in range(5):
        _seed_contributor(f"user{i}", f"User {i}", total_earnings=float(100 * (5 - i)))

    data = _lb(limit=2, offset=2)
    assert len(data.entries) == 2
    assert data.entries[0].rank == 3


def test_pagination_beyond_total():
    _seed_contributor("only", "Only One", total_earnings=100.0)

    data = _lb(limit=10, offset=5)
    assert data.total == 1
    assert len(data.entries) == 0


# ── Tiebreaker test ─────────────────────────────────────────────────────


def test_tiebreaker_reputation_then_username():
    _seed_contributor("bob", "Bob", total_earnings=500.0, reputation=90)
    _seed_contributor("alice", "Alice", total_earnings=500.0, reputation=100)
    _seed_contributor("charlie", "Charlie", total_earnings=500.0, reputation=90)

    data = _lb()
    usernames = [e.username for e in data.entries]
    # alice has higher reputation, then bob < charlie alphabetically
    assert usernames == ["alice", "bob", "charlie"]


# ── Cache test ───────────────────────────────────────────────────────────


def test_cache_returns_same_result():
    _seed_contributor("cached", "Cached", total_earnings=100.0)
    assert _lb().total == _lb().total


def test_cache_invalidation():
    _seed_contributor("first", "First", total_earnings=100.0)
    assert _lb().total == 1
    invalidate_cache()
    _seed_contributor("second", "Second", total_earnings=200.0)
    assert _lb().total == 2


# ── API route tests (frontend JSON array format) ───────────────────────


def test_api_returns_200():
    assert client.get("/api/leaderboard").status_code == 200


def test_api_empty_array():
    assert client.get("/api/leaderboard").json() == []


def test_api_ranked():
    _seed_contributor("top", "Top", total_earnings=1000.0)
    data = client.get("/api/leaderboard").json()
    assert data[0]["username"] == "top" and data[0]["rank"] == 1
