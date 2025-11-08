"""
Universal scraper for company blogs and news pages with configurable sources,
retry policies, rate limiting, and SPA fallbacks.
"""

from __future__ import annotations

import asyncio
import hashlib
import re
from collections import OrderedDict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup
from loguru import logger

from app.core.config import settings
from app.models.news import NewsCategory
from app.scrapers.config_loader import ScraperConfigRegistry, SourceConfig
from app.scrapers.headless import fetch_page_with_headless
from app.scrapers.rate_limiter import RateLimiter


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


class NeedsHeadless(RuntimeError):
    """Raised when a request is blocked and should be retried via headless browser."""


class UniversalBlogScraper:
    """Universal scraper that can scrape blogs from any company."""

    def __init__(
        self,
        config_registry: Optional[ScraperConfigRegistry] = None,
        rate_limiter: Optional[RateLimiter] = None,
    ):
        self.session = httpx.AsyncClient(
            headers={"User-Agent": settings.SCRAPER_USER_AGENT},
            timeout=settings.SCRAPER_TIMEOUT,
            follow_redirects=True,
        )
        self.config_registry = config_registry or ScraperConfigRegistry()
        self.rate_limiter = rate_limiter or RateLimiter()

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

    async def scrape_company_blog(
        self,
        company_name: str,
        website: str,
        news_page_url: Optional[str] = None,
        max_articles: int = 10,
        source_overrides: Optional[List[Dict[str, Any]]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Scrape blog/news from a company website.
        """
        logger.info(
            "Scraping blog for %s (news_page_url=%s, overrides=%s)",
            company_name,
            news_page_url,
            bool(source_overrides),
        )

        news_items: List[Dict[str, Any]] = []
        seen_urls: Set[str] = set()

        source_configs = self.config_registry.get_sources(
            company_name=company_name,
            website=website,
            manual_url=news_page_url,
            overrides=source_overrides,
        )

        if not source_configs:
            logger.warning("No source configurations found for %s", company_name)
            return []

        for source_config in source_configs:
            per_source_limit = source_config.max_articles or max_articles
            logger.info(
                "Scraping source %s for %s with %d max articles",
                source_config.id,
                company_name,
                per_source_limit,
            )
            try:
                source_items = await self._scrape_source(
                    company_name=company_name,
                    source_config=source_config,
                    max_articles=per_source_limit,
                    seen_urls=seen_urls,
                )
                news_items.extend(source_items)
            except Exception as exc:
                logger.warning(
                    "Failed to scrape source %s for %s: %s",
                    source_config.id,
                    company_name,
                    exc,
                )

        if news_items:
            logger.info("Successfully scraped %d items from %s", len(news_items), company_name)
        else:
            logger.warning("No articles found for %s", company_name)

        return news_items

    async def scrape_multiple_companies(
        self,
        companies: List[Dict[str, str]],
        max_articles_per_company: int = 5,
        source_override_map: Optional[Dict[str, List[Dict[str, Any]]]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Scrape blogs from multiple companies.
        """
        logger.info("Scraping blogs from %d companies...", len(companies))

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
            "Total scraped: %d news items from %d companies", len(all_news), len(companies)
        )
        return all_news

    async def close(self) -> None:
        """Close HTTP session."""
        await self.session.aclose()

    async def _scrape_source(
        self,
        company_name: str,
        source_config: SourceConfig,
        max_articles: int,
        seen_urls: Set[str],
    ) -> List[Dict[str, Any]]:
        items: List[Dict[str, Any]] = []

        for raw_url in source_config.urls:
            url = str(raw_url)
            html, final_url = await self._fetch_with_retry(url, source_config)
            if not html:
                continue

            snapshot_path = self._persist_snapshot(company_name, source_config.id, final_url, html)
            soup = BeautifulSoup(html, "html.parser")
            selectors = source_config.selectors or DEFAULT_ARTICLE_SELECTORS
            articles = self._extract_articles(soup, final_url, selectors)

            if not articles:
                logger.debug(
                    "No articles found for %s at %s (source %s)",
                    company_name,
                    final_url,
                    source_config.id,
                )
                continue

            logger.info(
                "Found %d articles for %s at %s (source %s)",
                len(articles),
                company_name,
                final_url,
                source_config.id,
            )

            for idx, article in enumerate(articles):
                if article["url"] in seen_urls:
                    continue
                seen_urls.add(article["url"])

                inferred_category = self._infer_category(article["title"])
                published_at = datetime.now() - timedelta(days=idx)
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

        return items

    async def _fetch_with_retry(
        self,
        url: str,
        source_config: SourceConfig,
    ) -> Tuple[Optional[str], str]:
        attempts = max(1, source_config.retry.attempts + 1)
        timeout = source_config.timeout or settings.SCRAPER_TIMEOUT
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
                response = await self.session.get(url, timeout=timeout, proxies=proxy)
                if self._requires_headless(response):
                    raise NeedsHeadless(f"Blocked by edge protection ({response.status_code})")
                response.raise_for_status()

                if source_config.min_delay:
                    await asyncio.sleep(source_config.min_delay)

                return response.text, str(response.url)
            except NeedsHeadless as exc:
                logger.warning("Headless fetch required for %s: %s", url, exc)
                if self._can_use_headless(source_config):
                    html = await fetch_page_with_headless(url, timeout)
                    if html:
                        return html, url
                break
            except (httpx.TimeoutException, httpx.HTTPError) as exc:
                logger.debug("Attempt %d failed for %s: %s", attempt + 1, url, exc)
                if attempt + 1 < attempts:
                    backoff = (source_config.retry.backoff_factor) ** attempt
                    await asyncio.sleep(min(10, backoff))
                else:
                    logger.warning("Gave up fetching %s after %d attempts", url, attempts)
                    break

        return None, url

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
            logger.warning("Failed to persist snapshot for %s: %s", url, exc)
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

"""
Universal scraper for company blogs and news pages
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from loguru import logger
import httpx
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import re

from app.core.config import settings
from app.models.news import NewsCategory


class UniversalBlogScraper:
    """Universal scraper that can scrape blogs from any company"""
    
    def __init__(self):
        self.session = httpx.AsyncClient(
            headers={'User-Agent': settings.SCRAPER_USER_AGENT},
            timeout=settings.SCRAPER_TIMEOUT,
            follow_redirects=True
        )
    
    def _detect_blog_url(self, website: str) -> List[str]:
        """Detect possible blog/news URLs from company website"""
        # Extract base domain from any URL
        parsed = urlparse(website)
        base_domain = f"{parsed.scheme}://{parsed.netloc}".rstrip('/')
        
        # Common blog/news URL patterns
        patterns = [
            f"{base_domain}/blog",
            f"{base_domain}/blogs",  # Next.js sites often use /blogs
            f"{base_domain}/blog/",
            f"{base_domain}/blogs/",  # Next.js sites often use /blogs/
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
    
    def _extract_articles(self, soup: BeautifulSoup, base_url: str) -> List[Dict[str, Any]]:
        """Extract article links from page"""
        articles = []
        
        # Common article selectors - expanded list for better coverage
        selectors = [
            'article a',
            'article h2 a',
            'article h3 a',
            'div.post a',
            'div.blog-post a',
            'div.news-item a',
            'div.card a',
            'div.entry a',
            'li.post a',
            'li.article a',
            'h2 a',
            'h3 a',
            'h4 a',
            'a[href*="/blog/"]',
            'a[href*="/news/"]',
            'a[href*="/post/"]',
            'a[href*="/article/"]',
            'a[href*="/posts/"]',
            '.article-link',
            '.post-link',
            '.news-link',
            '.entry-title a',
            '.post-title a',
            '[class*="post"] a',
            '[class*="article"] a',
            '[class*="blog"] a',
            '[class*="news"] a',
        ]
        
        found_links = set()
        
        for selector in selectors:
            try:
                elements = soup.select(selector)
                
                for element in elements:
                    href = element.get('href', '')
                    # Try to get title from multiple places
                    title = element.get_text(strip=True)
                    if not title or len(title) < 10:
                        # Try getting title from parent or nearby elements
                        parent = element.parent
                        if parent:
                            title = parent.get_text(strip=True)[:500]
                            if len(title) < 10:
                                continue
                        else:
                            continue
                    
                    # Skip if no href
                    if not href:
                        continue
                    
                    # Build full URL
                    full_url = urljoin(base_url, href)
                    
                    # Skip duplicates
                    if full_url in found_links:
                        continue
                    
                    # Skip non-article URLs (images, PDFs, etc.)
                    if any(ext in full_url.lower() for ext in ['.jpg', '.jpeg', '.png', '.gif', '.pdf', '.zip', '.mp4', '.mp3', '.svg']):
                        continue
                    
                    # Skip social media and external links
                    base_domain = urlparse(base_url).netloc
                    link_domain = urlparse(full_url).netloc
                    if link_domain and base_domain not in link_domain:
                        continue
                    
                    # Check if looks like an article URL
                    article_patterns = ['/blog/', '/blogs/', '/news/', '/post/', '/posts/', '/article/', '/articles/', '/update/', '/updates/', '/insight/', '/insights/', '/press/', '/press-release/']
                    if any(pattern in full_url.lower() for pattern in article_patterns):
                        found_links.add(full_url)
                        articles.append({
                            'url': full_url,
                            'title': title[:500]
                        })
            except Exception as e:
                logger.debug(f"Error processing selector {selector}: {e}")
                continue
        
        # If no articles found with selectors, try a fallback approach:
        # Look for any links that contain blog/news patterns in their URL
        if not articles:
            try:
                all_links = soup.find_all('a', href=True)
                for link in all_links:
                    href = link.get('href', '')
                    if not href:
                        continue
                    
                    full_url = urljoin(base_url, href)
                    
                    # Check if URL pattern matches article patterns
                    article_patterns = ['/blog/', '/blogs/', '/news/', '/post/', '/posts/', '/article/']
                    if any(pattern in full_url.lower() for pattern in article_patterns):
                        # Skip duplicates and non-content files
                        if full_url in found_links:
                            continue
                        if any(ext in full_url.lower() for ext in ['.jpg', '.jpeg', '.png', '.gif', '.pdf']):
                            continue
                        
                        # Check domain
                        base_domain = urlparse(base_url).netloc
                        link_domain = urlparse(full_url).netloc
                        if link_domain and base_domain not in link_domain:
                            continue
                        
                        title = link.get_text(strip=True)
                        if title and len(title) >= 10:
                            found_links.add(full_url)
                            articles.append({
                                'url': full_url,
                                'title': title[:500]
                            })
            except Exception as e:
                logger.debug(f"Error in fallback article extraction: {e}")
        
        # If no articles found with CSS selectors or fallback, try Next.js script parsing
        if not articles:
            logger.debug("No articles found with CSS selectors, trying Next.js script parsing")
            nextjs_articles = self._extract_from_nextjs_scripts(soup, base_url)
            if nextjs_articles:
                articles.extend(nextjs_articles)
        
        return articles
    
    def _extract_from_nextjs_scripts(self, soup: BeautifulSoup, base_url: str) -> List[Dict[str, Any]]:
        """
        Extract article links from Next.js script tags containing JSON data
        
        Next.js stores page data in <script> tags with format:
        self.__next_f.push([1, "JSON_DATA"])
        
        This method parses those scripts to extract article links and titles.
        """
        articles = []
        found_links = set()
        
        try:
            # Find all script tags
            scripts = soup.find_all('script')
            
            for script in scripts:
                script_text = script.string
                if not script_text:
                    continue
                
                # Method 1: Look for href patterns in Next.js JSON data
                # Pattern: "href":"/blogs/article-slug" with optional escaping
                href_pattern = r'(?:\\?["\'])href(?:\\?["\']):\s*(?:\\?["\'])(/blogs?/[^"\'\\]+)(?:\\?["\'])'
                href_matches = re.finditer(href_pattern, script_text)
                
                for href_match in href_matches:
                    href = href_match.group(1)
                    full_url = urljoin(base_url, href)
                    
                    if full_url in found_links:
                        continue
                    
                    # Skip non-article URLs
                    if any(ext in full_url.lower() for ext in ['.jpg', '.jpeg', '.png', '.gif', '.pdf', '.zip', '.mp4', '.mp3', '.svg']):
                        continue
                    
                    # Check domain
                    base_domain = urlparse(base_url).netloc
                    link_domain = urlparse(full_url).netloc
                    if link_domain and base_domain not in link_domain:
                        continue
                    
                    # Try to find title near this href
                    # Look in a window around the href match
                    start_pos = max(0, href_match.start() - 500)
                    end_pos = min(len(script_text), href_match.end() + 2000)
                    context = script_text[start_pos:end_pos]
                    
                    # Try multiple title patterns
                    title = None
                    
                    title_patterns = [
                        # Escaped JSON strings (\") with className hints first
                        r'\\"className\\":\\"[^\\"]*(?:postTitle|articleTitle)[^\\"]*\\",\\"children\\":\\"((?:\\u[0-9a-fA-F]{4}|[^\\"\\]){10,})\\"',
                        r'\\"title\\":\\"((?:\\u[0-9a-fA-F]{4}|[^\\"\\]){10,})\\"',
                        r'\\"children\\":\\"((?:\\u[0-9a-fA-F]{4}|[^\\"\\]){10,})\\"',
                        # Unescaped JSON strings
                        r'"className":"[^"]*(?:postTitle|articleTitle)[^"]*","children":"((?:\\u[0-9a-fA-F]{4}|[^"\\]){10,})"',
                        r'"title":"((?:\\u[0-9a-fA-F]{4}|[^"\\]){10,})"',
                        r'"children":"((?:\\u[0-9a-fA-F]{4}|[^"\\]){10,})"',
                    ]
                    
                    for pattern in title_patterns:
                        title_match = re.search(pattern, context, re.IGNORECASE)
                        if not title_match:
                            continue
                        candidate = title_match.group(1)
                        candidate = candidate.replace('\\n', ' ').replace('\\t', ' ').strip()
                        try:
                            candidate = bytes(candidate, 'utf-8').decode('unicode_escape')
                        except Exception:
                            pass
                        try:
                            candidate = candidate.encode('latin1').decode('utf-8')
                        except Exception:
                            pass
                        if len(candidate) < 10:
                            continue
                        # Ensure we are capturing the article title, not a page-level title
                        if 'postTitle' not in context and 'articleTitle' not in context:
                            continue
                        title = candidate
                        break

                    if not title or len(title) < 10:
                        slug = href.split('/')[-1]
                        title = slug.replace('-', ' ').replace('_', ' ').title()
                    
                    if title and len(title) >= 10:
                        found_links.add(full_url)
                        articles.append({
                            'url': full_url,
                            'title': title[:500]
                        })
                
                # Method 2: Look for Next.js data structure with article links
                # Sometimes Next.js stores data in a different format
                # Look for patterns like: "/blogs/article-slug" directly in script
                if not articles:
                    # More aggressive pattern: find any /blogs/ or /blog/ URLs in script
                    url_pattern = r'(?:\\?["\'])(/blogs?/[a-zA-Z0-9\-]+)(?:\\?["\'])'
                    url_matches = re.finditer(url_pattern, script_text)
                    
                    for url_match in url_matches:
                        href = url_match.group(1)
                        full_url = urljoin(base_url, href)
                        
                        if full_url in found_links:
                            continue
                        
                        # Skip non-article URLs
                        if any(ext in full_url.lower() for ext in ['.jpg', '.jpeg', '.png', '.gif', '.pdf']):
                            continue
                        
                        # Check domain
                        base_domain = urlparse(base_url).netloc
                        link_domain = urlparse(full_url).netloc
                        if link_domain and base_domain not in link_domain:
                            continue
                        
                        # Extract title from slug
                        slug = href.split('/')[-1]
                        title = slug.replace('-', ' ').replace('_', ' ').title()
                        
                        if title and len(title) >= 10:
                            found_links.add(full_url)
                            articles.append({
                                'url': full_url,
                                'title': title[:500]
                            })
        
        except Exception as e:
            logger.debug(f"Error extracting from Next.js scripts: {e}")
            return []
        
        if articles:
            logger.info(f"Extracted {len(articles)} articles from Next.js scripts")
        
        return articles
    
    async def scrape_company_blog(
        self, 
        company_name: str, 
        website: str,
        news_page_url: Optional[str] = None,
        max_articles: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Scrape blog/news from a company website
        
        Args:
            company_name: Name of the company
            website: Company website URL
            news_page_url: Optional manual URL for news/blog page (if auto-detection fails)
            max_articles: Maximum number of articles to scrape
        
        Returns:
            List of news items found
        """
        logger.info(f"Scraping blog for: {company_name}, news_page_url: {news_page_url}")
        
        news_items = []
        
        try:
            # If manual news page URL is provided, use it instead of auto-detection
            if news_page_url:
                blog_urls = [news_page_url]
                logger.info(f"Using manual news page URL: {news_page_url}")
            else:
                # Try different blog URL patterns (auto-detection)
                blog_urls = self._detect_blog_url(website)
            
            for blog_url in blog_urls:
                try:
                    logger.info(f"Trying URL: {blog_url}")
                    response = await self.session.get(blog_url)
                    
                    # Check final URL after redirects
                    final_url = str(response.url)
                    if final_url != blog_url:
                        logger.debug(f"Redirected from {blog_url} to {final_url}")
                        # Skip if redirected to a different path that doesn't match blog patterns
                        # This helps avoid cases where all URLs redirect to home page
                        if '/blog' not in final_url.lower() and '/news' not in final_url.lower():
                            if 'blog' in blog_url.lower() or 'news' in blog_url.lower():
                                logger.debug(f"Skipping {final_url} - redirect away from blog/news section")
                                continue
                    
                    # Skip if not found
                    if response.status_code == 404:
                        continue
                    
                    if response.status_code != 200:
                        logger.debug(f"Non-200 status {response.status_code} for {blog_url}")
                        continue
                    
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # Extract articles
                    articles = self._extract_articles(soup, final_url)
                    
                    if not articles:
                        # Log when page loads but no articles found - helps with debugging
                        logger.debug(f"Page loaded successfully from {final_url} but no articles found. "
                                   f"Page title: {soup.title.string if soup.title else 'N/A'}")
                        continue
                    
                    logger.info(f"Found {len(articles)} articles at {final_url}")
                    
                    # Process articles
                    for idx, article in enumerate(articles[:max_articles]):
                        # Detect source type from URL
                        source_type = 'blog'
                        if '/news/' in article['url'].lower():
                            source_type = 'news_site'
                        elif '/press/' in article['url'].lower():
                            source_type = 'press_release'
                        
                        # Infer category from title heuristics
                        title_lower = article['title'].lower()
                        inferred_category = None
                        try:
                            if any(k in title_lower for k in ['price', 'pricing', 'plan', 'billing']):
                                inferred_category = NewsCategory.PRICING_CHANGE.value
                            elif any(k in title_lower for k in ['funding', 'seed', 'series a', 'series b', 'investment']):
                                inferred_category = NewsCategory.FUNDING_NEWS.value
                            elif any(k in title_lower for k in ['release', 'launched', 'launch', 'introducing']):
                                inferred_category = NewsCategory.PRODUCT_UPDATE.value
                            elif any(k in title_lower for k in ['security', 'vulnerability', 'patch', 'cve']):
                                inferred_category = NewsCategory.SECURITY_UPDATE.value
                            elif any(k in title_lower for k in ['api', 'sdk']):
                                inferred_category = NewsCategory.API_UPDATE.value
                            elif any(k in title_lower for k in ['integration', 'integrates with']):
                                inferred_category = NewsCategory.INTEGRATION.value
                            elif any(k in title_lower for k in ['deprecated', 'deprecation', 'sunset']):
                                inferred_category = NewsCategory.FEATURE_DEPRECATION.value
                            elif any(k in title_lower for k in ['acquires', 'acquisition', 'merger']):
                                inferred_category = NewsCategory.ACQUISITION.value
                            elif any(k in title_lower for k in ['partner', 'partnership']):
                                inferred_category = NewsCategory.PARTNERSHIP.value
                            elif any(k in title_lower for k in ['model', 'gpt', 'llama', 'release']):
                                inferred_category = NewsCategory.MODEL_RELEASE.value
                            elif any(k in title_lower for k in ['performance', 'faster', 'improvement']):
                                inferred_category = NewsCategory.PERFORMANCE_IMPROVEMENT.value
                            elif any(k in title_lower for k in ['paper', 'arxiv', 'research']):
                                inferred_category = NewsCategory.RESEARCH_PAPER.value
                            elif any(k in title_lower for k in ['webinar', 'event', 'conference', 'meetup']):
                                inferred_category = NewsCategory.COMMUNITY_EVENT.value
                            elif any(k in title_lower for k in ['strategy', 'vision', 'roadmap']):
                                inferred_category = NewsCategory.STRATEGIC_ANNOUNCEMENT.value
                            elif any(k in title_lower for k in ['technical', 'architecture', 'infra', 'infrastructure']):
                                inferred_category = NewsCategory.TECHNICAL_UPDATE.value
                        except Exception:
                            inferred_category = None

                        news_items.append({
                            'title': article['title'],
                            'content': f"Article from {company_name}: {article['title']}",
                            'summary': article['title'][:200],
                            'source_url': article['url'],
                            'source_type': source_type,
                            'company_name': company_name,
                            'category': inferred_category or NewsCategory.PRODUCT_UPDATE.value,
                            'topic': None,
                            'sentiment': None,
                            'priority_score': 0.5,
                            'raw_snapshot_url': None,
                            'published_at': datetime.now() - timedelta(days=idx),
                        })
                    
                    # If we found articles, stop trying other URLs
                    if news_items:
                        break
                        
                except httpx.HTTPError as e:
                    logger.debug(f"HTTP error for {blog_url}: {e}")
                    continue
                except Exception as e:
                    logger.debug(f"Error scraping {blog_url}: {e}")
                    continue
            
            if news_items:
                logger.info(f"Successfully scraped {len(news_items)} items from {company_name}")
            else:
                logger.warning(f"No articles found for {company_name}")
            
            return news_items
            
        except Exception as e:
            logger.error(f"Failed to scrape {company_name}: {e}")
            return []
    
    async def scrape_multiple_companies(
        self, 
        companies: List[Dict[str, str]], 
        max_articles_per_company: int = 5
    ) -> List[Dict[str, Any]]:
        """Scrape blogs from multiple companies"""
        logger.info(f"Scraping blogs from {len(companies)} companies...")
        
        all_news = []
        
        for company in companies:
            company_name = company.get('name')
            website = company.get('website')
            
            if not company_name or not website:
                continue
            
            news = await self.scrape_company_blog(
                company_name, 
                website, 
                max_articles=max_articles_per_company
            )
            all_news.extend(news)
        
        logger.info(f"Total scraped: {len(all_news)} news items from {len(companies)} companies")
        return all_news
    
    async def close(self):
        """Close HTTP session"""
        await self.session.aclose()






