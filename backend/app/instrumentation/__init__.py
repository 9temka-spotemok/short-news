"""
Instrumentation utilities for background workers and services.

This package currently exposes Celery-specific helpers for metrics collection,
idempotency guards, and observability hooks.
"""

from .celery_metrics import (  # noqa: F401
    InMemoryDedupBackend,
    TaskExecutionContext,
    configure_dedup_backend,
)

__all__ = [
    "TaskExecutionContext",
    "configure_dedup_backend",
    "InMemoryDedupBackend",
]


