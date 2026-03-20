"""Tests for the Search & Filter Engine (Issue #30).

Uses pytest parametrize extensively to avoid repeated test boilerplate.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.bounty import BountyDB, BountyStatus, BountyTier
from app.services.bounty_service import _bounty_store

client = TestClient(app)

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _seed(overrides: dict | None = None) -> BountyDB:
    """Create a bounty with sensible defaults, applying *overrides*."""
    now = datetime.now(timezone.utc)
    defaults = dict(
        id=str(uuid.uuid4()), title="Default Bounty", description="desc",
        tier=BountyTier.T1, reward_amount=100.0, status=BountyStatus.OPEN,
        required_skills=[], deadline=None, created_by="system",
        created_at=now, updated_at=now,
    )
    defaults.update(overrides or {})
    bounty = BountyDB(**defaults)
    _bounty_store[bounty.id] = bounty
    return bounty


def _get(path: str = "/api/bounties/search", **params) -> dict:
    """GET helper that asserts 200 and returns JSON body."""
    resp = client.get(path, params=params)
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    return resp.json()


def _titles(data: dict) -> list[str]:
    """Extract ordered list of titles from a search response."""
    return [item["title"] for item in data["items"]]


@pytest.fixture(autouse=True)
def _clean_store():
    _bounty_store.clear()
    yield
    _bounty_store.clear()


# ===========================================================================
# Basic text search
# ===========================================================================

class TestTextSearch:
    def test_empty_store(self):
        data = _get()
        assert data["total"] == 0 and data["items"] == []

    def test_no_query_returns_all(self):
        for label in ("A", "B", "C"):
            _seed({"title": f"Bounty {label}"})
        assert _get()["total"] == 3

    @pytest.mark.parametrize("field,seed_kw,query", [
        ("title", {"title": "Solana bridge"}, "solana"),
        ("description", {"title": "X", "description": "Redis caching layer"}, "redis"),
        ("skills", {"title": "Y", "required_skills": ["python", "fastapi"]}, "python"),
    ], ids=["in_title", "in_description", "in_skills"])
    def test_keyword_match_by_field(self, field, seed_kw, query):
        _seed(seed_kw)
        _seed({"title": "Unrelated task"})
        data = _get(q=query)
        assert data["total"] == 1

    def test_case_insensitive(self):
        _seed({"title": "SOLANA Integration"})
        _seed({"title": "solana bridge"})
        assert _get(q="Solana")["total"] == 2

    def test_no_match(self):
        _seed({"title": "Something"})
        data = _get(q="zznonexistent")
        assert data["total"] == 0

    def test_response_echoes_query(self):
        assert _get(q="test")["query"] == "test"

    def test_multi_word_query(self):
        _seed({"title": "Smart contract audit"})
        _seed({"title": "Logo design"})
        data = _get(q="smart contract")
        assert data["total"] == 1 and data["items"][0]["title"] == "Smart contract audit"


# ===========================================================================
# Filters (parametrized)
# ===========================================================================

class TestFilters:
    def test_filter_by_tier(self):
        for t in (BountyTier.T1, BountyTier.T2, BountyTier.T3):
            _seed({"title": f"Tier {t.value}", "tier": t})
        data = _get(tier=1)
        assert data["total"] == 1 and data["items"][0]["tier"] == 1

    def test_filter_by_status(self):
        for st in (BountyStatus.OPEN, BountyStatus.COMPLETED, BountyStatus.PAID):
            _seed({"title": st.value, "status": st})
        data = _get(status="open")
        assert data["total"] == 1 and data["items"][0]["status"] == "open"

    @pytest.mark.parametrize("param,value,amounts,expected_count", [
        ("reward_min", 100, [50, 200, 500], 2),
        ("reward_max", 200, [50, 200, 500], 2),
    ], ids=["min_bound", "max_bound"])
    def test_reward_boundary(self, param, value, amounts, expected_count):
        for amt in amounts:
            _seed({"title": f"R{amt}", "reward_amount": amt})
        data = _get(**{param: value})
        assert data["total"] == expected_count

    def test_reward_range(self):
        for amt in (10, 50, 200, 500):
            _seed({"title": f"R{amt}", "reward_amount": float(amt)})
        data = _get(reward_min=50, reward_max=200)
        assert data["total"] == 2
        assert all(50 <= i["reward_amount"] <= 200 for i in data["items"])

    def test_skills_intersection(self):
        _seed({"title": "py", "required_skills": ["python"]})
        _seed({"title": "py+rs", "required_skills": ["python", "rust"]})
        _seed({"title": "rs", "required_skills": ["rust"]})
        data = _get(skills="python,rust")
        assert data["total"] == 1 and data["items"][0]["title"] == "py+rs"

    def test_combined_filters(self):
        _seed({"title": "Match", "tier": BountyTier.T1, "status": BountyStatus.OPEN, "reward_amount": 150.0})
        _seed({"title": "WrongTier", "tier": BountyTier.T2, "status": BountyStatus.OPEN, "reward_amount": 150.0})
        _seed({"title": "WrongStatus", "tier": BountyTier.T1, "status": BountyStatus.COMPLETED, "reward_amount": 150.0})
        data = _get(tier=1, status="open", reward_min=100)
        assert data["total"] == 1 and data["items"][0]["title"] == "Match"

    def test_search_plus_filter(self):
        _seed({"title": "Solana DeFi", "tier": BountyTier.T1, "reward_amount": 300.0})
        _seed({"title": "Solana NFT", "tier": BountyTier.T2, "reward_amount": 500.0})
        _seed({"title": "React app", "tier": BountyTier.T1, "reward_amount": 200.0})
        data = _get(q="solana", tier=1)
        assert data["total"] == 1 and data["items"][0]["title"] == "Solana DeFi"

    def test_filters_applied_in_response(self):
        data = _get(tier=1, status="open", reward_min=100)
        fa = data["filters_applied"]
        assert fa["tier"] == 1 and fa["status"] == "open" and fa["reward_min"] == 100.0


# ===========================================================================
# Sorting
# ===========================================================================

class TestSorting:
    @pytest.mark.parametrize("sort_val,expected_order", [
        ("newest", ["New", "Mid", "Old"]),
        ("oldest", ["Old", "Mid", "New"]),
    ], ids=["newest_first", "oldest_first"])
    def test_chronological(self, sort_val, expected_order):
        now = datetime.now(timezone.utc)
        for label, offset in [("Old", 10), ("New", 0), ("Mid", 5)]:
            _seed({"title": label, "created_at": now - timedelta(days=offset)})
        assert _titles(_get(sort=sort_val)) == expected_order

    @pytest.mark.parametrize("sort_val,expected_amounts", [
        ("reward_high", [500.0, 200.0, 50.0]),
        ("reward_low", [50.0, 200.0, 500.0]),
    ], ids=["high_first", "low_first"])
    def test_reward_sort(self, sort_val, expected_amounts):
        for amt in (50, 500, 200):
            _seed({"title": f"R{amt}", "reward_amount": float(amt)})
        amounts = [i["reward_amount"] for i in _get(sort=sort_val)["items"]]
        assert amounts == expected_amounts

    def test_deadline_soonest(self):
        now = datetime.now(timezone.utc)
        _seed({"title": "NoDeadline", "deadline": None})
        _seed({"title": "Soon", "deadline": now + timedelta(days=1)})
        _seed({"title": "Later", "deadline": now + timedelta(days=7)})
        assert _titles(_get(sort="deadline_soonest")) == ["Soon", "Later", "NoDeadline"]

    def test_text_search_defaults_to_relevance(self):
        _seed({"title": "Solana", "description": "Solana smart contract on Solana"})
        _seed({"title": "Solana blockchain", "description": "Something else"})
        _seed({"title": "Fix CSS bug", "description": "Solana related maybe"})
        data = _get(q="solana")
        assert data["items"][0]["title"] == "Solana"


# ===========================================================================
# Pagination
# ===========================================================================

class TestPagination:
    def test_defaults(self):
        for i in range(5):
            _seed({"title": f"B{i}"})
        data = _get()
        assert data["page"] == 1 and data["page_size"] == 20 and len(data["items"]) == 5

    def test_custom_page_size(self):
        for i in range(10):
            _seed({"title": f"B{i}"})
        data = _get(page_size=3)
        assert len(data["items"]) == 3 and data["total_pages"] == 4

    def test_page_navigation(self):
        now = datetime.now(timezone.utc)
        for i in range(5):
            _seed({"title": f"B{i}", "created_at": now - timedelta(hours=i)})
        p1 = _get(page=1, page_size=2, sort="newest")
        p2 = _get(page=2, page_size=2, sort="newest")
        p3 = _get(page=3, page_size=2, sort="newest")
        assert len(p1["items"]) == 2 and len(p2["items"]) == 2 and len(p3["items"]) == 1

    def test_beyond_last_page(self):
        _seed({"title": "Only"})
        data = _get(page=99, page_size=10)
        assert data["items"] == [] and data["total"] == 1

    def test_total_pages_math(self):
        for i in range(7):
            _seed({"title": f"B{i}"})
        assert _get(page_size=3)["total_pages"] == 3


# ===========================================================================
# Autocomplete
# ===========================================================================

class TestAutocomplete:
    def _ac(self, **params) -> dict:
        return _get(path="/api/bounties/autocomplete", **params)

    def test_prefix_match(self):
        _seed({"title": "Solana DeFi bridge"})
        _seed({"title": "Solana NFT market"})
        _seed({"title": "React dashboard"})
        data = self._ac(q="sol")
        assert len(data["suggestions"]) == 2 and data["query"] == "sol"

    def test_substring_fallback(self):
        _seed({"title": "Build Solana bridge"})
        _seed({"title": "React app"})
        data = self._ac(q="solana")
        assert len(data["suggestions"]) == 1

    def test_limit(self):
        for i in range(15):
            _seed({"title": f"Solana project {i}"})
        assert len(self._ac(q="sol", limit=5)["suggestions"]) == 5

    def test_no_match(self):
        _seed({"title": "React app"})
        assert len(self._ac(q="xyz")["suggestions"]) == 0

    def test_empty_query_rejected(self):
        resp = client.get("/api/bounties/autocomplete", params={"q": ""})
        assert resp.status_code == 422

    def test_returns_metadata(self):
        _seed({"title": "Solana task", "tier": BountyTier.T2, "reward_amount": 250.0})
        s = self._ac(q="sol")["suggestions"][0]
        assert s["tier"] == 2 and s["reward_amount"] == 250.0 and s["status"] == "open"

    def test_prefix_ranked_first(self):
        _seed({"title": "Build Solana bridge"})
        _seed({"title": "Solana DeFi project"})
        titles = [s["title"] for s in self._ac(q="sol")["suggestions"]]
        assert titles[0] == "Solana DeFi project"


# ===========================================================================
# Relevance scoring
# ===========================================================================

class TestRelevance:
    def test_exact_title_ranks_highest(self):
        _seed({"title": "Solana", "description": "Desc"})
        _seed({"title": "Build Solana bridge", "description": "Desc"})
        data = _get(q="solana")
        assert data["items"][0]["title"] == "Solana"
        assert data["items"][0]["relevance_score"] > data["items"][1]["relevance_score"]

    def test_title_beats_description(self):
        _seed({"title": "Solana project", "description": "Simple"})
        _seed({"title": "Random task", "description": "Uses Solana"})
        assert _get(q="solana")["items"][0]["title"] == "Solana project"

    def test_scores_are_positive(self):
        _seed({"title": "Solana DeFi"})
        assert _get(q="solana")["items"][0]["relevance_score"] > 0


# ===========================================================================
# Edge cases & security
# ===========================================================================

class TestEdgeCases:
    @pytest.mark.parametrize("param,value", [
        ("tier", 5),
        ("reward_min", -10),
        ("page", 0),
        ("page_size", 200),
        ("sort", "invalid"),
    ], ids=["bad_tier", "negative_reward", "page_zero", "oversized_page", "bad_sort"])
    def test_validation_rejects_bad_params(self, param, value):
        resp = client.get("/api/bounties/search", params={param: value})
        assert resp.status_code == 422

    @pytest.mark.parametrize("dangerous_input", [
        "'; DROP TABLE bounties; --",
        "<script>alert(1)</script>",
        "' OR '1'='1",
        "UNION SELECT * FROM users",
        "../../../etc/passwd",
    ], ids=["sql_inject", "xss", "or_inject", "union_inject", "path_traversal"])
    def test_malicious_queries_return_safe_empty(self, dangerous_input):
        data = _get(q=dangerous_input)
        assert isinstance(data["items"], list)
        assert data["total"] >= 0

    def test_empty_filters_return_all(self):
        _seed({"title": "A"})
        _seed({"title": "B"})
        assert _get()["total"] == 2

    def test_result_has_all_expected_fields(self):
        now = datetime.now(timezone.utc)
        _seed({
            "title": "Complete bounty", "description": "Full desc",
            "tier": BountyTier.T2, "reward_amount": 300.0,
            "required_skills": ["python", "rust"],
            "deadline": now + timedelta(days=7), "created_by": "admin",
        })
        item = _get()["items"][0]
        for key in ("id", "title", "description", "tier", "reward_amount",
                     "status", "required_skills", "deadline", "created_by",
                     "created_at", "updated_at", "relevance_score"):
            assert key in item, f"Missing field: {key}"

    def test_reward_min_equals_max(self):
        _seed({"title": "Exact", "reward_amount": 100.0})
        _seed({"title": "Other", "reward_amount": 200.0})
        data = _get(reward_min=100, reward_max=100)
        assert data["total"] == 1 and data["items"][0]["reward_amount"] == 100.0

    def test_very_long_query(self):
        long_q = "a" * 500
        data = _get(q=long_q)
        assert data["total"] == 0

    def test_unicode_query(self):
        _seed({"title": "Ethereum bridge"})
        data = _get(q="brucke")
        assert isinstance(data["items"], list)
