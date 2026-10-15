"""In-memory rate limiting (sliding window), for the /auth endpoints.

Each limiter remembers the times of recent attempts per key (an IP, an email...). It
lives in the API process: enough for one process on one VPS. With several replicas each
would count on its own; then the counters should move to a shared store (e.g. Redis).
"""

import math
import threading
import time
from collections import deque


class RateLimited(Exception):
    """Too many attempts. ``retry_after`` is how many seconds to wait."""

    def __init__(self, retry_after: int) -> None:
        super().__init__(f"Too many attempts, retry in {retry_after} s")
        self.retry_after = retry_after


class RateLimiter:
    """At most ``limit`` attempts per ``window`` seconds for each key."""

    # Above this many keys, keys with no recent attempts are dropped
    MAX_KEYS = 10_000

    def __init__(self, limit: int, window: float) -> None:
        self.limit = limit
        self.window = window
        self._hits: dict[str, deque[float]] = {}
        self._lock = threading.Lock()

    def hit(self, key: str) -> None:
        """Count one attempt for ``key``; raise RateLimited if it goes over the limit."""
        now = time.monotonic()
        with self._lock:
            hits = self._hits.setdefault(key, deque())
            while hits and hits[0] <= now - self.window:
                hits.popleft()
            if len(hits) >= self.limit:
                raise RateLimited(max(1, math.ceil(hits[0] + self.window - now)))
            hits.append(now)
            if len(self._hits) > self.MAX_KEYS:
                self._forget_old(now)

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()

    def _forget_old(self, now: float) -> None:
        for key in [k for k, h in self._hits.items() if not h or h[-1] <= now - self.window]:
            del self._hits[key]
