"""
Asynchronous rate limiting utilities for scrapers.
"""

from __future__ import annotations

import asyncio
import time
from collections import defaultdict, deque
from typing import Deque, Dict


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


