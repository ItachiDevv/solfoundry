"""
Rate limiting middleware for SolFoundry backend.

Supports per-IP and per-user rate limiting with configurable limits per endpoint.
Uses Redis when available, falls back to in-memory store for development.
Returns 429 Too Many Requests when limits are exceeded.
"""

import time
from collections import defaultdict
from typing import Optional

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse


class _InMemoryStore:
    """In-memory sliding-window rate limit store (dev fallback)."""

    def __init__(self):
        # key -> list of timestamps
        self._windows: dict[str, list[float]] = defaultdict(list)

    def _prune(self, key: str, window_seconds: float):
        cutoff = time.time() - window_seconds
        self._windows[key] = [t for t in self._windows[key] if t > cutoff]

    def is_rate_limited(self, key: str, max_requests: int, window_seconds: float) -> tuple[bool, dict]:
        """Check if a key exceeds its rate limit. Returns (limited, info_dict)."""
        now = time.time()
        self._prune(key, window_seconds)

        count = len(self._windows[key])
        remaining = max(0, max_requests - count)
        reset_at = int(now + window_seconds)

        info = {
            "limit": max_requests,
            "remaining": remaining,
            "reset": reset_at,
            "window": int(window_seconds),
        }

        if count >= max_requests:
            return True, info

        self._windows[key].append(now)
        info["remaining"] = max(0, remaining - 1)
        return False, info

    def reset(self):
        """Clear all stored windows."""
        self._windows.clear()


class _RedisStore:
    """Redis-backed sliding-window rate limit store."""

    def __init__(self, redis_client):
        self._redis = redis_client

    def is_rate_limited(self, key: str, max_requests: int, window_seconds: float) -> tuple[bool, dict]:
        now = time.time()
        redis_key = f"rl:{key}"

        pipe = self._redis.pipeline()
        pipe.zremrangebyscore(redis_key, 0, now - window_seconds)
        pipe.zcard(redis_key)
        pipe.zadd(redis_key, {str(now): now})
        pipe.expire(redis_key, int(window_seconds) + 1)
        results = pipe.execute()

        count = results[1]  # zcard result
        remaining = max(0, max_requests - count)
        reset_at = int(now + window_seconds)

        info = {
            "limit": max_requests,
            "remaining": remaining,
            "reset": reset_at,
            "window": int(window_seconds),
        }

        if count >= max_requests:
            return True, info

        info["remaining"] = max(0, remaining - 1)
        return False, info


# Default rate limits: {path_prefix: (max_requests, window_seconds)}
DEFAULT_LIMITS: dict[str, tuple[int, float]] = {
    "/api/spam/check": (30, 60.0),       # 30 checks per minute
    "/api/spam/config": (5, 60.0),        # 5 config changes per minute
    "/api/spam": (60, 60.0),              # 60 spam API calls per minute
    "/api/webhooks": (120, 60.0),         # 120 webhook calls per minute
    "/api/contributors": (60, 60.0),      # 60 contributor calls per minute
    "/api/leaderboard": (60, 60.0),       # 60 leaderboard calls per minute
    "/api": (100, 60.0),                  # Global fallback: 100/min
    "/health": (300, 60.0),               # Health check: generous
}


def _get_client_ip(request: Request) -> str:
    """Extract client IP, respecting X-Forwarded-For behind a proxy."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "unknown"


def _get_user_id(request: Request) -> Optional[str]:
    """Extract user ID from auth header if present (for per-user limiting)."""
    auth = request.headers.get("authorization")
    if auth and auth.startswith("Bearer "):
        # Use first 16 chars of token as user key (not the full secret)
        token = auth[7:]
        return f"user:{token[:16]}"
    return None


def _match_limit(path: str, limits: dict[str, tuple[int, float]]) -> tuple[int, float]:
    """Find the most specific rate limit matching a request path."""
    best_match = ("", (100, 60.0))
    for prefix, limit in limits.items():
        if path.startswith(prefix) and len(prefix) > len(best_match[0]):
            best_match = (prefix, limit)
    return best_match[1]


class RateLimitMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware for per-IP and per-user rate limiting."""

    def __init__(
        self,
        app,
        redis_url: Optional[str] = None,
        limits: Optional[dict[str, tuple[int, float]]] = None,
        enabled: bool = True,
    ):
        super().__init__(app)
        self.enabled = enabled
        self.limits = limits or DEFAULT_LIMITS

        # Try Redis; fall back to in-memory
        self._store: _InMemoryStore | _RedisStore
        if redis_url:
            try:
                import redis
                client = redis.from_url(redis_url)
                client.ping()
                self._store = _RedisStore(client)
            except Exception:
                self._store = _InMemoryStore()
        else:
            self._store = _InMemoryStore()

    async def dispatch(self, request: Request, call_next) -> Response:
        if not self.enabled:
            return await call_next(request)

        path = request.url.path
        max_requests, window = _match_limit(path, self.limits)

        # Per-IP check
        ip = _get_client_ip(request)
        ip_key = f"ip:{ip}:{path}"
        limited, info = self._store.is_rate_limited(ip_key, max_requests, window)

        # Per-user check (stricter limit = 2x IP limit)
        if not limited:
            user_id = _get_user_id(request)
            if user_id:
                user_key = f"{user_id}:{path}"
                limited, info = self._store.is_rate_limited(
                    user_key, max_requests * 2, window
                )

        if limited:
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "Too many requests",
                    "retry_after": info["window"],
                },
                headers={
                    "Retry-After": str(info["window"]),
                    "X-RateLimit-Limit": str(info["limit"]),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(info["reset"]),
                },
            )

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(info["limit"])
        response.headers["X-RateLimit-Remaining"] = str(info["remaining"])
        response.headers["X-RateLimit-Reset"] = str(info["reset"])
        return response
