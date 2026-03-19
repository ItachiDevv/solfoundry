"""Tests for the rate limiting middleware."""

import pytest
from unittest.mock import patch
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.middleware.rate_limit import RateLimitMiddleware, _InMemoryStore


@pytest.fixture
def store():
    s = _InMemoryStore()
    yield s
    s.reset()


class TestInMemoryStore:
    def test_first_request_passes(self, store):
        limited, info = store.is_rate_limited("test_key", max_requests=5, window_seconds=60)
        assert limited is False
        assert info["limit"] == 5
        assert info["remaining"] >= 3

    def test_exceeds_limit(self, store):
        for _ in range(5):
            store.is_rate_limited("test_key", max_requests=5, window_seconds=60)
        limited, info = store.is_rate_limited("test_key", max_requests=5, window_seconds=60)
        assert limited is True
        assert info["remaining"] == 0

    def test_different_keys_independent(self, store):
        for _ in range(5):
            store.is_rate_limited("key_a", max_requests=5, window_seconds=60)
        limited, _ = store.is_rate_limited("key_b", max_requests=5, window_seconds=60)
        assert limited is False

    def test_window_expiry(self, store):
        import time
        # Use a very short window
        for _ in range(3):
            store.is_rate_limited("expire_key", max_requests=3, window_seconds=0.1)
        limited, _ = store.is_rate_limited("expire_key", max_requests=3, window_seconds=0.1)
        assert limited is True
        # Wait for window to expire
        time.sleep(0.15)
        limited, _ = store.is_rate_limited("expire_key", max_requests=3, window_seconds=0.1)
        assert limited is False

    def test_reset(self, store):
        store.is_rate_limited("key", max_requests=1, window_seconds=60)
        store.reset()
        limited, _ = store.is_rate_limited("key", max_requests=1, window_seconds=60)
        assert limited is False


class TestRateLimitMiddleware:
    def _make_app(self, limits=None, enabled=True):
        app = FastAPI()
        app.add_middleware(
            RateLimitMiddleware,
            limits=limits or {"/test": (3, 60.0)},
            enabled=enabled,
        )

        @app.get("/test")
        async def test_endpoint():
            return {"ok": True}

        @app.get("/other")
        async def other_endpoint():
            return {"ok": True}

        return TestClient(app)

    def test_allows_under_limit(self):
        client = self._make_app()
        resp = client.get("/test")
        assert resp.status_code == 200
        assert "X-RateLimit-Limit" in resp.headers

    def test_returns_429_over_limit(self):
        client = self._make_app()
        for _ in range(3):
            client.get("/test")
        resp = client.get("/test")
        assert resp.status_code == 429
        assert resp.json()["detail"] == "Too many requests"
        assert "Retry-After" in resp.headers

    def test_disabled_middleware(self):
        client = self._make_app(enabled=False)
        for _ in range(10):
            resp = client.get("/test")
            assert resp.status_code == 200

    def test_rate_limit_headers_present(self):
        client = self._make_app()
        resp = client.get("/test")
        assert "X-RateLimit-Limit" in resp.headers
        assert "X-RateLimit-Remaining" in resp.headers
        assert "X-RateLimit-Reset" in resp.headers

    def test_different_paths_different_limits(self):
        client = self._make_app(limits={
            "/test": (2, 60.0),
            "/other": (100, 60.0),
        })
        for _ in range(2):
            client.get("/test")
        # /test should be limited
        resp = client.get("/test")
        assert resp.status_code == 429
        # /other should still work
        resp = client.get("/other")
        assert resp.status_code == 200

    def test_x_forwarded_for_header(self):
        client = self._make_app(limits={"/test": (2, 60.0)})
        for _ in range(2):
            client.get("/test", headers={"X-Forwarded-For": "1.2.3.4"})
        resp = client.get("/test", headers={"X-Forwarded-For": "1.2.3.4"})
        assert resp.status_code == 429
        # Different IP should work
        resp = client.get("/test", headers={"X-Forwarded-For": "5.6.7.8"})
        assert resp.status_code == 200
