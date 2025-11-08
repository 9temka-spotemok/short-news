"""Universal scraper with multi-source discovery for company blogs and news pages."""

from __future__ import annotations

import json
import re
import time
from collections import Counter, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple, TYPE_CHECKING
from urllib.parse import urljoin, urlparse, urlunparse, urlencode, parse_qsl

import httpx
from bs4 import BeautifulSoup
from loguru import logger

from app.core.config import settings
from app.models.news import NewsCategory

if TYPE_CHECKING:  # pragma: no cover - typing aid
    import feedparser as feedparser_type

try:  # Optional dependency used for RSS/Atom parsing
    import feedparser  # type: ignore
except ImportError:  # pragma: no cover - executed only when dependency missing
    feedparser = None  # type: ignore[assignment]
    FEEDPARSER_AVAILABLE = False
    logger.warning(
        "Optional dependency 'feedparser' is not installed. RSS/Atom feeds will be skipped. "
        "Install it with `pip install feedparser` and rebuild the backend image to enable full scraping."
    )
else:  # pragma: no cover - normal execution path
    FEEDPARSER_AVAILABLE = True

try:  # Optional dependency for bypassing heavy anti-bot pages (e.g., Vercel Vision)
    from playwright.async_api import (
        Browser,
        BrowserContext,
        Error as PlaywrightError,
        async_playwright,
    )
except ImportError:  # pragma: no cover - executed when playwright is not installed
    Browser = BrowserContext = None  # type: ignore[assignment]
    PlaywrightError = Exception  # type: ignore[assignment]
    async_playwright = None  # type: ignore[assignment]
    PLAYWRIGHT_AVAILABLE = False
    logger.warning(
        "Optional dependency 'playwright' is not installed. Some sites protected by bot checks may require it."
    )
else:  # pragma: no cover - normal execution path
    PLAYWRIGHT_AVAILABLE = True


DEFAULT_MAX_REQUESTS = 40
MAX_PAGINATION_DEPTH = 5
MAX_CATEGORY_PAGES = 5
MAX_FEED_ITEMS = 50
SUPPORTED_JSON_LD_TYPES = {"NewsArticle", "BlogPosting", "Article"}
DESKTOP_BROWSER_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/126.0.0.0 Safari/537.36"
)


@dataclass
class ArticleCandidate:
    """Normalized intermediate article representation before final dedupe."""

    url: str
    title: str
    strategy: str
    summary: Optional[str] = None
    description: Optional[str] = None
    published_at: Optional[datetime] = None
    authors: Set[str] = field(default_factory=set)
    tags: Set[str] = field(default_factory=set)
    categories: Set[str] = field(default_factory=set)
    source_type: str = "blog"
    canonical_url: Optional[str] = None
    og_url: Optional[str] = None
    identifiers: Set[str] = field(default_factory=set)
    context_url: Optional[str] = None
    language: Optional[str] = None
    extra: Dict[str, Any] = field(default_factory=dict)

    def all_identifiers(self) -> Set[str]:
        urls = {self.url}
        if self.canonical_url:
            urls.add(self.canonical_url)
        if self.og_url:
            urls.add(self.og_url)
        urls |= {identifier for identifier in self.identifiers if identifier}
        return {normalize_url(url) for url in urls if url}

    def effective_summary(self) -> str:
        if self.summary:
            return self.summary[:500]
        if self.description:
            return self.description[:500]
        return self.title[:500]


def normalize_url(url: str) -> str:
    """Normalize URLs to improve deduplication (strip fragments, normalize path)."""

    try:
        parsed = urlparse(url)
        if not parsed.scheme:
            return url
        path = parsed.path or "/"
        if path != "/":
            path = re.sub(r"/{2,}", "/", path)
            if path.endswith("/") and len(path) > 1:
                path = path.rstrip("/")
        normalized = parsed._replace(fragment="", path=path)
        return urlunparse(normalized)
    except Exception:
        return url


def parse_struct_time(value: Optional[time.struct_time]) -> Optional[datetime]:
    """Convert feedparser struct_time into timezone-aware datetime."""

    if not value:
        return None
    try:
        timestamp = time.mktime(value)
        return datetime.fromtimestamp(timestamp, tz=timezone.utc)
    except (OverflowError, ValueError):
        return None


class UniversalBlogScraper:
    """Universal scraper that aggregates content from multiple discovery strategies."""
    
    def __init__(
        self,
        *,
        max_requests: int = DEFAULT_MAX_REQUESTS,
        request_timeout: Optional[float] = None,
    ) -> None:
        timeout_value = float(request_timeout or settings.SCRAPER_TIMEOUT)
        self.session = httpx.AsyncClient(
            headers={"User-Agent": settings.SCRAPER_USER_AGENT},
            timeout=timeout_value,
            follow_redirects=True,
        )
        self._max_requests = max_requests
        self._request_timeout = timeout_value
        self._deadline: Optional[float] = None
        self._playwright: Optional[Any] = None
        self._playwright_browser: Optional[Browser] = None
        self._playwright_context: Optional[BrowserContext] = None

    def _set_deadline(self, max_duration: Optional[float]) -> None:
        self._deadline = (
            time.monotonic() + max_duration if max_duration and max_duration > 0 else None
        )

    def _clear_deadline(self) -> None:
        self._deadline = None

    def _deadline_reached(self) -> bool:
        return self._deadline is not None and time.monotonic() >= self._deadline

    def _time_remaining(self) -> Optional[float]:
        if self._deadline is None:
            return None
        return self._deadline - time.monotonic()

    def _effective_timeout(self) -> Optional[float]:
        remaining = self._time_remaining()
        if remaining is None:
            return self._request_timeout
        if remaining <= 0:
            return 0.0
        return min(self._request_timeout, remaining)

    async def _ensure_playwright_context(self) -> Optional[BrowserContext]:
        if not PLAYWRIGHT_AVAILABLE or async_playwright is None:
            return None

        if self._playwright is None:
            try:
                self._playwright = await async_playwright().start()
            except PlaywrightError as exc:  # pragma: no cover - startup failure is rare
                logger.debug("Playwright start failed", error=str(exc))
                self._playwright = None
                return None

        if self._playwright_browser is None:
            try:
                self._playwright_browser = await self._playwright.chromium.launch(headless=True)
            except PlaywrightError as exc:  # pragma: no cover - launch failure is rare
                logger.debug("Playwright Chromium launch failed", error=str(exc))
                await self._playwright.stop()
                self._playwright = None
                self._playwright_browser = None
                return None

        if self._playwright_context is None:
            try:
                self._playwright_context = await self._playwright_browser.new_context(
                    user_agent=DESKTOP_BROWSER_USER_AGENT,
                    viewport={"width": 1280, "height": 720},
                )
            except PlaywrightError as exc:  # pragma: no cover - context failure is rare
                logger.debug("Playwright context creation failed", error=str(exc))
                return None

        return self._playwright_context

    async def _fetch_page_with_playwright(self, url: str) -> Optional[Tuple[str, str]]:
        context = await self._ensure_playwright_context()
        if context is None:
            return None

        timeout_seconds = self._effective_timeout()
        timeout_ms = None
        if timeout_seconds is not None:
            if timeout_seconds <= 0:
                return None
            timeout_ms = max(1000, int(timeout_seconds * 1000))

        page = await context.new_page()
        try:
            response = await page.goto(
                url,
                wait_until="networkidle",
                timeout=timeout_ms,
            )
            if response and response.status >= 400:
                logger.debug(
                    "Playwright fetch received non-success status",
                    url=url,
                    status=response.status,
                )
                return None
            html = await page.content()
            final_url = page.url
            return final_url, html
        except PlaywrightError as exc:
            logger.debug("Playwright fetch failed", url=url, error=str(exc))
            return None
        finally:
            await page.close()

    async def scrape_company_blog(
        self,
        company_name: str,
        website: str,
        news_page_url: Optional[str] = None,
        max_articles: int = 10,
        max_duration: Optional[float] = None,
    ) -> List[Dict[str, Any]]:
        """Scrape a company website for news items using layered discovery strategies."""

        logger.bind(company=company_name).info(
            "Scraping blog", news_page_url=news_page_url, max_articles=max_articles
        )

        if max_articles <= 0:
            return []

        self._set_deadline(max_duration)

        candidate_urls = (
            [news_page_url]
            if news_page_url
            else self._detect_blog_urls(website)
        )

        metrics: Counter[str] = Counter()
        all_candidates: List[ArticleCandidate] = []
        request_budget = self._max_requests

        try:
            for candidate_url in candidate_urls:
                if self._deadline_reached():
                    logger.debug(
                        "Time budget exhausted before processing more candidate URLs",
                        url=candidate_url,
                    )
                    break
                if request_budget <= 0:
                    logger.debug(
                        "Request budget exhausted before processing URL",
                        url=candidate_url,
                    )
                    break

                try:
                    fetched = await self._fetch_page(candidate_url)
                except httpx.HTTPError as exc:
                    logger.debug(
                        "Failed to fetch candidate URL",
                        url=candidate_url,
                        error=str(exc),
                    )
                    continue

                if not fetched:
                    continue

                request_budget = max(0, request_budget - 1)
                final_url, response_text = fetched
                soup = BeautifulSoup(response_text, "html.parser")

                metrics["bootstrap"] += 1

                if self._deadline_reached():
                    logger.debug(
                        "Time budget exhausted after bootstrap fetch",
                        url=final_url,
                    )
                    break

                # RSS / JSON feeds
                feed_candidates = await self._collect_from_feeds(
                    final_url, soup, request_budget
                )
                request_budget = max(0, request_budget - feed_candidates.extra_requests)
                all_candidates.extend(feed_candidates.items)
                metrics.update(feed_candidates.metrics)

                if self._deadline_reached():
                    logger.debug(
                        "Time budget exhausted after feed collection",
                        url=final_url,
                    )
                    break

                # JSON-LD structured data
                json_ld_candidates = self._collect_from_json_ld(final_url, soup)
                metrics["json_ld"] += bool(json_ld_candidates)
                all_candidates.extend(json_ld_candidates)

                # CMS adapters and SPA script data
                adapter_results = await self._collect_from_cms_adapters(
                    final_url, soup, request_budget
                )
                request_budget = max(0, request_budget - adapter_results.extra_requests)
                metrics.update(adapter_results.metrics)
                all_candidates.extend(adapter_results.items)

                if self._deadline_reached():
                    logger.debug(
                        "Time budget exhausted after CMS adapters",
                        url=final_url,
                    )
                    break

                # HTML discovery with pagination & categories
                html_results = await self._crawl_html_pages(
                    final_url,
                    soup,
                    request_budget,
                    target_items=max(max_articles * 3, 20),
                )
                request_budget = max(0, request_budget - html_results.extra_requests)
                metrics.update(html_results.metrics)
                all_candidates.extend(html_results.items)

                if len(all_candidates) >= max_articles * 3:
                    break
        
            if not all_candidates:
                logger.warning("No candidates discovered", company=company_name)
                return []

            deduped = await self._deduplicate_and_enrich(
                company_name,
                all_candidates,
                max_articles=max_articles,
                request_budget=request_budget,
            )

            logger.info(
                "Scraping completed",
                company=company_name,
                total_candidates=len(all_candidates),
                selected=len(deduped),
                strategies={k: v for k, v in metrics.items() if v},
            )

            return deduped
        finally:
            self._clear_deadline()

    async def scrape_multiple_companies(
        self,
        companies: List[Dict[str, str]],
        max_articles_per_company: int = 5,
    ) -> List[Dict[str, Any]]:
        logger.info("Scraping multiple companies", count=len(companies))
        results: List[Dict[str, Any]] = []

        for company in companies:
            name = company.get("name")
            website = company.get("website")
            if not name or not website:
                continue
            items = await self.scrape_company_blog(
                company_name=name,
                website=website,
                max_articles=max_articles_per_company,
            )
            results.extend(items)

        logger.info("Completed multi-company scrape", total=len(results))
        return results

    async def close(self) -> None:
        await self.session.aclose()
        if self._playwright_context is not None:
            try:
                await self._playwright_context.close()
            except PlaywrightError:  # pragma: no cover - close failures are rare
                pass
            finally:
                self._playwright_context = None

        if self._playwright_browser is not None:
            try:
                await self._playwright_browser.close()
            except PlaywrightError:  # pragma: no cover - close failures are rare
                pass
            finally:
                self._playwright_browser = None

        if self._playwright is not None:
            try:
                await self._playwright.stop()
            except PlaywrightError:  # pragma: no cover - stop failures are rare
                pass
            finally:
                self._playwright = None

    # ------------------------------------------------------------------
    # Discovery helpers
    # ------------------------------------------------------------------

    def _detect_blog_urls(self, website: str) -> List[str]:
        parsed = urlparse(website)
        if not parsed.scheme or not parsed.netloc:
            return [website]

        base = f"{parsed.scheme}://{parsed.netloc}".rstrip("/")
        candidates = {
            base,
            f"{base}/blog",
            f"{base}/blogs",
            f"{base}/news",
            f"{base}/newsroom",
            f"{base}/press",
            f"{base}/press-releases",
            f"{base}/insights",
            f"{base}/updates",
            f"{base}/stories",
            f"{base}/company/blog",
            f"{base}/company/news",
            f"{base}/resources/blog",
            f"{base}/hub/blog",
        }
        return list({normalize_url(url) for url in candidates})

    async def _fetch_page(self, url: str) -> Optional[Tuple[str, str]]:
        if self._deadline_reached():
            logger.debug("Time budget exhausted before fetching URL", url=url)
            return None

        timeout = self._effective_timeout()
        if timeout is not None and timeout <= 0:
            logger.debug("Non-positive timeout before fetching URL", url=url)
            return None

        request_kwargs: Dict[str, Any] = {}
        if timeout is not None:
            request_kwargs["timeout"] = timeout

        response = await self.session.get(url, **request_kwargs)
        if response.status_code >= 400:
            logger.debug("Non-success status", url=url, status=response.status_code)
            if response.status_code in {401, 403, 429, 503}:
                fallback = await self._fetch_page_with_playwright(url)
                if fallback:
                    return fallback
            return None
        # Some providers (e.g., Vercel Vision) return 200 but deliver a security challenge page.
        if "Vercel Security Checkpoint" in response.text:
            logger.debug("Detected Vercel checkpoint page, switching to Playwright", url=url)
            fallback = await self._fetch_page_with_playwright(url)
            if fallback:
                return fallback
        if (
            "__NEXT_DATA__" not in response.text
            and "/_next/static/" in response.text
        ):
            logger.debug(
                "Detected client-rendered Next.js page, attempting Playwright fallback",
                url=url,
            )
            fallback = await self._fetch_page_with_playwright(url)
            if fallback:
                return fallback
        return str(response.url), response.text

    async def _collect_from_feeds(
        self,
        page_url: str,
        soup: BeautifulSoup,
        request_budget: int,
    ) -> "CollectionResult":
        feed_urls = self._discover_feed_urls(page_url, soup)
        metrics: Counter[str] = Counter()
        items: List[ArticleCandidate] = []
        extra_requests = 0

        for feed_url in feed_urls:
            if self._deadline_reached():
                logger.debug("Time budget exhausted before processing feed", url=feed_url)
                break
            if request_budget - extra_requests <= 0:
                break

            try:
                timeout = self._effective_timeout()
                if timeout is not None and timeout <= 0:
                    break
                request_kwargs: Dict[str, Any] = {}
                if timeout is not None:
                    request_kwargs["timeout"] = timeout
                response = await self.session.get(feed_url, **request_kwargs)
                extra_requests += 1
            except httpx.HTTPError as exc:
                logger.debug("Feed fetch failed", url=feed_url, error=str(exc))
                continue

            if response.status_code >= 400 or not response.content:
                continue

            content_type = response.headers.get("content-type", "").lower()
            parsed_items: List[ArticleCandidate] = []
            if "json" in content_type or feed_url.endswith(".json"):
                parsed_items = self._parse_json_feed(response, feed_url)
                strategy = "json_feed"
            else:
                if not FEEDPARSER_AVAILABLE:
                    logger.warning(
                        "feedparser dependency missing – skipping XML feed",
                        url=feed_url,
                    )
                    continue
                parsed_items = self._parse_xml_feed(response, feed_url)
                strategy = "rss"

            if parsed_items:
                metrics[strategy] += 1
                items.extend(parsed_items[:MAX_FEED_ITEMS])

        return CollectionResult(items=items, metrics=metrics, extra_requests=extra_requests)

    def _discover_feed_urls(self, page_url: str, soup: BeautifulSoup) -> List[str]:
        base = page_url
        feed_urls: Set[str] = set()

        for link in soup.find_all("link", attrs={"rel": True, "href": True}):
            rel = link.get("rel") or []
            if isinstance(rel, str):
                rel_values = {rel.lower()}
            else:
                rel_values = {value.lower() for value in rel}
            if "alternate" not in rel_values:
                continue
            mime = (link.get("type") or "").lower()
            href = link.get("href")
            if not href:
                continue
            if any(token in mime for token in ["rss", "atom", "xml", "json"]):
                feed_urls.add(normalize_url(urljoin(base, href)))

        parsed = urlparse(base)
        base_root = f"{parsed.scheme}://{parsed.netloc}".rstrip("/")
        common_paths = [
            "rss",
            "rss.xml",
            "feed",
            "feed.xml",
            "atom.xml",
            "index.xml",
            "blog/rss",
            "blog/rss.xml",
            "blog/feed",
            "news/rss",
            "news/feed",
        ]

        for path in common_paths:
            feed_urls.add(normalize_url(urljoin(base_root + "/", path)))

        # WordPress JSON endpoint
        feed_urls.add(normalize_url(urljoin(base_root + "/", "wp-json/wp/v2/posts")))
        # Ghost default feed
        feed_urls.add(normalize_url(urljoin(base_root + "/", "rss/")))

        return list(feed_urls)

    def _parse_xml_feed(self, response: httpx.Response, feed_url: str) -> List[ArticleCandidate]:
        if not FEEDPARSER_AVAILABLE or feedparser is None:
            return []
        parsed = feedparser.parse(response.content)
        results: List[ArticleCandidate] = []

        for entry in parsed.entries:
            link = entry.get("link") or entry.get("id")
            title = entry.get("title")
            if not link or not title:
                            continue
                        
            published = (
                parse_struct_time(entry.get("published_parsed"))
                or parse_struct_time(entry.get("updated_parsed"))
            )

            summary = entry.get("summary") or entry.get("description")
            tags = {
                tag.get("term")
                for tag in entry.get("tags", [])
                if isinstance(tag, dict)
            }
            authors = set()
            if "author" in entry and entry["author"]:
                authors.add(entry["author"])
            for author_obj in entry.get("authors", []):
                if isinstance(author_obj, dict) and author_obj.get("name"):
                    authors.add(author_obj["name"])

            identifiers = {
                entry.get("id"),
                entry.get("guid"),
                entry.get("link"),
            }

            candidate = ArticleCandidate(
                url=normalize_url(link),
                title=title.strip(),
                summary=summary.strip() if isinstance(summary, str) else None,
                published_at=published,
                authors={author.strip() for author in authors if author},
                tags={tag.strip() for tag in tags if tag},
                strategy="rss",
                identifiers={normalize_url(identifier) for identifier in identifiers if identifier},
                extra={"feed_url": feed_url, "feed_version": parsed.version},
            )
            results.append(candidate)

        return results

    def _parse_json_feed(self, response: httpx.Response, feed_url: str) -> List[ArticleCandidate]:
        try:
            payload = response.json()
        except json.JSONDecodeError:
            return []

        results: List[ArticleCandidate] = []

        # Support JSON Feed spec and WordPress REST API posts
        if isinstance(payload, dict) and "items" in payload:
            items = payload.get("items") or []
            for item in items:
                link = item.get("url") or item.get("external_url")
                title = item.get("title")
                if not link or not title:
                    continue
                published = self._coerce_datetime(item.get("date_published") or item.get("date_modified"))
                summary = item.get("summary") or item.get("content_text")
                tags = set(item.get("tags") or [])
                authors = set()
                for author in item.get("authors", []):
                    if isinstance(author, dict) and author.get("name"):
                        authors.add(author["name"])

                candidate = ArticleCandidate(
                    url=normalize_url(link),
                    title=title.strip(),
                    summary=summary.strip() if isinstance(summary, str) else None,
                    published_at=published,
                    authors=authors,
                    tags=tags,
                    strategy="json_feed",
                    identifiers={normalize_url(item.get("id"))} if item.get("id") else set(),
                )
                results.append(candidate)
            return results

        if isinstance(payload, list):
            # WordPress posts
            for post in payload:
                link = post.get("link") or post.get("guid", {}).get("rendered")
                title = (
                    (post.get("title") or {}).get("rendered")
                    if isinstance(post.get("title"), dict)
                    else post.get("title")
                )
                if not link or not title:
                    continue
                summary_html = (post.get("excerpt") or {}).get("rendered")
                summary = BeautifulSoup(summary_html or "", "html.parser").get_text(" ").strip() or None
                published = self._coerce_datetime(post.get("date_gmt") or post.get("date") or post.get("modified_gmt"))
                tags = set()
                if isinstance(post.get("tags"), list):
                    tags |= {str(tag) for tag in post["tags"]}
                candidate = ArticleCandidate(
                    url=normalize_url(link),
                    title=BeautifulSoup(title, "html.parser").get_text(" ").strip(),
                    summary=summary,
                    published_at=published,
                    tags=tags,
                    strategy="wp_json",
                    identifiers={normalize_url(str(post.get("id")))},
                )
                results.append(candidate)

        return results

    def _collect_from_json_ld(self, page_url: str, soup: BeautifulSoup) -> List[ArticleCandidate]:
        scripts = soup.find_all(
            "script",
            attrs={"type": lambda value: value and "ld+json" in value.lower()},
        )
        results: List[ArticleCandidate] = []
        for script in scripts:
            if not script.string:
                continue
            try:
                data = json.loads(script.string)
            except json.JSONDecodeError:
                        continue
                    
            for node in self._iterate_json_ld_nodes(data):
                node_type = node.get("@type")
                if not node_type:
                    continue
                node_types = {node_type} if isinstance(node_type, str) else set(node_type)
                if not node_types & SUPPORTED_JSON_LD_TYPES:
                        continue
                url = node.get("url") or node.get("mainEntityOfPage") or node.get("@id")
                title = node.get("headline") or node.get("name")
                if not url or not title:
                        continue
                summary = node.get("description")
                published = self._coerce_datetime(node.get("datePublished") or node.get("dateCreated"))
                authors = set()
                author_node = node.get("author")
                if isinstance(author_node, dict):
                    if author_node.get("name"):
                        authors.add(author_node["name"])
                elif isinstance(author_node, list):
                    for author in author_node:
                        if isinstance(author, dict) and author.get("name"):
                            authors.add(author["name"])
                        elif isinstance(author, str):
                            authors.add(author)

                tags = set()
                keywords = node.get("keywords")
                if isinstance(keywords, list):
                    tags |= {kw for kw in keywords if isinstance(kw, str)}
                elif isinstance(keywords, str):
                    tags |= {kw.strip() for kw in keywords.split(",") if kw.strip()}

                category = node.get("articleSection")
                categories = {category} if isinstance(category, str) else set(category or [])

                candidate = ArticleCandidate(
                    url=normalize_url(urljoin(page_url, url)),
                    title=title.strip(),
                    summary=summary.strip() if isinstance(summary, str) else None,
                    published_at=published,
                    authors=authors,
                    tags=tags,
                    categories={cat for cat in categories if cat},
                    strategy="json_ld",
                    identifiers={normalize_url(node.get("@id"))} if node.get("@id") else set(),
                )
                results.append(candidate)

        return results

    def _iterate_json_ld_nodes(self, data: Any) -> Iterable[Dict[str, Any]]:
        stack: List[Any] = [data]
        seen_ids: Set[int] = set()

        while stack:
            current = stack.pop()

            if isinstance(current, dict):
                current_id = id(current)
                if current_id in seen_ids:
                    continue
                seen_ids.add(current_id)

                graph = current.get("@graph")
                if isinstance(graph, list):
                    stack.extend(reversed(graph))
                    continue

                yield current

            elif isinstance(current, list):
                stack.extend(reversed(current))

    async def _collect_from_cms_adapters(
        self,
        page_url: str,
        soup: BeautifulSoup,
        request_budget: int,
    ) -> "CollectionResult":
        cms_types = self._detect_cms_types(page_url, soup)
        items: List[ArticleCandidate] = []
        metrics: Counter[str] = Counter()
        extra_requests = 0

        for cms in cms_types:
            if self._deadline_reached():
                logger.debug("Time budget exhausted before CMS adapter", cms=cms)
                break
            if cms == "next_js":
                next_data_candidates = self._extract_from_next_data(soup, page_url)
                if next_data_candidates:
                    metrics["next_js"] += 1
                    items.extend(next_data_candidates)
            elif cms == "ghost":
                # Ghost feed is usually /rss/
                ghost_feed = normalize_url(urljoin(page_url, "/rss/"))
                ghost_result = await self._collect_from_feeds(
                    ghost_feed,
                    soup,
                    max(0, request_budget - extra_requests),
                )
                extra_requests += ghost_result.extra_requests
                metrics["ghost"] += bool(ghost_result.items)
                items.extend(ghost_result.items)
            elif cms == "medium":
                medium_feed = self._build_medium_feed(page_url)
                if medium_feed:
                    medium_result = await self._collect_from_feeds(
                        medium_feed,
                        soup,
                        max(0, request_budget - extra_requests),
                    )
                    extra_requests += medium_result.extra_requests
                    metrics["medium"] += bool(medium_result.items)
                    items.extend(medium_result.items)
            elif cms in {"hubspot", "webflow"}:
                json_endpoint = self._build_format_json_endpoint(page_url)
                if json_endpoint and request_budget - extra_requests > 0:
                    if self._deadline_reached():
                        break
                    try:
                        timeout = self._effective_timeout()
                        if timeout is not None and timeout <= 0:
                            break
                        kwargs: Dict[str, Any] = {}
                        if timeout is not None:
                            kwargs["timeout"] = timeout
                        response = await self.session.get(json_endpoint, **kwargs)
                        extra_requests += 1
                    except httpx.HTTPError:
                        continue
                    if response.status_code < 400:
                        cms_items = self._parse_cms_json_listing(response, page_url, cms)
                        metrics[cms] += bool(cms_items)
                        items.extend(cms_items)

        return CollectionResult(items=items, metrics=metrics, extra_requests=extra_requests)

    def _detect_cms_types(self, page_url: str, soup: BeautifulSoup) -> Set[str]:
        types: Set[str] = set()
        html = soup.prettify().lower()

        generator_meta = soup.find("meta", attrs={"name": "generator"})
        generator = generator_meta.get("content", "").lower() if generator_meta else ""

        if "ghost" in html or "ghost" in generator:
            types.add("ghost")
        if "medium" in urlparse(page_url).netloc or "medium" in generator:
            types.add("medium")
        if "hs-scripts" in html or "hubspot" in generator:
            types.add("hubspot")
        if "webflow" in generator or "webflow" in html:
            types.add("webflow")
        if soup.find("script", attrs={"id": "__NEXT_DATA__"}) or "__next" in html:
            types.add("next_js")

        return types

    def _extract_from_next_data(self, soup: BeautifulSoup, base_url: str) -> List[ArticleCandidate]:
        results: List[ArticleCandidate] = []
        data_script = soup.find("script", attrs={"id": "__NEXT_DATA__"})
        if not data_script or not data_script.string:
            return self._extract_from_nextjs_scripts(soup, base_url)

        try:
            data = json.loads(data_script.string)
        except json.JSONDecodeError:
            return []
        
        def walk(node: Any) -> Iterable[Dict[str, Any]]:
            if isinstance(node, dict):
                if {"title", "href"} & node.keys():
                    yield node
                for value in node.values():
                    yield from walk(value)
            elif isinstance(node, list):
                for item in node:
                    yield from walk(item)

        for candidate in walk(data):
            href = candidate.get("href") or candidate.get("url")
            title = candidate.get("title") or candidate.get("name")
            if not href or not title:
                continue
            url = normalize_url(urljoin(base_url, href))
            results.append(
                ArticleCandidate(
                    url=url,
                    title=title.strip(),
                    strategy="next_js",
                    summary=(candidate.get("description") or "").strip() or None,
                )
            )

        return results or self._extract_from_nextjs_scripts(soup, base_url)

    def _extract_from_nextjs_scripts(self, soup: BeautifulSoup, base_url: str) -> List[ArticleCandidate]:
        results: List[ArticleCandidate] = []
        scripts = soup.find_all("script")
        for script in scripts:
            script_text = script.string
            if not script_text:
                continue

            if "self.__next_f.push" in script_text:
                stream_results = self._extract_from_next_f_stream(script_text, base_url)
                if stream_results:
                    results.extend(stream_results)
                    continue

            for href_match in re.finditer(r"href\"?[:=]\"(/(?:blogs?|articles?)/[^\"']+)", script_text):
                href = href_match.group(1)
                url = normalize_url(urljoin(base_url, href))
                title_match = re.search(r"title\"?[:=]\"([^\"]{10,})\"", script_text)
                title = (
                    title_match.group(1)
                    if title_match
                    else href.split("/")[-1].replace("-", " ").title()
                )
                results.append(
                    ArticleCandidate(
                        url=url,
                        title=title.strip(),
                        strategy="next_js_script",
                    )
                )
        return results

    def _decode_js_string(self, value: str) -> str:
        try:
            return json.loads(f'"{value}"')
        except Exception:
            try:
                return bytes(value, "utf-8").decode("unicode_escape")
            except Exception:
                return value

    def _extract_from_next_f_stream(self, script_text: str, base_url: str) -> List[ArticleCandidate]:
        results: List[ArticleCandidate] = []

        href_iterator = [
            m
            for m in re.finditer(r'href\\":\\"(?P<href>/[^\\"\\]+)\\"', script_text)
            if '/blog' in m.group('href')
        ]
        for index, match in enumerate(href_iterator):
            href = match.group("href")
            start = match.start()
            end = href_iterator[index + 1].start() if index + 1 < len(href_iterator) else len(script_text)
            block = script_text[start:end]

            def search(pattern: str) -> Optional[str]:
                found = re.search(pattern, block, re.DOTALL)
                return self._decode_js_string(found.group(1)) if found else None

            title = search(r'blogs_postTitle__[^"}]+\\",\\"children\\":\\"([^\\"]+)\\"')
            excerpt = search(r'blogs_postExcerpt__[^"}]+\\",\\"children\\":\\"([^\\"]*)\\"')
            date_raw = search(r'blogs_postDate__[^"}]+\\",\\"children\\":\\"([^\\"]+)\\"')
            author = search(r'blogs_postAuthor__[^"}]+\\",\\"children\\":\[\\"by \",\\"([^\\"\]]+)\\"\]')
            read_time = search(r'blogs_postReadingTime__[^"}]+\\",\\"children\\":\[\\"([^\\"\]]+)\\"')

            if not title:
                continue

            published_at: Optional[datetime] = None
            if date_raw:
                for fmt in ("%m/%d/%Y", "%m/%d/%y"):
                    try:
                        published_at = datetime.strptime(date_raw, fmt).replace(tzinfo=timezone.utc)
                        break
                    except ValueError:
                        continue

            candidate = ArticleCandidate(
                url=normalize_url(urljoin(base_url, href)),
                title=title.strip(),
                summary=excerpt.strip() if excerpt else None,
                published_at=published_at,
                strategy="next_js_stream",
            )
            if author:
                candidate.authors.add(author.strip())
            if read_time:
                candidate.extra["reading_time"] = read_time.strip()
            results.append(candidate)

        return results

    def _build_medium_feed(self, page_url: str) -> Optional[str]:
        parsed = urlparse(page_url)
        host_parts = parsed.netloc.split(".")
        if "medium" in host_parts:
            return normalize_url(f"{parsed.scheme}://{parsed.netloc}/feed")
        path = parsed.path.strip("/")
        if path:
            slug = path.split("/")[0]
            return normalize_url(f"https://medium.com/feed/{slug}")
        return None

    def _build_format_json_endpoint(self, page_url: str) -> Optional[str]:
        parsed = urlparse(page_url)
        if not parsed.scheme or not parsed.netloc:
            return None

        query_params = dict(parse_qsl(parsed.query, keep_blank_values=True))
        if query_params.get("format") == "json":
            return normalize_url(urlunparse(parsed))

        query_params["format"] = "json"
        new_query = urlencode(query_params, doseq=True)
        return normalize_url(urlunparse(parsed._replace(query=new_query)))

    def _parse_cms_json_listing(
        self, response: httpx.Response, page_url: str, cms: str
    ) -> List[ArticleCandidate]:
        try:
            data = response.json()
        except json.JSONDecodeError:
            return []

        items: List[ArticleCandidate] = []

        if cms == "hubspot" and isinstance(data, dict):
            posts = data.get("posts") or data.get("results") or []
            for post in posts:
                url = post.get("url") or post.get("absoluteUrl")
                title = post.get("title")
                if not url or not title:
                                continue
                summary = post.get("metaDescription") or post.get("postSummary")
                published = self._coerce_datetime(post.get("publishDate") or post.get("published"))
                items.append(
                    ArticleCandidate(
                        url=normalize_url(url),
                        title=title.strip(),
                        summary=summary.strip() if isinstance(summary, str) else None,
                        published_at=published,
                        strategy="hubspot_json",
                    )
                )

        if cms == "webflow":
            collections = []
            if isinstance(data, dict):
                collections = data.get("items") or data.get("posts") or []
            elif isinstance(data, list):
                collections = data
            for item in collections:
                url = item.get("url") or item.get("slug")
                title = item.get("name") or item.get("title")
                if not url or not title:
                        continue
                summary = item.get("summary") or item.get("excerpt")
                absolute_url = normalize_url(urljoin(page_url, url))
                items.append(
                    ArticleCandidate(
                        url=absolute_url,
                        title=title.strip(),
                        summary=summary.strip() if isinstance(summary, str) else None,
                        strategy="webflow_json",
                    )
                )

        return items

    async def _crawl_html_pages(
        self,
        start_url: str,
        start_soup: BeautifulSoup,
        request_budget: int,
        *,
        target_items: int,
    ) -> "CollectionResult":
        metrics: Counter[str] = Counter()
        items: List[ArticleCandidate] = []
        queue: deque[Tuple[str, BeautifulSoup, int]] = deque()
        queue.append((start_url, start_soup, 0))
        visited: Set[str] = {normalize_url(start_url)}
        extra_requests = 0

        while queue and len(items) < target_items:
            if self._deadline_reached():
                logger.debug("Time budget exhausted during HTML crawl", url=start_url)
                break
            current_url, current_soup, depth = queue.popleft()
            metrics["html"] += 1
            html_candidates = self._extract_article_links(current_soup, current_url)
            items.extend(html_candidates)

            if depth >= MAX_PAGINATION_DEPTH:
                        continue
                    
            pagination_links = self._discover_pagination_links(current_soup, current_url)
            category_links = (
                set()
                if depth >= MAX_CATEGORY_PAGES
                else self._discover_category_links(current_soup, current_url)
            )

            for link in pagination_links | category_links:
                if extra_requests >= request_budget:
                    break
                if self._deadline_reached():
                    logger.debug("Time budget exhausted before fetching pagination link", url=link)
                    break
                normalized = normalize_url(link)
                if normalized in visited:
                    continue
                try:
                    fetched = await self._fetch_page(link)
                except httpx.HTTPError:
                    continue
                if not fetched:
                    continue
                extra_requests += 1
                visited.add(normalized)
                final_url, response_text = fetched
                queue.append((final_url, BeautifulSoup(response_text, "html.parser"), depth + 1))
                        
        return CollectionResult(items=items, metrics=metrics, extra_requests=extra_requests)

    def _extract_article_links(self, soup: BeautifulSoup, base_url: str) -> List[ArticleCandidate]:
        selectors = [
            "article a",
            "article h2 a",
            "article h3 a",
            "div[class*='post'] a",
            "div[class*='article'] a",
            "div[class*='card'] a",
            "li[class*='post'] a",
            "h2 a",
            "h3 a",
            "h4 a",
            "a[class*='post']",
            "a[class*='article']",
            "a[href*='/blog/']",
            "a[href*='/news/']",
            "a[href*='/press']",
            "a[href*='/story']",
            "a[href*='/insight']",
        ]

        found: Dict[str, ArticleCandidate] = {}
        base_domain = urlparse(base_url).netloc

        for selector in selectors:
            for element in soup.select(selector):
                href = element.get("href")
                if not href:
                    continue
                url = normalize_url(urljoin(base_url, href))
                if any(ext in url.lower() for ext in [".jpg", ".jpeg", ".png", ".gif", ".pdf", ".mp4", ".svg"]):
                    continue
                if base_domain and urlparse(url).netloc and base_domain not in urlparse(url).netloc:
                    continue
                title = element.get_text(strip=True)
                if not title or len(title) < 8:
                    continue
            
                if url not in found:
                    found[url] = ArticleCandidate(
                        url=url,
                        title=title[:500],
                        strategy="html",
                    )

        if not found:
            all_links = soup.find_all("a", href=True)
            for link in all_links:
                href = link.get("href")
                if not href:
                    continue
                url = normalize_url(urljoin(base_url, href))
                if any(pattern in url.lower() for pattern in ["/blog/", "/news/", "/article/", "/post/"]):
                    title = link.get_text(strip=True)
                    if title and len(title) >= 8:
                        found[url] = ArticleCandidate(
                            url=url,
                            title=title[:500],
                            strategy="html_fallback",
                        )

        return list(found.values())

    def _discover_pagination_links(self, soup: BeautifulSoup, base_url: str) -> Set[str]:
        links: Set[str] = set()
        next_rel = soup.find("link", attrs={"rel": "next", "href": True})
        if next_rel:
            links.add(urljoin(base_url, next_rel["href"]))

        for anchor in soup.find_all("a", href=True):
            text = anchor.get_text(strip=True).lower()
            if text in {"next", "older", "load more"} or "page" in anchor.get("class", []):
                links.add(urljoin(base_url, anchor["href"]))

        return links

    def _discover_category_links(self, soup: BeautifulSoup, base_url: str) -> Set[str]:
        links: Set[str] = set()
        for anchor in soup.find_all("a", href=True):
            href = anchor["href"].lower()
            if any(segment in href for segment in ["/category/", "/tag/", "/topics/", "?category="]):
                links.add(urljoin(base_url, anchor["href"]))
        return links

    # ------------------------------------------------------------------
    # Deduplication & enrichment
    # ------------------------------------------------------------------

    async def _deduplicate_and_enrich(
        self, 
        company_name: str,
        candidates: List[ArticleCandidate],
        *,
        max_articles: int,
        request_budget: int,
    ) -> List[Dict[str, Any]]:
        deduped: Dict[str, ArticleCandidate] = {}

        for candidate in candidates:
            identifiers = candidate.all_identifiers()
            existing_key = next((key for key in identifiers if key in deduped), None)
            if existing_key:
                existing = deduped[existing_key]
                deduped[existing_key] = self._merge_candidates(existing, candidate)
                continue
            canonical = next(iter(identifiers), candidate.url)
            deduped[canonical] = candidate

        enriched: List[ArticleCandidate] = []
        remaining_budget = max(0, request_budget)

        for candidate in deduped.values():
            if len(enriched) >= max_articles:
                break
            if self._deadline_reached():
                logger.debug("Time budget exhausted during enrichment", url=candidate.url)
                break
            if remaining_budget <= 0:
                enriched.append(candidate)
                continue
            
            meta_result = await self._enrich_article_metadata(candidate)
            if meta_result.extra_requests:
                remaining_budget -= meta_result.extra_requests
            enriched.append(meta_result.item)

        final_items: List[Dict[str, Any]] = []
        now = datetime.now(timezone.utc)
        for idx, article in enumerate(enriched[:max_articles]):
            published = article.published_at or now - timedelta(minutes=idx)
            source_type = self._detect_source_type(article.url)
            category = self._infer_category(article)

            final_items.append(
                {
                    "title": article.title[:500],
                    "content": article.extra.get("content") or article.effective_summary(),
                    "summary": article.effective_summary(),
                    "source_url": article.url,
                    "source_type": source_type,
                    "company_name": company_name,
                    "category": category,
                    "published_at": published,
                    "authors": sorted(article.authors) if article.authors else None,
                    "tags": sorted(article.tags) if article.tags else None,
                    "strategy": article.strategy,
                }
            )

        return final_items

    def _merge_candidates(
        self,
        existing: ArticleCandidate,
        incoming: ArticleCandidate,
    ) -> ArticleCandidate:
        existing.summary = existing.summary or incoming.summary
        existing.description = existing.description or incoming.description
        if not existing.published_at and incoming.published_at:
            existing.published_at = incoming.published_at
        existing.authors |= incoming.authors
        existing.tags |= incoming.tags
        existing.categories |= incoming.categories
        if not existing.canonical_url and incoming.canonical_url:
            existing.canonical_url = incoming.canonical_url
        if not existing.og_url and incoming.og_url:
            existing.og_url = incoming.og_url
        existing.identifiers |= incoming.identifiers
        existing.extra = {**incoming.extra, **existing.extra}
        return existing

    async def _enrich_article_metadata(
        self, candidate: ArticleCandidate
    ) -> "MetadataResult":
        if self._deadline_reached():
            logger.debug("Time budget exhausted before enriching article", url=candidate.url)
            return MetadataResult(item=candidate, extra_requests=0)
        timeout = self._effective_timeout()
        if timeout is not None and timeout <= 0:
            return MetadataResult(item=candidate, extra_requests=0)
        kwargs: Dict[str, Any] = {}
        if timeout is not None:
            kwargs["timeout"] = timeout
        try:
            response = await self.session.get(candidate.url, **kwargs)
        except httpx.HTTPError as exc:
            logger.debug("Failed to enrich article", url=candidate.url, error=str(exc))
            return MetadataResult(item=candidate, extra_requests=0)

        if response.status_code >= 400:
            return MetadataResult(item=candidate, extra_requests=1)

        soup = BeautifulSoup(response.text, "html.parser")

        canonical = soup.find("link", attrs={"rel": "canonical", "href": True})
        if canonical:
            candidate.canonical_url = normalize_url(canonical["href"])

        og_url = soup.find("meta", attrs={"property": "og:url", "content": True})
        if og_url:
            candidate.og_url = normalize_url(og_url["content"])

        og_title = soup.find("meta", attrs={"property": "og:title", "content": True})
        if og_title and og_title["content"]:
            candidate.title = og_title["content"].strip()

        description = soup.find("meta", attrs={"property": "og:description", "content": True})
        if description and description["content"]:
            candidate.summary = candidate.summary or description["content"].strip()

        meta_author = soup.find("meta", attrs={"name": "author", "content": True})
        if meta_author and meta_author["content"]:
            candidate.authors.add(meta_author["content"].strip())

        published_meta = soup.find(
            "meta",
            attrs={"property": "article:published_time", "content": True},
        )
        if published_meta and published_meta["content"]:
            published = self._coerce_datetime(published_meta["content"])
            if published:
                candidate.published_at = candidate.published_at or published

        tag_meta = soup.find_all("meta", attrs={"property": "article:tag", "content": True})
        for tag in tag_meta:
            candidate.tags.add(tag["content"].strip())

        json_ld_candidates = self._collect_from_json_ld(candidate.url, soup)
        for json_candidate in json_ld_candidates:
            candidate = self._merge_candidates(candidate, json_candidate)

        return MetadataResult(item=candidate, extra_requests=1)

    def _detect_source_type(self, url: str) -> str:
        lowered = url.lower()
        if "/press" in lowered:
            return "press_release"
        if "/news" in lowered or "newsroom" in lowered:
            return "news_site"
        return "blog"

    def _infer_category(self, candidate: ArticleCandidate) -> str:
        text = " ".join(
            filter(
                None,
                [candidate.title.lower(), (candidate.summary or "").lower()],
            )
        )
        tag_text = " ".join(tag.lower() for tag in candidate.tags)
        combined = f"{text} {tag_text}".strip()

        mapping = [
            ("price pricing plan billing", NewsCategory.PRICING_CHANGE.value),
            ("funding seed series investment", NewsCategory.FUNDING_NEWS.value),
            ("launch released release introducing", NewsCategory.PRODUCT_UPDATE.value),
            ("security vulnerability patch cve", NewsCategory.SECURITY_UPDATE.value),
            ("api sdk", NewsCategory.API_UPDATE.value),
            ("integration integrates", NewsCategory.INTEGRATION.value),
            ("deprecated deprecation sunset", NewsCategory.FEATURE_DEPRECATION.value),
            ("acquires acquisition merger", NewsCategory.ACQUISITION.value),
            ("partner partnership", NewsCategory.PARTNERSHIP.value),
            ("model gpt llama", NewsCategory.MODEL_RELEASE.value),
            ("performance faster improvement", NewsCategory.PERFORMANCE_IMPROVEMENT.value),
            ("paper arxiv research", NewsCategory.RESEARCH_PAPER.value),
            ("webinar event conference meetup", NewsCategory.COMMUNITY_EVENT.value),
            ("strategy vision roadmap", NewsCategory.STRATEGIC_ANNOUNCEMENT.value),
            ("technical architecture infra", NewsCategory.TECHNICAL_UPDATE.value),
        ]

        for keywords, category in mapping:
            if any(keyword in combined for keyword in keywords.split()):
                return category

        for category in candidate.categories:
            normalized = category.lower()
            if "press" in normalized:
                return NewsCategory.STRATEGIC_ANNOUNCEMENT.value
            if "research" in normalized:
                return NewsCategory.RESEARCH_PAPER.value

        return NewsCategory.PRODUCT_UPDATE.value

    def _coerce_datetime(self, value: Optional[str]) -> Optional[datetime]:
        if not value or not isinstance(value, str):
            return None
        try:
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
            return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        except ValueError:
            if not FEEDPARSER_AVAILABLE or feedparser is None:
                return None
            try:
                parsed = feedparser.parse("""<feed><updated>%s</updated></feed>""" % value)
                struct_time_value = (
                    parsed.feed.get("updated_parsed")
                    or parsed.feed.get("published_parsed")
                )
                return parse_struct_time(struct_time_value)
            except Exception:
                return None


@dataclass
class CollectionResult:
    items: List[ArticleCandidate]
    metrics: Counter[str]
    extra_requests: int


@dataclass
class MetadataResult:
    item: ArticleCandidate
    extra_requests: int