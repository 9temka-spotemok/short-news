import pytest

from app.core.config import settings
from app.instrumentation.celery_metrics import (
    InMemoryDedupBackend,
    TaskExecutionContext,
    capture_prometheus_snapshot,
    configure_dedup_backend,
    reset_metrics_for_tests,
)


def setup_module() -> None:
    # Disable embedded Prometheus HTTP exporter during test runs.
    settings.CELERY_METRICS_EXPOSE_SERVER = False
    reset_metrics_for_tests()
    configure_dedup_backend(InMemoryDedupBackend())


def test_task_metrics_success_failure_and_deduplication() -> None:
    # Successful execution should update counters and histograms.
    with TaskExecutionContext("test.task", labels={"queue": "analytics"}) as ctx:
        assert ctx.should_run
        ctx.finish({"status": "ok"})

    # A failure increments the failure counter and releases the lock.
    with pytest.raises(RuntimeError):
        with TaskExecutionContext("test.task", labels={"queue": "analytics"}) as ctx:
            assert ctx.should_run
            raise RuntimeError("boom")

    # Deduplication path should prevent second execution and emit duplicate metric.
    with TaskExecutionContext(
        "test.task",
        labels={"queue": "analytics"},
        dedup_key="baseline",
        dedup_ttl=30,
    ) as primary:
        with TaskExecutionContext(
            "test.task",
            labels={"queue": "analytics"},
            dedup_key="baseline",
            dedup_ttl=30,
            duplicate_payload={"status": "duplicate"},
        ) as duplicate:
            assert duplicate.should_run is False
            assert duplicate.result == {"status": "duplicate"}
        primary.finish("primary")

    snapshot = capture_prometheus_snapshot()

    assert 'celery_task_total{task_name="test.task",status="success",queue="analytics"} 1.0' in snapshot
    assert 'celery_task_total{task_name="test.task",status="failure",queue="analytics"} 1.0' in snapshot
    assert 'celery_task_duplicates_total{task_name="test.task",queue="analytics"} 1.0' in snapshot

