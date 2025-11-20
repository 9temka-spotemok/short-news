"""
Celery observability helpers: deduplication guards and metrics exporters.

This module provides:

* Redis-backed deduplication to prevent double execution of expensive analytics tasks.
* Prometheus counters/gauges/histograms for task throughput, latency and duplicates.
* Optional OpenTelemetry hooks (enabled when the SDK is installed and configured).
"""

from __future__ import annotations

import threading
import time
from contextlib import AbstractContextManager
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from loguru import logger

from app.core.config import settings

try:
    import redis
    from redis import Redis
    from redis.exceptions import RedisError
except Exception:  # pragma: no cover - redis is an hard dependency in prod
    redis = None
    Redis = None

try:
    from prometheus_client import (
        CollectorRegistry,
        Counter,
        Gauge,
        Histogram,
        generate_latest,
        start_http_server,
    )
except Exception:  # pragma: no cover - optional dependency for local/dev
    CollectorRegistry = None
    Counter = None
    Gauge = None
    Histogram = None
    generate_latest = None

try:
    from opentelemetry import metrics as ot_metrics
    from opentelemetry.metrics import Counter as OtCounter
    from opentelemetry.metrics import Histogram as OtHistogram
    from opentelemetry.metrics import Meter
    from opentelemetry.metrics import UpDownCounter as OtUpDownCounter
except Exception:  # pragma: no cover - OpenTelemetry optional
    ot_metrics = None
    Meter = None
    OtCounter = None
    OtHistogram = None
    OtUpDownCounter = None


MetricLabels = Dict[str, str]

DEFAULT_DURATION_BUCKETS = (
    0.1,
    0.5,
    1.0,
    2.0,
    5.0,
    10.0,
    30.0,
    60.0,
    120.0,
    300.0,
)

_PROMETHEUS_SERVER_LOCK = threading.Lock()
_PROMETHEUS_STARTED = False


class DeduplicationBackend:
    """Protocol used by TaskExecutionContext to manage idempotency locks."""

    def acquire(self, key: str, ttl: int) -> bool:
        raise NotImplementedError

    def release(self, key: str) -> None:
        raise NotImplementedError


class RedisDedupBackend(DeduplicationBackend):
    """Redis implementation using SET NX for distributed locking."""

    def __init__(self, redis_url: str, namespace: str = "celery:dedup") -> None:
        self._redis_url = redis_url
        self._namespace = namespace
        self._client: Optional[Redis] = None

    @property
    def client(self) -> Optional[Redis]:
        if redis is None:
            return None
        if self._client is None:
            try:
                self._client = redis.from_url(self._redis_url)
            except Exception as exc:  # pragma: no cover - connection errors
                logger.warning("Deduplication backend failed to connect to Redis: {}", exc)
                self._client = None
        return self._client

    def _build_key(self, key: str) -> str:
        return f"{self._namespace}:{key}"

    def acquire(self, key: str, ttl: int) -> bool:
        client = self.client
        if client is None:
            # Without Redis we cannot deduplicate, allow the task to proceed.
            logger.warning("Redis dedup backend unavailable; skipping idempotency guard for {}", key)
            return True
        namespaced = self._build_key(key)
        try:
            acquired = bool(client.set(namespaced, "1", nx=True, ex=ttl))
            if not acquired:
                logger.info("Deduplication hit for key={}, skipping execution", namespaced)
            return acquired
        except RedisError as exc:  # pragma: no cover - network errors
            logger.error("Failed to acquire dedup key {}: {}", namespaced, exc)
            return True

    def release(self, key: str) -> None:
        client = self.client
        if client is None:
            return
        namespaced = self._build_key(key)
        try:
            client.delete(namespaced)
        except RedisError as exc:  # pragma: no cover - network errors
            logger.error("Failed to release dedup key {}: {}", namespaced, exc)


class InMemoryDedupBackend(DeduplicationBackend):
    """Simple backend for tests."""

    def __init__(self) -> None:
        self._locks: Dict[str, float] = {}

    def acquire(self, key: str, ttl: int) -> bool:
        now = time.monotonic()
        expires = self._locks.get(key)
        if expires and expires > now:
            return False
        self._locks[key] = now + ttl
        return True

    def release(self, key: str) -> None:
        self._locks.pop(key, None)


class OpenTelemetryAdapter:
    """Optional OpenTelemetry metrics exporter."""

    def __init__(self) -> None:
        self._enabled = bool(getattr(settings, "CELERY_OTEL_ENABLED", False) and ot_metrics)
        self._meter: Optional[Meter] = None
        self._task_counter: Optional[OtCounter] = None
        self._task_duration: Optional[OtHistogram] = None
        self._task_in_progress: Optional[OtUpDownCounter] = None
        if self._enabled:
            try:
                self._meter = ot_metrics.get_meter("shot_news.celery")
                self._task_counter = self._meter.create_counter(
                    "celery.task.total", unit="1", description="Celery task executions"
                )
                self._task_duration = self._meter.create_histogram(
                    "celery.task.duration",
                    unit="s",
                    description="Celery task duration in seconds",
                )
                self._task_in_progress = self._meter.create_up_down_counter(
                    "celery.task.in_progress",
                    unit="1",
                    description="Celery tasks currently executing",
                )
            except Exception as exc:  # pragma: no cover - misconfiguration
                logger.warning("Failed to bootstrap OpenTelemetry metrics: {}", exc)
                self._enabled = False

    def _attrs(self, task_name: str, labels: MetricLabels) -> MetricLabels:
        attrs = {"task_name": task_name}
        attrs.update(labels)
        if "queue" not in attrs:
            attrs["queue"] = "default"
        return attrs

    def on_start(self, task_name: str, labels: MetricLabels) -> None:
        if not self._enabled or not self._task_in_progress:
            return
        self._task_in_progress.add(1, self._attrs(task_name, labels))

    def on_complete(self, task_name: str, labels: MetricLabels, duration: float, status: str) -> None:
        if not self._enabled or not self._task_counter or not self._task_duration or not self._task_in_progress:
            return
        attrs = self._attrs(task_name, labels)
        self._task_in_progress.add(-1, attrs)
        self._task_counter.add(1, {**attrs, "status": status})
        self._task_duration.record(duration, attrs)

    def on_duplicate(self, task_name: str, labels: MetricLabels) -> None:
        if not self._enabled or not self._task_counter:
            return
        attrs = self._attrs(task_name, labels)
        self._task_counter.add(1, {**attrs, "status": "duplicate"})


class PrometheusAdapter:
    """Prometheus exporter using prometheus_client."""

    def __init__(self) -> None:
        enabled = bool(getattr(settings, "CELERY_METRICS_ENABLED", True) and Counter and Gauge and Histogram)
        self._enabled = enabled
        self._registry: Optional[CollectorRegistry] = None
        self._task_total: Optional[Counter] = None
        self._task_duplicates: Optional[Counter] = None
        self._task_in_progress: Optional[Gauge] = None
        self._task_duration: Optional[Histogram] = None

        if not enabled:
            return

        namespace = getattr(settings, "CELERY_METRICS_NAMESPACE", "shot_news")
        buckets = getattr(settings, "CELERY_METRICS_DURATION_BUCKETS", DEFAULT_DURATION_BUCKETS)
        self._registry = CollectorRegistry(auto_describe=True)

        self._task_total = Counter(
            "celery_task_total",
            "Total Celery tasks by status",
            ["task_name", "status", "queue"],
            namespace=namespace,
            registry=self._registry,
        )
        self._task_duplicates = Counter(
            "celery_task_duplicates_total",
            "Celery tasks skipped due to deduplication",
            ["task_name", "queue"],
            namespace=namespace,
            registry=self._registry,
        )
        self._task_in_progress = Gauge(
            "celery_task_in_progress",
            "Currently executing Celery tasks",
            ["task_name", "queue"],
            namespace=namespace,
            registry=self._registry,
        )
        self._task_duration = Histogram(
            "celery_task_duration_seconds",
            "Celery task duration in seconds",
            ["task_name", "queue"],
            namespace=namespace,
            registry=self._registry,
            buckets=buckets,
        )
        
        # Scraper-specific metrics
        self._scraper_requests_total = Counter(
            "scraper_requests_total",
            "Total HTTP requests made by scraper",
            ["status", "source_type"],
            namespace=namespace,
            registry=self._registry,
        )
        self._scraper_dead_urls_count = Gauge(
            "scraper_dead_urls_count",
            "Number of disabled/dead URLs per company",
            ["company_id"],
            namespace=namespace,
            registry=self._registry,
        )
        self._scraper_duplicate_requests_total = Counter(
            "scraper_duplicate_requests_total",
            "Duplicate requests prevented by deduplication",
            ["source_type"],
            namespace=namespace,
            registry=self._registry,
        )
        
        # Digest-specific metrics
        self._digests_duration_seconds = Histogram(
            "digests_duration_seconds",
            "Digest generation duration in seconds",
            ["digest_type"],
            namespace=namespace,
            registry=self._registry,
            buckets=buckets,
        )

        if getattr(settings, "CELERY_METRICS_EXPOSE_SERVER", True):
            self._ensure_server()

    def _ensure_server(self) -> None:
        global _PROMETHEUS_STARTED
        if _PROMETHEUS_STARTED:
            return
        with _PROMETHEUS_SERVER_LOCK:
            if _PROMETHEUS_STARTED:
                return
            host = getattr(settings, "CELERY_METRICS_HOST", "0.0.0.0")
            port = getattr(settings, "CELERY_METRICS_PORT", 9464)
            try:
                start_http_server(port=port, addr=host, registry=self._registry)
                logger.info("Started Celery Prometheus exporter on %s:%s", host, port)
                _PROMETHEUS_STARTED = True
            except Exception as exc:  # pragma: no cover - binding issues
                logger.error("Failed to start Prometheus exporter: {}", exc)

    def _queue_label(self, labels: MetricLabels) -> str:
        return labels.get("queue", "default")

    def on_start(self, task_name: str, labels: MetricLabels) -> None:
        if not self._enabled or not self._task_in_progress:
            return
        queue = self._queue_label(labels)
        self._task_in_progress.labels(task_name=task_name, queue=queue).inc()

    def on_complete(self, task_name: str, labels: MetricLabels, duration: float, status: str) -> None:
        if not self._enabled:
            return
        queue = self._queue_label(labels)
        if self._task_in_progress:
            self._task_in_progress.labels(task_name=task_name, queue=queue).dec()
        if self._task_total:
            self._task_total.labels(task_name=task_name, status=status, queue=queue).inc()
        if status == "success" and self._task_duration:
            self._task_duration.labels(task_name=task_name, queue=queue).observe(duration)

    def on_duplicate(self, task_name: str, labels: MetricLabels) -> None:
        if not self._enabled or not self._task_duplicates:
            return
        queue = self._queue_label(labels)
        self._task_duplicates.labels(task_name=task_name, queue=queue).inc()
    
    def record_scraper_request(self, status: str, source_type: str = "unknown") -> None:
        """Record a scraper HTTP request."""
        if not self._enabled or not self._scraper_requests_total:
            return
        self._scraper_requests_total.labels(status=status, source_type=source_type).inc()
    
    def update_dead_urls_count(self, company_id: str, count: int) -> None:
        """Update the count of dead URLs for a company."""
        if not self._enabled or not self._scraper_dead_urls_count:
            return
        self._scraper_dead_urls_count.labels(company_id=company_id).set(count)
    
    def record_duplicate_request(self, source_type: str = "unknown") -> None:
        """Record a duplicate request that was prevented."""
        if not self._enabled or not self._scraper_duplicate_requests_total:
            return
        self._scraper_duplicate_requests_total.labels(source_type=source_type).inc()
    
    def record_digest_duration(self, digest_type: str, duration: float) -> None:
        """Record digest generation duration."""
        if not self._enabled or not self._digests_duration_seconds:
            return
        self._digests_duration_seconds.labels(digest_type=digest_type).observe(duration)


class CeleryMetrics:
    """Facade combining Prometheus and OpenTelemetry exporters."""

    def __init__(self) -> None:
        self._prometheus = PrometheusAdapter()
        self._otel = OpenTelemetryAdapter()

    def on_start(self, task_name: str, labels: MetricLabels) -> None:
        self._prometheus.on_start(task_name, labels)
        self._otel.on_start(task_name, labels)

    def on_complete(self, task_name: str, labels: MetricLabels, duration: float, status: str) -> None:
        self._prometheus.on_complete(task_name, labels, duration, status)
        self._otel.on_complete(task_name, labels, duration, status)

    def on_duplicate(self, task_name: str, labels: MetricLabels) -> None:
        self._prometheus.on_duplicate(task_name, labels)
        self._otel.on_duplicate(task_name, labels)
    
    def record_scraper_request(self, status: str, source_type: str = "unknown") -> None:
        """Record a scraper HTTP request."""
        self._prometheus.record_scraper_request(status, source_type)
    
    def update_dead_urls_count(self, company_id: str, count: int) -> None:
        """Update the count of dead URLs for a company."""
        self._prometheus.update_dead_urls_count(company_id, count)
    
    def record_duplicate_request(self, source_type: str = "unknown") -> None:
        """Record a duplicate request that was prevented."""
        self._prometheus.record_duplicate_request(source_type)
    
    def record_digest_duration(self, digest_type: str, duration: float) -> None:
        """Record digest generation duration."""
        self._prometheus.record_digest_duration(digest_type, duration)


_metrics = CeleryMetrics()
_dedup_backend: DeduplicationBackend = RedisDedupBackend(settings.REDIS_URL)


def configure_dedup_backend(backend: DeduplicationBackend) -> None:
    """
    Override the deduplication backend (useful for tests).
    """

    global _dedup_backend
    _dedup_backend = backend


@dataclass
class TaskExecutionContext(AbstractContextManager["TaskExecutionContext"]):
    """
    Context manager that wraps a Celery task body.

    Usage:

        with TaskExecutionContext("task_name", dedup_key=key) as ctx:
            if not ctx.should_run:
                return ctx.result
            value = expensive_operation()
            return ctx.finish(value)
    """

    task_name: str
    labels: MetricLabels = field(default_factory=dict)
    dedup_key: Optional[str] = None
    dedup_ttl: int = field(default_factory=lambda: getattr(settings, "CELERY_DEDUP_TTL_SECONDS", 900))
    duplicate_payload: Optional[Dict[str, Any]] = None

    should_run: bool = field(init=False, default=True)
    result: Any = field(init=False, default=None)
    _started_at: Optional[float] = field(init=False, default=None)

    def __enter__(self) -> "TaskExecutionContext":
        if self.dedup_key:
            acquired = _dedup_backend.acquire(self.dedup_key, self.dedup_ttl)
            if not acquired:
                self.should_run = False
                self.result = self.duplicate_payload or {
                    "status": "duplicate",
                    "reason": "deduplication_guard",
                    "dedup_key": self.dedup_key,
                }
                _metrics.on_duplicate(self.task_name, self.labels)
                return self
        self._started_at = time.perf_counter()
        _metrics.on_start(self.task_name, self.labels)
        return self

    def finish(self, result: Any) -> Any:
        """
        Attach the result for downstream access and return it to the caller.
        """

        self.result = result
        return result

    def __exit__(self, exc_type, exc, exc_tb) -> bool:
        if self.dedup_key and self.should_run:
            try:
                _dedup_backend.release(self.dedup_key)
            except Exception as release_exc:  # pragma: no cover - defensive
                logger.warning("Failed to release dedup key %s: %s", self.dedup_key, release_exc)

        if not self.should_run:
            return False

        duration = 0.0
        if self._started_at is not None:
            duration = max(time.perf_counter() - self._started_at, 0.0)
        status = "success" if exc_type is None else "failure"
        _metrics.on_complete(self.task_name, self.labels, duration, status)

        return False  # Do not suppress exceptions


def capture_prometheus_snapshot() -> str:
    """
    Return current Prometheus metrics in text exposition format.

    Useful for tests and tooling that validate observability without scraping
    the embedded HTTP server.
    """

    adapter = getattr(_metrics, "_prometheus", None)
    if not adapter or not getattr(adapter, "_enabled", False):
        return ""
    registry = getattr(adapter, "_registry", None)
    if not registry or generate_latest is None:
        return ""
    return generate_latest(registry).decode("utf-8")


def reset_metrics_for_tests() -> None:
    """
    Reset global instrumentation state. Intended strictly for test suites.
    """

    global _metrics, _PROMETHEUS_STARTED
    _PROMETHEUS_STARTED = False
    _metrics = CeleryMetrics()
    configure_dedup_backend(InMemoryDedupBackend())

