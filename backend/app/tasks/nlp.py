"""
Celery tasks for NLP processing.
"""

from __future__ import annotations

from loguru import logger

from app.celery_app import celery_app
from app.services.nlp_service import PIPELINE, run_async


@celery_app.task(bind=True, autoretry_for=(Exception,), retry_backoff=60, retry_kwargs={"max_retries": 3})
def classify_news(self, news_id: str):
    """
    Classify news item (topic, sentiment, priority score).
    """
    logger.info("Starting news classification for ID: %s", news_id)
    result = run_async(PIPELINE.classify_news(news_id))
    logger.info("News classification completed for ID: %s | %s", news_id, result)
    return {"status": "success", **result}


@celery_app.task(bind=True, autoretry_for=(Exception,), retry_backoff=60, retry_kwargs={"max_retries": 3})
def summarize_news(self, news_id: str, force: bool = False):
    """
    Generate or refresh summary for news item.
    """
    logger.info("Starting news summarisation for ID: %s", news_id)
    result = run_async(PIPELINE.summarise_news(news_id, force=force))
    logger.info("News summarisation completed for ID: %s", news_id)
    return {"status": "success", **result}


@celery_app.task(bind=True, autoretry_for=(Exception,), retry_backoff=60, retry_kwargs={"max_retries": 3})
def extract_keywords(self, news_id: str, limit: int = 8):
    """
    Extract keywords from news item content/title.
    """
    logger.info("Starting keyword extraction for ID: %s", news_id)
    result = run_async(PIPELINE.extract_keywords(news_id, limit=limit))
    logger.info("Keyword extraction completed for ID: %s (%d keywords)", news_id, len(result.get("keywords", [])))
    return {"status": "success", **result}
"""
NLP processing tasks
"""

