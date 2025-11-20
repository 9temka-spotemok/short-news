"""
Request lock backend for preventing duplicate requests across multiple workers.

Implements distributed locking using Redis or in-memory storage for testing.
"""

from __future__ import annotations

from typing import Protocol, Optional
from loguru import logger

try:
    import redis
    from redis import Redis
    from redis.exceptions import RedisError
except ImportError:
    redis = None
    Redis = None


class RequestLockBackend(Protocol):
    """Protocol for request lock backends."""

    async def acquire(self, url: str, ttl: int) -> bool:
        """
        Try to acquire a lock for the given URL.
        
        Args:
            url: Normalized URL to lock
            ttl: Time to live in seconds
            
        Returns:
            True if lock was acquired, False if already locked
        """
        ...

    async def release(self, url: str) -> None:
        """
        Release a lock for the given URL.
        
        Args:
            url: Normalized URL to unlock
        """
        ...


class RedisRequestLockBackend:
    """Redis-based request lock backend using SET NX for atomic locking."""

    def __init__(self, redis_url: str, namespace: str = "scraper:lock"):
        """
        Initialize Redis lock backend.
        
        Args:
            redis_url: Redis connection URL
            namespace: Key namespace prefix
        """
        self._redis_url = redis_url
        self._namespace = namespace
        self._client: Optional[Redis] = None

    @property
    def client(self) -> Optional[Redis]:
        """Get or create Redis client."""
        if redis is None:
            logger.warning("Redis not available, request locking disabled")
            return None
        
        if self._client is None:
            try:
                self._client = redis.from_url(self._redis_url, decode_responses=True)
                # Test connection
                self._client.ping()
            except Exception as exc:
                logger.warning(f"Failed to connect to Redis for request locking: {exc}")
                self._client = None
        
        return self._client

    def _build_key(self, url: str) -> str:
        """Build Redis key for URL."""
        return f"{self._namespace}:{url}"

    async def acquire(self, url: str, ttl: int) -> bool:
        """
        Try to acquire a lock using Redis SET NX.
        
        Args:
            url: Normalized URL to lock
            ttl: Time to live in seconds
            
        Returns:
            True if lock was acquired, False if already locked or Redis unavailable
        """
        client = self.client
        if client is None:
            # If Redis is unavailable, allow the request to proceed
            # This is a graceful degradation
            logger.debug(f"Redis unavailable, allowing request for {url}")
            return True
        
        key = self._build_key(url)
        try:
            # SET key value NX EX ttl - atomic operation
            # Returns True if key was set, False if key already exists
            acquired = bool(client.set(key, "1", nx=True, ex=ttl))
            if not acquired:
                logger.debug(f"Lock already held for {url} (key: {key})")
            return acquired
        except RedisError as exc:
            logger.error(f"Failed to acquire lock for {url}: {exc}")
            # On error, allow request to proceed (graceful degradation)
            return True

    async def release(self, url: str) -> None:
        """
        Release a lock by deleting the Redis key.
        
        Args:
            url: Normalized URL to unlock
        """
        client = self.client
        if client is None:
            return
        
        key = self._build_key(url)
        try:
            client.delete(key)
        except RedisError as exc:
            logger.error(f"Failed to release lock for {url}: {exc}")


class InMemoryRequestLockBackend:
    """In-memory request lock backend for testing."""

    def __init__(self):
        """Initialize in-memory lock backend."""
        self._locks: dict[str, float] = {}

    async def acquire(self, url: str, ttl: int) -> bool:
        """
        Try to acquire a lock in memory.
        
        Args:
            url: Normalized URL to lock
            ttl: Time to live in seconds
            
        Returns:
            True if lock was acquired, False if already locked
        """
        import time
        
        now = time.monotonic()
        expires = self._locks.get(url)
        
        if expires and expires > now:
            # Lock is still held
            return False
        
        # Acquire lock
        self._locks[url] = now + ttl
        return True

    async def release(self, url: str) -> None:
        """
        Release a lock by removing it from memory.
        
        Args:
            url: Normalized URL to unlock
        """
        self._locks.pop(url, None)

