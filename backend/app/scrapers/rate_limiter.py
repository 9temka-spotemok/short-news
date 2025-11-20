"""
Asynchronous rate limiting utilities for scrapers.
"""

from __future__ import annotations

import asyncio
import time
from collections import defaultdict, deque
from typing import Deque, Dict, Optional

from app.scrapers.request_lock import RequestLockBackend, RedisRequestLockBackend, InMemoryRequestLockBackend
from app.core.config import settings
from loguru import logger


class SourceFetchLock:
    """
    Lock for preventing duplicate requests to the same URL across multiple workers.
    
    Uses distributed locking (Redis) or in-memory locking (for tests) to ensure
    only one worker processes a URL at a time.
    """

    def __init__(self, backend: Optional[RequestLockBackend] = None):
        """
        Initialize source fetch lock.
        
        Args:
            backend: Lock backend implementation. If None, uses RedisRequestLockBackend
                     or falls back to InMemoryRequestLockBackend if Redis unavailable.
        """
        if backend is None:
            try:
                self._backend = RedisRequestLockBackend(settings.REDIS_URL)
            except Exception:
                logger.warning("Redis unavailable for request locking, using in-memory backend")
                self._backend = InMemoryRequestLockBackend()
        else:
            self._backend = backend

    async def acquire(self, url: str, timeout: int) -> bool:
        """
        Try to acquire a lock for fetching a URL.
        
        Args:
            url: Normalized URL to lock
            timeout: Request timeout in seconds (used as TTL for lock)
            
        Returns:
            True if lock was acquired, False if already locked
        """
        # TTL = timeout + buffer (30 seconds buffer for safety)
        ttl = timeout + 30
        return await self._backend.acquire(url, ttl)

    async def release(self, url: str) -> None:
        """
        Release a lock for a URL.
        
        Args:
            url: Normalized URL to unlock
        """
        await self._backend.release(url)


class RateLimiter:
    """
    Simple async rate limiter that limits the number of events per key within a time window.
    """

    def __init__(self) -> None:
        self._locks: Dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)
        self._history: Dict[str, Deque[float]] = defaultdict(deque)

    async def throttle(self, key: str, max_requests: int, period: float) -> None:
        """
        Ensure that no more than `max_requests` are executed for `key` within `period` seconds.
        """
        if max_requests <= 0 or period <= 0:
            # No throttling requested for this key.
            return

        lock = self._locks[key]
        async with lock:
            now = time.monotonic()
            window = self._history[key]

            # Drop timestamps older than the time window.
            while window and now - window[0] >= period:
                window.popleft()

            if len(window) >= max_requests:
                sleep_for = period - (now - window[0])
                if sleep_for > 0:
                    await asyncio.sleep(sleep_for)
                # Clean up after waiting.
                while window and time.monotonic() - window[0] >= period:
                    window.popleft()

            window.append(time.monotonic())


