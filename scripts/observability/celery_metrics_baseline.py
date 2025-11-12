#!/usr/bin/env python
"""
Smoke script to exercise Celery TaskExecutionContext instrumentation and
produce baseline metrics artefacts for B-302.
"""

import os

# Configure defaults before importing application settings.
os.environ.setdefault("SECRET_KEY", "baseline-secret")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./celery_baseline.db")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("CELERY_METRICS_EXPOSE_SERVER", "false")

import json
import math
import random
import statistics
import time
from pathlib import Path

from loguru import logger
from prometheus_client.parser import text_string_to_metric_families

from app.instrumentation.celery_metrics import (
    InMemoryDedupBackend,
    TaskExecutionContext,
    capture_prometheus_snapshot,
    configure_dedup_backend,
    reset_metrics_for_tests,
)


random.seed(2025)


def run_task(task_name: str, queue: str, duration: float, should_fail: bool = False) -> None:
    """
    Execute a synthetic TaskExecutionContext to emit metrics.
    """

    with TaskExecutionContext(task_name, labels={"queue": queue}) as ctx:
        if not ctx.should_run:
            return
        time.sleep(duration)
        if should_fail:
            raise RuntimeError(f"{task_name} simulated failure")
        ctx.finish({"status": "ok"})


def run_deduplicated(task_name: str, queue: str, key: str) -> None:
    """
    Trigger duplicate guard and corresponding metrics.
    """

    with TaskExecutionContext(task_name, labels={"queue": queue}, dedup_key=key, dedup_ttl=60) as primary:
        with TaskExecutionContext(task_name, labels={"queue": queue}, dedup_key=key, dedup_ttl=60) as duplicate:
            if duplicate.should_run:
                logger.warning("Expected duplicate guard for key={} but task was executed", key)
            else:
                logger.info("Duplicate guard triggered for key={}", key)
        if primary.should_run:
            time.sleep(0.05)
            primary.finish("seed")


def aggregate_metrics(snapshot: str) -> dict:
    """
    Convert Prometheus exposition text into a compact JSON summary.
    """

    summary = {
        "success_total": 0.0,
        "failure_total": 0.0,
        "duplicate_total": 0.0,
        "queues": {},
    }
    for family in text_string_to_metric_families(snapshot):
        for sample in family.samples:
            sample_name = sample.name
            if sample_name.endswith("celery_task_total") and "status" in sample.labels:
                queue = sample.labels.get("queue", "default")
                status = sample.labels.get("status")
                summary["queues"].setdefault(queue, {"success": 0.0, "failure": 0.0})
                if status == "success":
                    summary["success_total"] += sample.value
                    summary["queues"][queue]["success"] += sample.value
                elif status == "failure":
                    summary["failure_total"] += sample.value
                    summary["queues"][queue]["failure"] += sample.value
            elif sample_name.endswith("celery_task_duplicates_total"):
                summary["duplicate_total"] += sample.value
    return summary


def main() -> None:
    logger.info("Preparing Celery instrumentation baseline run")

    reset_metrics_for_tests()
    configure_dedup_backend(InMemoryDedupBackend())

    durations = [random.uniform(0.05, 0.12) for _ in range(10)] + [random.uniform(0.2, 0.4) for _ in range(5)]

    for duration in durations:
        run_task("analytics.recompute_single", "analytics", duration)

    try:
        run_task("analytics.recompute_single", "analytics", 0.1, should_fail=True)
    except RuntimeError:
        logger.warning("Simulated failure recorded")

    run_deduplicated("analytics.recompute_single", "analytics", key="baseline")

    snapshot = capture_prometheus_snapshot()
    summary = aggregate_metrics(snapshot)

    metrics_dir = Path("artifacts")
    metrics_dir.mkdir(parents=True, exist_ok=True)

    (metrics_dir / "celery_metrics_baseline.txt").write_text(snapshot)
    (metrics_dir / "celery_metrics_summary.json").write_text(json.dumps(summary, indent=2))

    logger.info(
        "Baseline complete: success={} failure={} duplicates={}",
        summary["success_total"],
        summary["failure_total"],
        summary["duplicate_total"],
    )

    def percentile(data: list[float], percent: float) -> float:
        if not data:
            return 0.0
        ordered = sorted(data)
        k = (len(ordered) - 1) * (percent / 100.0)
        f = math.floor(k)
        c = math.ceil(k)
        if f == c:
            return ordered[int(k)]
        return ordered[f] + (ordered[c] - ordered[f]) * (k - f)

    if durations:
        logger.info(
            "Duration stats: avg={:.3f}s p95={:.3f}s max={:.3f}s",
            statistics.mean(durations),
            percentile(durations, 95),
            max(durations),
        )


if __name__ == "__main__":
    main()

