"""Small local rate limiter for v1.

It intentionally lives behind one function so a Redis-backed implementation
can replace it when the API runs on multiple replicas. Local memory is not a
distributed security boundary; Docker production deployments should put a
shared Redis limiter or gateway in front of multiple API replicas.
"""
import threading
import time
from collections import defaultdict, deque

from app.core.config import settings


class LocalRateLimiter:
    def __init__(self):
        self._lock = threading.Lock()
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        window_start = now - 60
        with self._lock:
            q = self._hits[key]
            while q and q[0] < window_start:
                q.popleft()
            if len(q) >= settings.rate_limit_per_minute:
                return False
            q.append(now)
            return True


limiter = LocalRateLimiter()
