"""
Universal scraper for company blogs and news pages with configurable sources,
retry policies, rate limiting, and SPA fallbacks.
"""

from __future__ import annotations

import asyncio
import hashlib
import re
import time
from collections import OrderedDict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup
from pydantic import ValidationError
from loguru import logger

from app.core.config import settings
from app.models.news import NewsCategory
from app.scrapers.config_loader import (
    ScraperConfigRegistry,
    SourceConfig,
    SourceRetryConfig,
)
from app.scrapers.headless import fetch_page_with_headless
from app.scrapers.rate_limiter import RateLimiter, SourceFetchLock
from app.utils.datetime_utils import utc_now_naive


DEFAULT_ARTICLE_SELECTORS: Tuple[str, ...] = (
    "article a",
    "article h2 a",
    "article h3 a",
    "div.post a",
    "div.blog-post a",
    "div.news-item a",
    "div.card a",
    "div.entry a",
    "li.post a",
    "li.article a",
    "h2 a",
    "h3 a",
    "h4 a",
    'a[href*="/blog/"]',
    'a[href*="/news/"]',
    'a[href*="/post/"]',
    'a[href*="/article/"]',
    'a[href*="/posts/"]',
    ".article-link",
    ".post-link",
    ".news-link",
    ".entry-title a",
    ".post-title a",
    '[class*="post"] a',
    '[class*="article"] a',
    '[class*="blog"] a',
    '[class*="news"] a',
)

DISCOVERY_KEYWORDS: Tuple[str, ...] = (
    "blog",
    "news",
    "press",
    "stories",
    "updates",
    "insights",
    "articles",
    "resource",
)


class NeedsHeadless(RuntimeError):
    """Raised when a request is blocked and should be retried via headless browser."""


class UniversalBlogScraper:
    """Universal scraper that can scrape blogs from any company."""

    def __init__(
        self,
        config_registry: Optional[ScraperConfigRegistry] = None,
        rate_limiter: Optional[RateLimiter] = None,
    ):
        common_kwargs = dict(
            headers={"User-Agent": settings.SCRAPER_USER_AGENT},
            timeout=settings.SCRAPER_TIMEOUT,
            follow_redirects=True,
        )
        self.session = httpx.AsyncClient(**common_kwargs)
        self.proxy_session: Optional[httpx.AsyncClient] = None
        if settings.SCRAPER_PROXY_URL:
            self.proxy_session = httpx.AsyncClient(
                proxies=settings.SCRAPER_PROXY_URL,
                **common_kwargs,
            )
        self.config_registry = config_registry or ScraperConfigRegistry()
        self.rate_limiter = rate_limiter or RateLimiter()
        # In-memory cache for request deduplication within a single scraper instance
        # Key: (normalized_url, company_name), Value: (html, final_url, fetched_at)
        self._request_cache: Dict[Tuple[str, str], Tuple[str, str, float]] = {}
        # Distributed lock for preventing duplicate requests across workers
        self._fetch_lock = SourceFetchLock()

    @staticmethod
    def detect_blog_urls(website: str) -> List[str]:
        """
        Detect possible blog/news URLs from company website.
        """
        parsed = urlparse(website)
        if not parsed.scheme or not parsed.netloc:
            return []
        base_domain = f"{parsed.scheme}://{parsed.netloc}".rstrip("/")
        patterns = [
            f"{base_domain}/blog",
            f"{base_domain}/blogs",
            f"{base_domain}/blog/",
            f"{base_domain}/blogs/",
            f"{base_domain}/news",
            f"{base_domain}/news/",
            f"{base_domain}/insights",
            f"{base_domain}/updates",
            f"{base_domain}/press",
            f"{base_domain}/newsroom",
            f"{base_domain}/press-releases",
            f"{base_domain}/company/blog",
            f"{base_domain}/company/news",
            f"{base_domain}/resources/blog",
            f"{base_domain}/hub/blog",
        ]
        return patterns

    def _detect_blog_url(self, website: str) -> List[str]:
        """
        Backwards-compatible wrapper around detect_blog_urls.
        """
        return self.detect_blog_urls(website)

    async def scrape_company_blog(
        self,
        company_name: str,
        website: str,
        news_page_url: Optional[str] = None,
        max_articles: int = 10,
        source_overrides: Optional[List[Dict[str, Any]]] = None,
        skip_urls: Optional[Set[str]] = None,
        company_id: Optional[str] = None,
        health_service: Optional[Any] = None,
    ) -> List[Dict[str, Any]]:
        """
        Scrape blog/news from a company website.
        """
        logger.info(
            f"Scraping blog for {company_name} (news_page_url={news_page_url}, overrides={bool(source_overrides)})"
        )

        # Сохраняем company_id и health_service для использования в _fetch_with_retry
        self._current_company_id = company_id
        self._current_health_service = health_service

        news_items: List[Dict[str, Any]] = []
        seen_urls: Set[str] = set()

        source_configs = self.config_registry.get_sources(
            company_name=company_name,
            website=website,
            manual_url=news_page_url,
            overrides=source_overrides,
        )
        
        # Фильтруем source_configs по skip_urls
        if skip_urls:
            filtered_configs = []
            for source_config in source_configs:
                # Проверяем, есть ли URL в skip_urls
                should_skip = False
                for url in source_config.urls:
                    normalized = self._normalize_url(str(url))
                    if normalized in skip_urls:
                        should_skip = True
                        logger.debug(
                            f"Skipping source {source_config.id} for {company_name} "
                            f"(URL {url} is in skip_urls)"
                        )
                        break
                if not should_skip:
                    filtered_configs.append(source_config)
            source_configs = filtered_configs

        discoveries: List[SourceConfig] = []
        has_custom_sources = any(not cfg.id.startswith("default_") for cfg in source_configs)
        # Оптимизация: если указан news_page_url или есть overrides, пропускаем discovery для скорости
        skip_discovery = news_page_url is not None or source_overrides is not None
        if not has_custom_sources and website and not skip_discovery:
            discovered_urls = await self._discover_candidate_sources(website)
            if discovered_urls:
                existing_urls = {
                    str(url).rstrip("/")
                    for cfg in source_configs
                    for url in cfg.urls
                }
                for idx, candidate in enumerate(discovered_urls):
                    normalized = candidate.rstrip("/")
                    if normalized in existing_urls:
                        continue
                    try:
                        discoveries.append(
                            SourceConfig(
                                id=f"discovered_{idx}",
                                urls=[candidate],
                                source_type="blog",
                                retry=SourceRetryConfig(attempts=0),
                                max_articles=max_articles,
                            )
                        )
                    except ValidationError as exc:
                        logger.debug(f"Skipping discovered url %s: %s", candidate, exc)
                        continue
                    existing_urls.add(normalized)
                if discoveries:
                    source_configs = discoveries + source_configs

        if not source_configs:
            logger.warning(f"No source configurations found for {company_name}")
        else:
            for source_config in source_configs:
                per_source_limit = source_config.max_articles or max_articles
                logger.info(
                    f"Scraping source {source_config.id} for {company_name} with {per_source_limit} max articles"
                )
                try:
                    source_items, source_stats = await self._scrape_source(
                        company_name=company_name,
                        source_config=source_config,
                        max_articles=per_source_limit,
                        seen_urls=seen_urls,
                    )
                    news_items.extend(source_items)
                except Exception as exc:
                    logger.warning(
                        f"Failed to scrape source {source_config.id} for {company_name}: {exc}"
                    )

        if news_items:
            logger.info(f"Successfully scraped {len(news_items)} items from {company_name}")
            return news_items

        logger.info(
            f"Falling back to heuristic scraping for {company_name} (news_page_url={news_page_url})"
        )
        return await self._scrape_with_heuristics(
            company_name=company_name,
            website=website,
            news_page_url=news_page_url,
            max_articles=max_articles,
        )

    async def _scrape_with_heuristics(
        self,
        company_name: str,
        website: str,
        news_page_url: Optional[str],
        max_articles: int,
    ) -> List[Dict[str, Any]]:
        """Fallback scraper that relies on heuristic URL detection."""
        news_items: List[Dict[str, Any]] = []

        try:
            if news_page_url:
                blog_urls = [news_page_url]
                logger.info(f"Using manual news page URL for {company_name}: {news_page_url}")
            else:
                blog_urls = self._detect_blog_url(website)
                logger.info(
                    f"Detected {len(blog_urls)} candidate blog URLs for {company_name}"
                )

            for blog_url in blog_urls:
                try:
                    logger.info(f"Trying URL {blog_url} for {company_name}")
                    response = await self.session.get(blog_url)

                    final_url = str(response.url)
                    if final_url != blog_url:
                        logger.debug(f"Redirected from {blog_url} to {final_url}")
                        if (
                            "/blog" not in final_url.lower()
                            and "/news" not in final_url.lower()
                            and "/press" not in final_url.lower()
                        ):
                            if any(segment in blog_url.lower() for segment in ("blog", "news", "press")):
                                logger.debug(
                                    f"Skipping {final_url} - redirect appears to leave blog/news section"
                                )
                                continue

                    if response.status_code == 404:
                        logger.debug(f"Received 404 for {blog_url}")
                        continue

                    if response.status_code != 200:
                        logger.debug(
                            f"Non-200 status {response.status_code} for {company_name} while scraping {blog_url}"
                        )
                        continue

                    soup = BeautifulSoup(response.text, "html.parser")
                    articles = self._extract_articles(soup, final_url, DEFAULT_ARTICLE_SELECTORS)
                    if not articles:
                        page_title = soup.title.string if soup.title else "N/A"
                        logger.debug(
                            f"Loaded {final_url} but no articles found (title={page_title})"
                        )
                        continue

                    logger.info(
                        f"Found {min(len(articles), max_articles)} articles for {company_name} at {final_url}"
                    )

                    for idx, article in enumerate(articles[:max_articles]):
                        source_type = "blog"
                        url_lower = article["url"].lower()
                        if "/news/" in url_lower:
                            source_type = "news_site"
                        elif "/press/" in url_lower or "press-release" in url_lower:
                            source_type = "press_release"

                        title_lower = article["title"].lower()
                        inferred_category: Optional[str] = None
                        try:
                            if any(k in title_lower for k in ["price", "pricing", "plan", "billing"]):
                                inferred_category = NewsCategory.PRICING_CHANGE.value
                            elif any(
                                k in title_lower
                                for k in ["funding", "seed", "series a", "series b", "investment"]
                            ):
                                inferred_category = NewsCategory.FUNDING_NEWS.value
                            elif any(k in title_lower for k in ["release", "launched", "launch", "introducing"]):
                                inferred_category = NewsCategory.PRODUCT_UPDATE.value
                            elif any(k in title_lower for k in ["security", "vulnerability", "patch", "cve"]):
                                inferred_category = NewsCategory.SECURITY_UPDATE.value
                            elif any(k in title_lower for k in ["api", "sdk"]):
                                inferred_category = NewsCategory.API_UPDATE.value
                            elif any(k in title_lower for k in ["integration", "integrates with"]):
                                inferred_category = NewsCategory.INTEGRATION.value
                            elif any(k in title_lower for k in ["deprecated", "deprecation", "sunset"]):
                                inferred_category = NewsCategory.FEATURE_DEPRECATION.value
                            elif any(k in title_lower for k in ["acquires", "acquisition", "merger"]):
                                inferred_category = NewsCategory.ACQUISITION.value
                            elif any(k in title_lower for k in ["partner", "partnership"]):
                                inferred_category = NewsCategory.PARTNERSHIP.value
                            elif any(k in title_lower for k in ["model", "gpt", "llama", "release"]):
                                inferred_category = NewsCategory.MODEL_RELEASE.value
                            elif any(k in title_lower for k in ["performance", "faster", "improvement"]):
                                inferred_category = NewsCategory.PERFORMANCE_IMPROVEMENT.value
                            elif any(k in title_lower for k in ["paper", "arxiv", "research"]):
                                inferred_category = NewsCategory.RESEARCH_PAPER.value
                            elif any(k in title_lower for k in ["webinar", "event", "conference", "meetup"]):
                                inferred_category = NewsCategory.COMMUNITY_EVENT.value
                            elif any(k in title_lower for k in ["strategy", "vision", "roadmap"]):
                                inferred_category = NewsCategory.STRATEGIC_ANNOUNCEMENT.value
                            elif any(
                                k in title_lower for k in ["technical", "architecture", "infra", "infrastructure"]
                            ):
                                inferred_category = NewsCategory.TECHNICAL_UPDATE.value
                        except Exception:
                            inferred_category = None

                        news_items.append(
                            {
                                "title": article["title"],
                                "content": f"Article from {company_name}: {article['title']}",
                                "summary": article["title"][:200],
                                "source_url": article["url"],
                                "source_type": source_type,
                                "company_name": company_name,
                                "category": inferred_category or NewsCategory.PRODUCT_UPDATE.value,
                                "topic": None,
                                "sentiment": None,
                                "priority_score": 0.5,
                                "raw_snapshot_url": None,
                                "published_at": utc_now_naive() - timedelta(days=idx),
                            }
                        )

                    if news_items:
                        break

                except httpx.HTTPError as exc:
                    logger.debug(f"HTTP error while scraping {blog_url} for {company_name}: {exc}")
                    continue
                except Exception as exc:
                    logger.debug(f"Unexpected error while scraping {blog_url} for {company_name}: {exc}")
                    continue

            if news_items:
                logger.info(f"Heuristic scraping found {len(news_items)} items for {company_name}")
            else:
                logger.warning(f"Heuristic scraping found no items for {company_name}")

            return news_items

        except Exception as exc:
            logger.exception(f"Fallback scraping failed for {company_name}: {exc}")
            return []

    async def scrape_multiple_companies(
        self,
        companies: List[Dict[str, str]],
        max_articles_per_company: int = 5,
        source_override_map: Optional[Dict[str, List[Dict[str, Any]]]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Scrape blogs from multiple companies.
        """
        logger.info(f"Scraping blogs from {len(companies)} companies...")

        all_news: List[Dict[str, Any]] = []

        for company in companies:
            company_name = company.get("name")
            website = company.get("website")

            if not company_name or not website:
                continue

            overrides = None
            if source_override_map:
                overrides = source_override_map.get(company_name) or source_override_map.get(
                    company_name.lower()
                )

            news = await self.scrape_company_blog(
                company_name=company_name,
                website=website,
                max_articles=max_articles_per_company,
                source_overrides=overrides,
            )
            all_news.extend(news)

        logger.info(
            f"Total scraped: {len(all_news)} news items from {len(companies)} companies"
        )
        return all_news

    async def close(self) -> None:
        """Close HTTP sessions and clear request cache."""
        await self.session.aclose()
        if self.proxy_session:
            await self.proxy_session.aclose()
        # Clear request cache when closing scraper
        self._request_cache.clear()

    async def _scrape_source(
        self,
        company_name: str,
        source_config: SourceConfig,
        max_articles: int,
        seen_urls: Set[str],
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Scrape a source and return items along with statistics.
        
        Returns:
            Tuple of (items, stats) where stats contains:
            - source_url: str
            - status: int (HTTP status code)
            - items_count: int
            - success: bool
        """
        items: List[Dict[str, Any]] = []
        source_stats: Dict[str, Any] = {
            "source_url": None,
            "status": None,
            "items_count": 0,
            "success": False,
        }

        for raw_url in source_config.urls:
            url = str(raw_url)
            source_stats["source_url"] = url
            
            # Получаем company_id и health_service из параметров scraper
            company_id = getattr(self, '_current_company_id', None)
            health_service = getattr(self, '_current_health_service', None)
            source_type_str = source_config.source_type
            
            html, final_url, status_code = await self._fetch_with_retry(
                url, 
                source_config, 
                company_name=company_name,
                company_id=company_id,
                health_service=health_service,
                source_type=source_type_str,
            )
            source_stats["status"] = status_code
            
            if not html:
                # Если HTML не получен, это может быть 404 или другая ошибка
                source_stats["success"] = False
                source_stats["items_count"] = 0
                continue

            # Если HTML получен, считаем успешным
            source_stats["success"] = True

            snapshot_path = self._persist_snapshot(company_name, source_config.id, final_url, html)
            soup = BeautifulSoup(html, "html.parser")
            selectors = source_config.selectors or DEFAULT_ARTICLE_SELECTORS
            articles = self._extract_articles(soup, final_url, selectors)

            if not articles:
                logger.debug(
                    f"No articles found for {company_name} at {final_url} (source {source_config.id})"
                )
                source_stats["items_count"] = 0
                # Записываем результат в health_service (пустой ответ)
                if company_id and health_service:
                    await self._record_health_result(
                        company_id, url, False, status_code, 0,
                        health_service, source_type_str
                    )
                # Не прерываем цикл, продолжаем со следующим URL
                continue

            logger.info(
                f"Found {len(articles)} articles for {company_name} at {final_url} (source {source_config.id})"
            )
            source_stats["items_count"] = len(articles)

            for idx, article in enumerate(articles):
                if article["url"] in seen_urls:
                    continue
                seen_urls.add(article["url"])

                inferred_category = self._infer_category(article["title"])
                published_at = utc_now_naive() - timedelta(days=idx)
                items.append(
                    {
                        "title": article["title"],
                        "content": f"Article from {company_name}: {article['title']}",
                        "summary": article["title"][:200],
                        "source_url": article["url"],
                        "source_type": source_config.source_type,
                        "company_name": company_name,
                        "category": inferred_category or NewsCategory.PRODUCT_UPDATE.value,
                        "topic": None,
                        "sentiment": None,
                        "priority_score": 0.5,
                        "raw_snapshot_url": snapshot_path,
                        "published_at": published_at,
                    }
                )

                if len(items) >= max_articles:
                    break

            if len(items) >= max_articles:
                break
            
            # Записываем результат в health_service после обработки URL
            if company_id and health_service:
                await self._record_health_result(
                    company_id, url, source_stats["success"], 
                    source_stats["status"], source_stats["items_count"],
                    health_service, source_type_str
                )

        return items, source_stats
    
    async def _record_health_result(
        self,
        company_id: str,
        source_url: str,
        success: bool,
        status: int,
        items_count: int,
        health_service: Any,
        source_type: Optional[str] = None,
    ) -> None:
        """Helper method to record health result."""
        try:
            from uuid import UUID
            from app.models.news import SourceType as ST
            
            company_uuid = UUID(company_id) if isinstance(company_id, str) else company_id
            st = ST.BLOG  # По умолчанию BLOG
            
            # Определяем source_type
            if source_type == "news_site":
                st = ST.NEWS_SITE
            elif source_type == "press_release":
                st = ST.PRESS_RELEASE
            
            await health_service.record_result(
                company_id=company_uuid,
                source_url=source_url,
                success=success,
                status=status,
                items_count=items_count,
                source_type=st,
            )
            logger.debug(
                f"Recorded source health result for {source_url} "
                f"(status={status}, items={items_count}, success={success})"
            )
        except Exception as exc:
            logger.warning(
                f"Failed to record source health result for {source_url}: {exc}",
                exc_info=True
            )

    def _normalize_url(self, url: str) -> str:
        """
        Нормализует URL для сравнения:
        - Убирает trailing slash
        - Приводит домен к lowercase
        - Убирает query params для сравнения
        - Возвращает канонический URL
        """
        parsed = urlparse(url)
        # Приводим домен к lowercase
        netloc = parsed.netloc.lower() if parsed.netloc else ""
        # Убираем trailing slash из path
        path = parsed.path.rstrip("/") if parsed.path else ""
        # Собираем URL без query params и fragment
        normalized = f"{parsed.scheme}://{netloc}{path}"
        return normalized

    async def _fetch_with_retry(
        self,
        url: str,
        source_config: SourceConfig,
        company_name: Optional[str] = None,
        company_id: Optional[str] = None,
        health_service: Optional[Any] = None,
        source_type: Optional[str] = None,
    ) -> Tuple[Optional[str], str, int]:
        """
        Fetch URL with retry logic and request deduplication.
        
        Args:
            url: URL to fetch
            source_config: Source configuration
            company_name: Company name for cache key (optional, for deduplication)
            company_id: Company ID for health service (optional)
            health_service: SourceHealthService instance (optional)
            source_type: Source type for health service (optional)
            
        Returns:
            Tuple of (html, final_url, status_code)
        """
        # Нормализуем URL для дедупликации
        normalized_url = self._normalize_url(url)
        
        # Проверяем кэш перед запросом (если указано имя компании)
        if company_name:
            cache_key = (normalized_url, company_name)
            if cache_key in self._request_cache:
                cached_html, cached_final_url, cached_time = self._request_cache[cache_key]
                logger.debug(
                    f"Using cached response for {url} (normalized: {normalized_url}, "
                    f"cached at {cached_time})"
                )
                # Записываем метрику дубликата
                try:
                    from app.instrumentation.celery_metrics import _metrics
                    _metrics.record_duplicate_request(source_type or "unknown")
                except Exception:
                    pass
                # Возвращаем статус 200 для кэшированного ответа
                return cached_html, cached_final_url, 200
        
        attempts = max(1, source_config.retry.attempts + 1)
        timeout = source_config.timeout or settings.SCRAPER_TIMEOUT
        
        # Попытка получить межпроцессную блокировку
        lock_acquired = await self._fetch_lock.acquire(normalized_url, timeout)
        if not lock_acquired:
            logger.debug(
                f"Lock not acquired for {url} (normalized: {normalized_url}), "
                f"another worker is already fetching it"
            )
            return None, url, 0  # Статус 0 означает, что запрос не был выполнен
        
        try:
            proxy = settings.SCRAPER_PROXY_URL if source_config.use_proxy and settings.SCRAPER_PROXY_URL else None
            parsed = urlparse(url)
            host_key = parsed.netloc or url

            for attempt in range(attempts):
                try:
                    await self.rate_limiter.throttle(
                        key=host_key,
                        max_requests=source_config.rate_limit.requests,
                        period=source_config.rate_limit.interval,
                    )
                    client = self.proxy_session if proxy else self.session
                    response = await client.get(url, timeout=timeout)
                    if self._requires_headless(response):
                        raise NeedsHeadless(f"Blocked by edge protection ({response.status_code})")
                    response.raise_for_status()

                    if source_config.min_delay:
                        await asyncio.sleep(source_config.min_delay)

                    html = response.text
                    final_url = str(response.url)
                    status_code = response.status_code
                    
                    # Записываем метрику запроса
                    try:
                        from app.instrumentation.celery_metrics import _metrics
                        _metrics.record_scraper_request(str(status_code), source_type or "unknown")
                    except Exception:
                        pass
                    
                    # Сохраняем результат в кэш (если указано имя компании)
                    if company_name:
                        cache_key = (normalized_url, company_name)
                        self._request_cache[cache_key] = (html, final_url, time.time())
                        logger.debug(
                            f"Cached response for {url} (normalized: {normalized_url})"
                        )
                    
                    return html, final_url, status_code
                except NeedsHeadless as exc:
                    logger.warning(f"Headless fetch required for {url}: {exc}")
                    if self._can_use_headless(source_config):
                        html = await fetch_page_with_headless(url, timeout)
                        if html:
                            return html, url, 200
                    break
                except httpx.HTTPStatusError as exc:
                    status = exc.response.status_code
                    logger.debug(f"Attempt {attempt + 1} failed for {url}: {exc}")
                    # Записываем метрику запроса (даже для ошибок)
                    try:
                        from app.instrumentation.celery_metrics import _metrics
                        _metrics.record_scraper_request(str(status), source_type or "unknown")
                    except Exception:
                        pass
                    if status in (404, 410):
                        logger.debug(f"Received {status} for {url}; not retrying further")
                        # Записываем результат в health_service перед выходом
                        if company_id and health_service:
                            await self._record_health_result(
                                company_id, url, False, status, 0, health_service, source_type
                            )
                        break
                    if attempt + 1 < attempts:
                        backoff = (source_config.retry.backoff_factor) ** attempt
                        await asyncio.sleep(min(10, backoff))
                    else:
                        logger.warning(f"Gave up fetching {url} after {attempts} attempts")
                        break
                except (httpx.TimeoutException, httpx.HTTPError) as exc:
                    logger.debug(f"Attempt {attempt + 1} failed for {url}: {exc}")
                    # Записываем метрику timeout/error
                    try:
                        from app.instrumentation.celery_metrics import _metrics
                        error_type = "timeout" if isinstance(exc, httpx.TimeoutException) else "error"
                        _metrics.record_scraper_request(error_type, source_type or "unknown")
                    except Exception:
                        pass
                    if attempt + 1 < attempts:
                        backoff = (source_config.retry.backoff_factor) ** attempt
                        await asyncio.sleep(min(10, backoff))
                    else:
                        logger.warning(f"Gave up fetching {url} after {attempts} attempts")
                        break

            # Записываем метрику для финальной ошибки
            try:
                from app.instrumentation.celery_metrics import _metrics
                _metrics.record_scraper_request("failed", source_type or "unknown")
            except Exception:
                pass
            return None, url, 404  # Предполагаем 404, если не удалось получить HTML
        finally:
            # Всегда освобождаем блокировку
            await self._fetch_lock.release(normalized_url)

    def _extract_articles(
        self,
        soup: BeautifulSoup,
        base_url: str,
        selectors: Iterable[str],
    ) -> List[Dict[str, str]]:
        articles: "OrderedDict[str, str]" = OrderedDict()

        for selector in selectors:
            try:
                elements = soup.select(selector)
            except Exception:
                continue

            for element in elements:
                href = element.get("href", "")
                if not href:
                    continue

                title = element.get_text(strip=True)
                if not title or len(title) < 6:
                    parent = element.parent
                    if parent:
                        title = parent.get_text(strip=True)[:500]
                    if not title or len(title) < 6:
                        continue

                full_url = urljoin(base_url, href)
                if not self._looks_like_article(full_url, base_url):
                    continue

                if full_url not in articles:
                    articles[full_url] = title[:500]

        if not articles:
            nextjs_articles = self._extract_from_nextjs_scripts(soup, base_url)
            for url_value, title_value in nextjs_articles:
                if url_value not in articles:
                    articles[url_value] = title_value

        return [{"url": url_value, "title": title_value} for url_value, title_value in articles.items()]

    def _extract_from_nextjs_scripts(self, soup: BeautifulSoup, base_url: str) -> List[Tuple[str, str]]:
        found: Dict[str, str] = {}

        scripts = soup.find_all("script")
        for script in scripts:
            script_text = script.string
            if not script_text:
                continue

            href_pattern = r'(?:\\?["\'])href(?:\\?["\']):\s*(?:\\?["\'])(/blogs?/[^\\"\'\s]+)(?:\\?["\'])'
            for href_match in re.finditer(href_pattern, script_text):
                href = href_match.group(1)
                full_url = urljoin(base_url, href)
                if not self._looks_like_article(full_url, base_url):
                    continue

                title = self._find_title_near_match(script_text, href_match)
                if title:
                    found.setdefault(full_url, title)

        return list(found.items())

    def _find_title_near_match(self, script_text: str, match: re.Match) -> Optional[str]:
        start_pos = max(0, match.start() - 500)
        end_pos = min(len(script_text), match.end() + 2000)
        context = script_text[start_pos:end_pos]

        title_patterns = [
            r'"title":"((?:\\u[0-9a-fA-F]{4}|[^"\\]){6,})"',
            r'"children":"((?:\\u[0-9a-fA-F]{4}|[^"\\]){6,})"',
        ]

        for pattern in title_patterns:
            title_match = re.search(pattern, context, re.IGNORECASE)
            if not title_match:
                continue
            candidate = title_match.group(1)
            candidate = candidate.replace("\\n", " ").replace("\\t", " ").strip()
            try:
                candidate = bytes(candidate, "utf-8").decode("unicode_escape")
            except Exception:
                pass
            if len(candidate) >= 6:
                return candidate[:500]

        slug = match.group(1).split("/")[-1]
        if slug:
            return slug.replace("-", " ").replace("_", " ").title()[:500]
        return None

    def _persist_snapshot(
        self,
        company_name: str,
        source_id: str,
        url: str,
        html: str,
    ) -> Optional[str]:
        if not settings.SCRAPER_SNAPSHOTS_ENABLED:
            return None

        snapshot_dir = Path(settings.SCRAPER_SNAPSHOT_DIR)
        slug = self._slugify(company_name)
        digest_input = f"{url}|{html}".encode("utf-8")
        digest = hashlib.sha256(digest_input).hexdigest()
        path = snapshot_dir / slug / f"{source_id}_{digest}.html"
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            if not path.exists():
                path.write_text(html, encoding="utf-8")
            return str(path.resolve())
        except Exception as exc:
            logger.warning(f"Failed to persist snapshot for {url}: {exc}")
            return None

    def _infer_category(self, title: str) -> Optional[str]:
        lower = title.lower()
        mapping = [
            (("price", "pricing", "plan", "billing"), NewsCategory.PRICING_CHANGE.value),
            (("funding", "seed", "series a", "series b", "investment"), NewsCategory.FUNDING_NEWS.value),
            (("release", "launched", "launch", "introducing"), NewsCategory.PRODUCT_UPDATE.value),
            (("security", "vulnerability", "patch", "cve"), NewsCategory.SECURITY_UPDATE.value),
            (("api", "sdk"), NewsCategory.API_UPDATE.value),
            (("integration", "integrates with"), NewsCategory.INTEGRATION.value),
            (("deprecated", "deprecation", "sunset"), NewsCategory.FEATURE_DEPRECATION.value),
            (("acquires", "acquisition", "merger"), NewsCategory.ACQUISITION.value),
            (("partner", "partnership"), NewsCategory.PARTNERSHIP.value),
            (("model", "gpt", "llama"), NewsCategory.MODEL_RELEASE.value),
            (("performance", "faster", "improvement"), NewsCategory.PERFORMANCE_IMPROVEMENT.value),
            (("paper", "arxiv", "research"), NewsCategory.RESEARCH_PAPER.value),
            (("webinar", "event", "conference", "meetup"), NewsCategory.COMMUNITY_EVENT.value),
            (("strategy", "vision", "roadmap"), NewsCategory.STRATEGIC_ANNOUNCEMENT.value),
            (("technical", "architecture", "infra", "infrastructure"), NewsCategory.TECHNICAL_UPDATE.value),
        ]
        for keywords, category in mapping:
            if any(keyword in lower for keyword in keywords):
                return category
        return None

    def _looks_like_article(self, full_url: str, base_url: str) -> bool:
        if any(ext in full_url.lower() for ext in [".jpg", ".jpeg", ".png", ".gif", ".pdf", ".zip", ".mp4", ".mp3", ".svg"]):
            return False
        base_domain = urlparse(base_url).netloc
        link_domain = urlparse(full_url).netloc
        if link_domain and base_domain not in link_domain:
            return False
        article_patterns = (
            "/blog/",
            "/blogs/",
            "/news/",
            "/post/",
            "/posts/",
            "/article/",
            "/articles/",
            "/update/",
            "/updates/",
            "/insight/",
            "/insights/",
            "/press/",
            "/press-release/",
        )
        return any(pattern in full_url.lower() for pattern in article_patterns)

    def _requires_headless(self, response: httpx.Response) -> bool:
        if response.status_code in (403, 503):
            return True
        text = response.text[:2000]
        if "Just a moment..." in text or "cf-browser-verification" in text.lower():
            return True
        return False

    def _can_use_headless(self, source_config: SourceConfig) -> bool:
        return source_config.use_headless or settings.SCRAPER_HEADLESS_ENABLED

    @staticmethod
    def _slugify(value: str) -> str:
        return re.sub(r"[^a-zA-Z0-9\-]+", "-", value.lower()).strip("-")

    async def _discover_candidate_sources(self, website: str, limit: int = 8) -> List[str]:
        parsed = urlparse(website)
        if not parsed.scheme or not parsed.netloc:
            return []
        try:
            response = await self.session.get(website, timeout=settings.SCRAPER_TIMEOUT)
            response.raise_for_status()
        except (httpx.HTTPError, ValueError) as exc:
            logger.debug(f"Could not auto-discover sources for %s: {exc}", website)
            return []

        soup = BeautifulSoup(response.text, "html.parser")
        candidates: List[str] = []
        seen: Set[str] = set()

        for anchor in soup.find_all("a", href=True):
            href = anchor["href"].strip()
            if not href or href.startswith("#"):
                continue

            anchor_text = anchor.get_text(strip=True).lower()
            href_lower = href.lower()
            if not any(keyword in anchor_text or keyword in href_lower for keyword in DISCOVERY_KEYWORDS):
                continue

            full_url = urljoin(website, href)
            full_parsed = urlparse(full_url)
            if full_parsed.scheme not in ("http", "https"):
                continue
            if not self._is_same_domain(website, full_url):
                continue

            normalized = full_url.rstrip("/")
            if normalized in seen:
                continue

            seen.add(normalized)
            candidates.append(normalized)

            if len(candidates) >= limit:
                break

        return candidates

    @staticmethod
    def _is_same_domain(base_url: str, target_url: str) -> bool:
        base_netloc = urlparse(base_url).netloc
        target_netloc = urlparse(target_url).netloc

        if not base_netloc or not target_netloc:
            return False

        return target_netloc == base_netloc or target_netloc.endswith(f".{base_netloc}")

