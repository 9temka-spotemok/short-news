"""
Celery tasks for NLP processing.
"""

from __future__ import annotations

from loguru import logger

from app.celery_app import celery_app
from app.domains.news.tasks import (
    classify_news as classify_news_async,
    summarise_news as summarise_news_async,
    extract_keywords as extract_keywords_async,
    run_in_loop,
)


@celery_app.task(bind=True, autoretry_for=(Exception,), retry_backoff=60, retry_kwargs={"max_retries": 3})
def classify_news(self, news_id: str):
    """
    Classify news item (topic, sentiment, priority score).
    """
    logger.info("Starting news classification for ID: %s", news_id)
    result = run_in_loop(lambda: classify_news_async(news_id))
    logger.info("News classification completed for ID: %s | %s", news_id, result)
    return {"status": "success", **result}


@celery_app.task(bind=True, autoretry_for=(Exception,), retry_backoff=60, retry_kwargs={"max_retries": 3})
def summarize_news(self, news_id: str, force: bool = False):
    """
    Generate or refresh summary for news item.
    """
    logger.info("Starting news summarisation for ID: %s", news_id)
    result = run_in_loop(lambda: summarise_news_async(news_id, force=force))
    logger.info("News summarisation completed for ID: %s", news_id)
    return {"status": "success", **result}


@celery_app.task(bind=True, autoretry_for=(Exception,), retry_backoff=60, retry_kwargs={"max_retries": 3})
def extract_keywords(self, news_id: str, limit: int = 8):
    """
    Extract keywords from news item content/title.
    """
    logger.info("Starting keyword extraction for ID: %s", news_id)
    result = run_in_loop(lambda: extract_keywords_async(news_id, limit=limit))
    logger.info("Keyword extraction completed for ID: %s (%d keywords)", news_id, len(result.get("keywords", [])))
    return {"status": "success", **result}
"""
NLP processing tasks
"""

