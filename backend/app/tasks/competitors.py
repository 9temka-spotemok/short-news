"""
Celery tasks for competitor ingestion and change processing.
"""

from __future__ import annotations

from celery import current_task
from loguru import logger

from app.celery_app import celery_app
from app.domains.competitors.tasks import (
    ingest_pricing_page as ingest_pricing_page_async,
    list_change_events as list_change_events_async,
    recompute_change_event as recompute_change_event_async,
    run_in_loop,
)
from app.models import SourceType


@celery_app.task(bind=True, name="competitors.ingest_pricing_page")
def ingest_pricing_page(
    self,
    company_id: str,
    source_url: str,
    *,
    source_type: str = SourceType.NEWS_SITE.value,
    html: str | None = None,
) -> dict:
    logger.info(
        "Ingesting competitor pricing page | company=%s | source=%s | type=%s",
        company_id,
        source_url,
        source_type,
    )
    try:
        result = run_in_loop(
            lambda: ingest_pricing_page_async(
                company_id,
                source_url=source_url,
                html=html,
                source_type=SourceType(source_type),
            )
        )
        logger.info("Pricing ingestion completed | result=%s", result)
        return {"status": "success", **result}
    except Exception as exc:
        logger.exception("Pricing ingestion failed for company=%s", company_id)
        raise self.retry(exc=exc, countdown=60, max_retries=3)


@celery_app.task(bind=True, name="competitors.recompute_change_event")
def recompute_change_event(self, event_id: str) -> dict:
    logger.info("Recomputing competitor change event %s", event_id)
    try:
        result = run_in_loop(lambda: recompute_change_event_async(event_id))
        logger.info("Recompute completed | result=%s", result)
        return {"status": "success", **result}
    except Exception as exc:
        logger.exception("Failed to recompute change event %s", event_id)
        raise self.retry(exc=exc, countdown=60, max_retries=3)


@celery_app.task(bind=True, name="competitors.list_change_events")
def list_change_events(self, company_id: str, limit: int = 20) -> dict:
    logger.info(
        "Listing competitor change events | company=%s | limit=%s",
        company_id,
        limit,
    )
    try:
        result = run_in_loop(lambda: list_change_events_async(company_id, limit=limit))
        return {"status": "success", **result}
    except Exception as exc:
        logger.exception("Failed to list change events for %s", company_id)
        raise self.retry(exc=exc, countdown=30, max_retries=3)


