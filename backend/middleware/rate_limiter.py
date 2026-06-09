"""
middleware/rate_limiter.py – Per-user rate limiting with slowapi + Redis-free in-memory fallback
"""
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from datetime import datetime, date
from collections import defaultdict
import asyncio

from backend.config import settings


# slowapi limiter (IP-based fallback for unauthenticated routes)
limiter = Limiter(key_func=get_remote_address)


def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> Response:
    return JSONResponse(
        status_code=429,
        content={
            "detail": f"Rate limit exceeded: {exc.detail}. Please slow down.",
            "retry_after": "60 seconds",
        },
    )


# ─── In-memory per-user rate tracker (production: replace with Redis) ─────────

class InMemoryRateLimiter:
    """
    Tracks query counts per user per minute and upload counts per day.
    Thread-safe for asyncio; for multi-worker deployments use Redis.
    """

    def __init__(self):
        self._query_counts: dict[str, list[datetime]] = defaultdict(list)
        self._upload_counts: dict[str, int] = defaultdict(int)
        self._upload_date: dict[str, date] = {}
        self._lock = asyncio.Lock()

    async def check_query_limit(self, user_id: str) -> bool:
        """Returns True if allowed, False if rate-limited."""
        async with self._lock:
            now = datetime.utcnow()
            window = [
                ts for ts in self._query_counts[user_id]
                if (now - ts).total_seconds() < 60
            ]
            self._query_counts[user_id] = window
            if len(window) >= settings.rate_limit_per_minute:
                return False
            self._query_counts[user_id].append(now)
            return True

    async def check_upload_limit(self, user_id: str) -> bool:
        """Returns True if allowed, False if daily upload limit hit."""
        async with self._lock:
            today = date.today()
            if self._upload_date.get(user_id) != today:
                self._upload_counts[user_id] = 0
                self._upload_date[user_id] = today
            if self._upload_counts[user_id] >= settings.rate_limit_upload_per_day:
                return False
            self._upload_counts[user_id] += 1
            return True

    async def get_query_remaining(self, user_id: str) -> int:
        async with self._lock:
            now = datetime.utcnow()
            window = [
                ts for ts in self._query_counts[user_id]
                if (now - ts).total_seconds() < 60
            ]
            return max(0, settings.rate_limit_per_minute - len(window))


rate_limiter = InMemoryRateLimiter()
