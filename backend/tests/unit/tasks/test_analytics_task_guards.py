from __future__ import annotations

import pytest

from app.instrumentation import InMemoryDedupBackend, TaskExecutionContext, configure_dedup_backend


@pytest.fixture()
def dedup_backend() -> InMemoryDedupBackend:
    backend = InMemoryDedupBackend()
    configure_dedup_backend(backend)
    yield backend
    configure_dedup_backend(InMemoryDedupBackend())


def test_task_context_skips_when_duplicate(dedup_backend: InMemoryDedupBackend) -> None:
    assert dedup_backend.acquire("duplicate-key", ttl=30) is True

    ctx = TaskExecutionContext("sample_task", dedup_key="duplicate-key", labels={"queue": "test"})
    with ctx:
        assert ctx.should_run is False
        assert ctx.result["status"] == "duplicate"


def test_task_context_releases_lock(dedup_backend: InMemoryDedupBackend) -> None:
    with TaskExecutionContext("sample_task", dedup_key="release-key", labels={"queue": "test"}):
        pass

    # Lock should be released after context exit.
    assert dedup_backend.acquire("release-key", ttl=30) is True


def test_task_context_finish_returns_result(dedup_backend: InMemoryDedupBackend) -> None:
    with TaskExecutionContext("sample_task", labels={"queue": "test"}) as ctx:
        assert ctx.should_run is True
        payload = {"status": "success"}
        assert ctx.finish(payload) == payload
        assert ctx.result == payload


