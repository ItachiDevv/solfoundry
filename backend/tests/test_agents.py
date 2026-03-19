"""Tests for agent registry API."""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services import agent_service

client = TestClient(app)

VALID_AGENT = {
    "name": "ReviewBot-1",
    "owner_wallet": "A" * 44,  # Solana base-58 addresses are 32-44 chars
    "capabilities": ["code-review", "security-audit"],
    "model": "gpt-5.4",
    "endpoint_url": "https://agent.example.com/callback",
}


@pytest.fixture(autouse=True)
def clear_store():
    agent_service._store.clear()
    yield
    agent_service._store.clear()


# ---------------------------------------------------------------------------
# POST /api/agents
# ---------------------------------------------------------------------------


def test_register_agent_success():
    resp = client.post("/api/agents", json=VALID_AGENT)
    assert resp.status_code == 201
    body = resp.json()
    assert body["name"] == "ReviewBot-1"
    assert body["status"] == "offline"
    assert body["stats"]["bounties_attempted"] == 0
    assert body["stats"]["success_rate"] == 0.0


def test_register_duplicate_name():
    client.post("/api/agents", json=VALID_AGENT)
    resp = client.post("/api/agents", json=VALID_AGENT)
    assert resp.status_code == 409


def test_register_invalid_wallet_too_short():
    bad = {**VALID_AGENT, "owner_wallet": "short"}
    resp = client.post("/api/agents", json=bad)
    assert resp.status_code == 422


def test_register_missing_name():
    bad = {k: v for k, v in VALID_AGENT.items() if k != "name"}
    resp = client.post("/api/agents", json=bad)
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# GET /api/agents
# ---------------------------------------------------------------------------


def test_list_empty():
    resp = client.get("/api/agents")
    assert resp.status_code == 200
    assert resp.json()["total"] == 0


def test_list_with_data():
    client.post("/api/agents", json=VALID_AGENT)
    agent2 = {**VALID_AGENT, "name": "AuditBot-2"}
    client.post("/api/agents", json=agent2)
    resp = client.get("/api/agents")
    assert resp.json()["total"] == 2


def test_list_filter_by_role():
    client.post("/api/agents", json=VALID_AGENT)
    agent2 = {**VALID_AGENT, "name": "DocBot", "capabilities": ["documentation"]}
    client.post("/api/agents", json=agent2)
    resp = client.get("/api/agents?role=code-review")
    assert resp.json()["total"] == 1
    assert resp.json()["items"][0]["name"] == "ReviewBot-1"


def test_list_filter_by_status():
    client.post("/api/agents", json=VALID_AGENT)
    resp = client.get("/api/agents?status=offline")
    assert resp.json()["total"] == 1
    resp = client.get("/api/agents?status=online")
    assert resp.json()["total"] == 0


def test_list_pagination():
    for i in range(5):
        client.post("/api/agents", json={**VALID_AGENT, "name": f"bot-{i}"})
    resp = client.get("/api/agents?skip=0&limit=2")
    body = resp.json()
    assert body["total"] == 5
    assert len(body["items"]) == 2


# ---------------------------------------------------------------------------
# GET /api/agents/{id}
# ---------------------------------------------------------------------------


def test_get_agent_by_id():
    create_resp = client.post("/api/agents", json=VALID_AGENT)
    agent_id = create_resp.json()["id"]
    resp = client.get(f"/api/agents/{agent_id}")
    assert resp.status_code == 200
    assert resp.json()["name"] == "ReviewBot-1"


def test_get_agent_not_found():
    resp = client.get("/api/agents/nonexistent-id")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# PATCH /api/agents/{id}
# ---------------------------------------------------------------------------


def test_update_agent():
    create_resp = client.post("/api/agents", json=VALID_AGENT)
    agent_id = create_resp.json()["id"]
    resp = client.patch(
        f"/api/agents/{agent_id}",
        json={"capabilities": ["code-review", "bug-fix"]},
    )
    assert resp.status_code == 200
    assert "bug-fix" in resp.json()["capabilities"]


def test_update_agent_not_found():
    resp = client.patch("/api/agents/nope", json={"name": "x"})
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# POST /api/agents/{id}/heartbeat
# ---------------------------------------------------------------------------


def test_heartbeat_brings_agent_online():
    create_resp = client.post("/api/agents", json=VALID_AGENT)
    agent_id = create_resp.json()["id"]
    assert create_resp.json()["status"] == "offline"

    hb_resp = client.post(f"/api/agents/{agent_id}/heartbeat")
    assert hb_resp.status_code == 200
    assert hb_resp.json()["status"] == "online"

    # Agent detail should now show online
    detail = client.get(f"/api/agents/{agent_id}").json()
    assert detail["status"] == "online"


def test_heartbeat_not_found():
    resp = client.post("/api/agents/missing/heartbeat")
    assert resp.status_code == 404


def test_heartbeat_suspended_stays_suspended():
    create_resp = client.post("/api/agents", json=VALID_AGENT)
    agent_id = create_resp.json()["id"]
    # Manually suspend
    db = agent_service._store[agent_id]
    db.status = "suspended"

    hb_resp = client.post(f"/api/agents/{agent_id}/heartbeat")
    assert hb_resp.json()["status"] == "suspended"
