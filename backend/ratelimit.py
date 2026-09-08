"""Simple in-memory rate limiter for FastAPI."""

import threading
import time
from collections import defaultdict, deque

from fastapi import Request


class RateLimiter:
    """Token-bucket style limiter keyed by client IP.

    `window_seconds` and `max_requests` define the bucketing.
    """

    def __init__(self, max_requests: int = 60, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._requests: dict[str, deque] = defaultdict(deque)
        self._lock = threading.Lock()

    def is_allowed(self, key: str) -> bool:
        now = time.monotonic()
        with self._lock:
            window = self._requests[key]
            while window and now - window[0] > self.window_seconds:
                window.popleft()
            if len(window) >= self.max_requests:
                return False
            window.append(now)
            return True


# One shared limiter instance for the whole app.
DEFAULT_LIMITER = RateLimiter(max_requests=120, window_seconds=60)
# Stricter limiter for expensive/mutating operations (enrichment, backfill).
STRICT_LIMITER = RateLimiter(max_requests=20, window_seconds=60)


def rate_limited(limiter=DEFAULT_LIMITER, key_func=None):
    """Dependency factory. Returns a FastAPI dependency that rejects when
    the client exceeds its quota with 429."""

    def dependency(request: Request):
        client = request.client.host if request.client else "unknown"
        key = key_func(client) if key_func else client
        if not limiter.is_allowed(key):
            from fastapi import HTTPException

            raise HTTPException(status_code=429, detail="Rate limit exceeded. Try again later.")
        return True

    return dependency
