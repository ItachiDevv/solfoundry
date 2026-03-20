"""Tests for PostgreSQL full migration (Issue #162)."""

import os
from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.models.bounty import BountyCreate, BountyStatus, BountyTier
from app.models.contributor import ContributorCreate, ContributorDB
from app.models.payout import PayoutCreate, PayoutRecord, PayoutStatus
from app.services import bounty_service, contributor_service
from app.services.payout_service import create_payout, reset_stores

client = TestClient(app)
TX = chr(65) * 88


@pytest.fixture(autouse=True)
def clear_stores():
    """Reset all in-memory stores."""
    bounty_service._bounty_store.clear()
    contributor_service._store.clear()
    reset_stores()
    yield
    bounty_service._bounty_store.clear()
    contributor_service._store.clear()
    reset_stores()


def test_payout_table_columns():
    """PayoutTable has required columns."""
    from app.models.payout_table import PayoutTable
    cols = {c.name for c in PayoutTable.__table__.columns}
    assert {"id", "recipient", "amount", "tx_hash", "status"} <= cols


def test_buyback_table_columns():
    """BuybackTable has required columns."""
    from app.models.payout_table import BuybackTable
    assert {"id", "amount_sol", "amount_fndry"} <= {c.name for c in BuybackTable.__table__.columns}


def test_contributor_shared_base():
    """ContributorDB uses app.database.Base."""
    from app.database import Base
    assert ContributorDB.__table__ in Base.metadata.sorted_tables


def test_all_tables_registered():
    """All ORM models on Base metadata."""
    from app.database import Base
    from app.models.payout_table import PayoutTable, BuybackTable  # noqa: F401
    from app.models.bounty_table import BountyTable  # noqa: F401
    names = {t.name for t in Base.metadata.sorted_tables}
    for t in ["bounties", "contributors", "payouts", "buybacks"]:
        assert t in names


def test_bounty_roundtrip():
    """BountyCreate -> BountyResponse preserves fields."""
    r = bounty_service.create_bounty(BountyCreate(title="Migration Test", reward_amount=1.0))
    assert r.title == "Migration Test" and r.status == BountyStatus.OPEN


def test_contributor_roundtrip():
    """ContributorCreate -> ContributorResponse with correct defaults."""
    r = contributor_service.create_contributor(
        ContributorCreate(username="user1", display_name="User"))
    assert r.username == "user1" and r.stats.total_contributions == 0


def test_payout_status():
    """PayoutRecord maps status correctly."""
    assert PayoutRecord(recipient="a", amount=1.0, status=PayoutStatus.PENDING).status == PayoutStatus.PENDING


@pytest.mark.asyncio
async def test_load_all_empty():
    """Loading from empty DB returns zero counts."""
    from app.services.persistence_service import load_all_from_database
    r = await load_all_from_database()
    assert r["bounties"] == 0 and r["contributors"] == 0 and r["payouts"] == 0


@pytest.mark.asyncio
async def test_load_db_errors():
    """Load functions handle DB errors gracefully."""
    from app.services.persistence_service import (
        load_bounties_from_database, load_contributors_from_database, load_payouts_from_database)
    for fn in [load_bounties_from_database, load_contributors_from_database, load_payouts_from_database]:
        with patch("app.services.persistence_service.get_db_session",
                   side_effect=Exception("fail")):
            assert await fn() == 0


@pytest.mark.asyncio
async def test_persist_missing_records():
    """Persist nonexistent records returns False."""
    from app.services.persistence_service import persist_payout, persist_buyback, persist_contributor
    assert await persist_payout("x") is False
    assert await persist_buyback("x") is False
    assert await persist_contributor("x") is False


@pytest.mark.asyncio
async def test_persist_db_errors():
    """Persist functions handle DB errors gracefully."""
    r = create_payout(PayoutCreate(recipient="a", amount=1.0))
    from app.services.persistence_service import persist_payout, delete_contributor_from_database
    with patch("app.services.persistence_service.get_db_session", side_effect=Exception("fail")):
        assert await persist_payout(r.id) is False
        assert await delete_contributor_from_database("x") is False


def test_bounty_api_shape():
    """POST /api/bounties returns expected schema."""
    r = client.post("/api/bounties", json={"title": "Migration Test", "reward_amount": 1.0})
    assert r.status_code == 201
    assert {"id", "title", "status", "created_at"} <= set(r.json().keys())


def test_contributor_api_lifecycle():
    """Full contributor CRUD with persistence hooks."""
    r = client.post("/api/contributors", json={"username": "test162", "display_name": "T"})
    assert r.status_code == 201
    cid = r.json()["id"]
    assert client.get(f"/api/contributors/{cid}").status_code == 200
    assert client.patch(f"/api/contributors/{cid}", json={"display_name": "U"}).status_code == 200
    assert client.delete(f"/api/contributors/{cid}").status_code == 204
    assert client.get(f"/api/contributors/{cid}").status_code == 404


def test_payout_api_shape():
    """POST /api/payouts returns expected schema with persistence."""
    r = client.post("/api/payouts", json={"recipient": "a", "amount": 1.0, "tx_hash": TX})
    assert r.status_code == 201 and r.json()["status"] == "confirmed"


def test_migration_script_exists():
    """Migration script exists with correct SQL."""
    path = os.path.join(os.path.dirname(__file__), "..",
                        "migrations", "002_postgresql_full_migration.py")
    assert os.path.exists(path)
    content = open(path).read()
    for table in ["contributors", "payouts", "buybacks"]:
        assert table in content
    assert "UPGRADE_SQL" in content and "DOWNGRADE_SQL" in content


def test_connection_pooling():
    """Pool settings are positive integers and session factory exists."""
    from app.database import POOL_SIZE, POOL_MAX_OVERFLOW, async_session_factory
    assert POOL_SIZE > 0 and POOL_MAX_OVERFLOW > 0 and async_session_factory is not None


def test_health_check():
    """Health endpoint works."""
    assert client.get("/health").json()["status"] == "ok"


def test_bounty_crud_lifecycle():
    """Full bounty CRUD works after migration."""
    r = client.post("/api/bounties", json={"title": "Zero Downtime", "reward_amount": 1.0})
    bid = r.json()["id"]
    assert client.patch(f"/api/bounties/{bid}", json={"status": "in_progress"}).status_code == 200
    assert client.delete(f"/api/bounties/{bid}").status_code == 204


def test_filters_and_pagination():
    """Filters and pagination work after migration."""
    for i in range(3):
        bounty_service.create_bounty(BountyCreate(
            title=f"Bounty {i}", reward_amount=1.0, tier=BountyTier.T1, required_skills=["python"]))
    assert client.get("/api/bounties?tier=1&skills=python").json()["total"] == 3
    body = client.get("/api/bounties?skip=0&limit=2").json()
    assert body["total"] == 3 and len(body["items"]) == 2


def test_submission_flow():
    """Bounty submission works after migration."""
    b = bounty_service.create_bounty(BountyCreate(title="Sub", reward_amount=1.0))
    r = client.post(f"/api/bounties/{b.id}/submit",
                    json={"pr_url": "https://github.com/o/r/pull/1", "submitted_by": "a"})
    assert r.status_code == 201
