"""Tests for contributor profiles API -- PostgreSQL migration."""

import uuid

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services import contributor_service

client = TestClient(app)


@pytest.fixture(autouse=True)
def clear_store():
    """Reset the in-memory store before and after every test."""
    contributor_service._store.clear()
    yield
    contributor_service._store.clear()


def _create(username="alice", display_name=None, skills=None, badges=None):
    """Helper — uses username.capitalize() as default display_name."""
    from app.models.contributor import ContributorCreate

    return contributor_service.create_contributor(
        ContributorCreate(
            username=username,
            display_name=display_name or username.capitalize(),
            skills=skills or ["python"],
            badges=badges or [],
        )
    )


def test_create_success():
    resp = client.post(
        "/api/contributors", json={"username": "alice", "display_name": "Alice"}
    )
    assert resp.status_code == 201
    assert resp.json()["username"] == "alice"
    assert resp.json()["stats"]["total_contributions"] == 0


def test_create_duplicate():
    _create("bob")
    resp = client.post(
        "/api/contributors", json={"username": "bob", "display_name": "Bob"}
    )
    assert resp.status_code == 409


def test_create_invalid_username():
    resp = client.post(
        "/api/contributors", json={"username": "a b", "display_name": "Bad"}
    )
    assert resp.status_code == 422


def test_list_empty():
    resp = client.get("/api/contributors")
    assert resp.json()["total"] == 0


def test_list_with_data():
    _create("alice")
    _create("bob")
    assert client.get("/api/contributors").json()["total"] == 2


def test_search():
    _create("alice")
    _create("bob")
    resp = client.get("/api/contributors?search=alice")
    assert resp.json()["total"] == 1


def test_filter_skills():
    _create("alice", skills=["python", "rust"])
    _create("bob", skills=["javascript"])
    resp = client.get("/api/contributors?skills=rust")
    assert resp.json()["total"] == 1


def test_filter_badges():
    _create("alice", badges=["early_adopter"])
    resp = client.get("/api/contributors?badges=early_adopter")
    assert resp.json()["total"] == 1


def test_pagination():
    for i in range(5):
        _create(f"user{i}")
    resp = client.get("/api/contributors?skip=0&limit=2")
    assert resp.json()["total"] == 5
    assert len(resp.json()["items"]) == 2


def test_get_by_id():
    c = _create("alice")
    resp = client.get(f"/api/contributors/{c.id}")
    assert resp.status_code == 200


def test_get_not_found():
    assert client.get("/api/contributors/nope").status_code == 404


def test_update():
    c = _create("alice")
    resp = client.patch(f"/api/contributors/{c.id}", json={"display_name": "Updated"})
    assert resp.json()["display_name"] == "Updated"


def test_delete():
    c = _create("alice")
    assert client.delete(f"/api/contributors/{c.id}").status_code == 204


# ---- Additional coverage for PostgreSQL migration --------------------------


def test_search_case_insensitive():
    _create("alice")
    assert client.get("/api/contributors?search=ALICE").json()["total"] == 1


def test_partial_update_preserves_fields():
    c = _create("alice", skills=["python"], badges=["tier-1"])
    client.patch(f"/api/contributors/{c.id}", json={"bio": "New bio"})
    data = client.get(f"/api/contributors/{c.id}").json()
    assert data["bio"] == "New bio" and data["skills"] == ["python"]


def test_delete_removes_from_store():
    c = _create("alice")
    client.delete(f"/api/contributors/{c.id}")
    assert client.get(f"/api/contributors/{c.id}").status_code == 404


def test_delete_not_found():
    assert client.delete("/api/contributors/nonexistent").status_code == 404


def test_stats_default_to_zero():
    c = _create("newuser")
    assert c.stats.total_contributions == 0 and c.stats.total_earnings == 0.0


def test_get_by_username_service():
    _create("alice")
    assert contributor_service.get_contributor_by_username("alice").username == "alice"
