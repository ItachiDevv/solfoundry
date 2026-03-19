"""Simple in-memory sliding-window rate limiter per model."""

from __future__ import annotations

import time
from collections import defaultdict
from threading import Lock


class RateLimiter:
    """Token-bucket style rate limiter keyed by model ID.

    Tracks request timestamps in a 60-second sliding window and rejects
    requests that would exceed `max_rpm` for a given model.
    """

    def __init__(self) -> None:
        self._lock = Lock()
        # model_id -> list of request epoch timestamps
        self._windows: dict[str, list[float]] = defaultdict(list)

    def allow(self, model_id: str, max_rpm: int) -> bool:
        """Return True if the request is allowed, False if rate-limited."""
        now = time.monotonic()
        cutoff = now - 60.0

        with self._lock:
            # Prune old timestamps
            timestamps = self._windows[model_id]
            self._windows[model_id] = [t for t in timestamps if t > cutoff]

            if len(self._windows[model_id]) >= max_rpm:
                return False

            self._windows[model_id].append(now)
            return True

    def reset(self, model_id: str | None = None) -> None:
        """Reset rate limit state. If model_id is None, reset all."""
        with self._lock:
            if model_id:
                self._windows.pop(model_id, None)
            else:
                self._windows.clear()
