"""
SEO Signal Collector Service

Сбор SEO сигналов с сайтов компаний:
- Meta tags (title, description, keywords, og:tags)
- Structured data (JSON-LD, Schema.org)
- robots.txt
- sitemap.xml
- Canonical URLs
- hreflang tags
"""

import json
import re
from typing import Dict, List, Optional, Any
from urllib.parse import urljoin, urlparse
from datetime import datetime, timezone

import httpx
from bs4 import BeautifulSoup
from loguru import logger

from app.core.config import settings


class SEOSignalCollector:
    """Сервис для сбора SEO сигналов с сайтов компаний"""

    def __init__(self):
        """Инициализация сервиса"""
        self.session = httpx.AsyncClient(
            headers={"User-Agent": settings.SCRAPER_USER_AGENT},
            timeout=settings.SCRAPER_TIMEOUT,
            follow_redirects=True,
        )

    async def close(self):
        """Закрыть HTTP сессию"""
        await self.session.aclose()

    async def collect_seo_signals(self, website_url: str) -> Dict[str, Any]:
        """
        Собирает все SEO сигналы с сайта.
        
        Args:
            website_url: URL главной страницы сайта
            
        Returns:
            {
                "website_url": "...",
                "collected_at": "...",
                "meta_tags": {...},
                "structured_data": [...],
                "robots_txt": {...},
                "sitemap": {...},
                "canonical_urls": [...],
                "hreflang_tags": [...]
            }
        """
        if not website_url:
            return {}
        
        try:
            logger.info(f"Collecting SEO signals for {website_url}")
            
            # Нормализовать URL
            normalized_url = self._normalize_url(website_url)
            if not normalized_url:
                return {}
            
            # Загрузить главную страницу
            response = await self.session.get(normalized_url)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'lxml')
            
            # Собрать все сигналы
            signals = {
                "website_url": normalized_url,
                "collected_at": datetime.now(timezone.utc).isoformat(),
                "meta_tags": self.extract_meta_tags(soup),
                "structured_data": self.extract_structured_data(soup),
                "canonical_urls": self._extract_canonical_urls(soup, normalized_url),
                "hreflang_tags": self._extract_hreflang_tags(soup, normalized_url),
            }
            
            # Проверить robots.txt и sitemap
            parsed = urlparse(normalized_url)
            base_url = f"{parsed.scheme}://{parsed.netloc}"
            
            signals["robots_txt"] = await self.check_robots_txt(base_url)
            signals["sitemap"] = await self.check_sitemap(base_url)
            
            logger.info(f"Successfully collected SEO signals for {normalized_url}")
            return signals
            
        except httpx.HTTPError as e:
            logger.error(f"HTTP error collecting SEO signals for {website_url}: {e}")
            return {}
        except Exception as e:
            logger.error(f"Error collecting SEO signals for {website_url}: {e}")
            return {}

    def extract_meta_tags(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """
        Извлекает meta теги со страницы.
        
        Returns:
            {
                "title": "...",
                "description": "...",
                "keywords": "...",
                "og_tags": {...},
                "twitter_tags": {...},
                "other_meta": {...}
            }
        """
        meta_tags = {
            "title": None,
            "description": None,
            "keywords": None,
            "og_tags": {},
            "twitter_tags": {},
            "other_meta": {},
        }
        
        # Title
        title_tag = soup.find('title')
        if title_tag:
            meta_tags["title"] = title_tag.get_text(strip=True)
        
        # Meta description
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if meta_desc:
            meta_tags["description"] = meta_desc.get('content', '').strip()
        
        # Meta keywords
        meta_keywords = soup.find('meta', attrs={'name': 'keywords'})
        if meta_keywords:
            meta_tags["keywords"] = meta_keywords.get('content', '').strip()
        
        # Open Graph теги
        og_tags = soup.find_all('meta', attrs={'property': re.compile(r'^og:')})
        for tag in og_tags:
            prop = tag.get('property', '').replace('og:', '')
            content = tag.get('content', '')
            if prop and content:
                meta_tags["og_tags"][prop] = content
        
        # Twitter Card теги
        twitter_tags = soup.find_all('meta', attrs={'name': re.compile(r'^twitter:')})
        for tag in twitter_tags:
            name = tag.get('name', '').replace('twitter:', '')
            content = tag.get('content', '')
            if name and content:
                meta_tags["twitter_tags"][name] = content
        
        # Другие meta теги
        other_meta = soup.find_all('meta', attrs={'name': True})
        for tag in other_meta:
            name = tag.get('name', '')
            if name not in ['description', 'keywords']:
                content = tag.get('content', '')
                if content:
                    meta_tags["other_meta"][name] = content
        
        return meta_tags

    def extract_structured_data(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """
        Извлекает structured data (JSON-LD, Schema.org) со страницы.
        
        Returns:
            Список объектов structured data
        """
        structured_data = []
        
        # JSON-LD скрипты
        json_ld_scripts = soup.find_all('script', type='application/ld+json')
        for script in json_ld_scripts:
            try:
                content = script.string
                if content:
                    data = json.loads(content)
                    if isinstance(data, list):
                        structured_data.extend(data)
                    else:
                        structured_data.append(data)
            except json.JSONDecodeError:
                logger.warning("Failed to parse JSON-LD script")
                continue
        
        # Микроданные (Schema.org)
        microdata_items = soup.find_all(attrs={'itemscope': True})
        for item in microdata_items:
            item_data = {}
            item_type = item.get('itemtype', '')
            if item_type:
                item_data['@type'] = item_type
            
            # Извлечь свойства
            props = item.find_all(attrs={'itemprop': True})
            for prop in props:
                prop_name = prop.get('itemprop', '')
                prop_value = prop.get('content') or prop.get_text(strip=True)
                if prop_name and prop_value:
                    if prop_name in item_data:
                        if not isinstance(item_data[prop_name], list):
                            item_data[prop_name] = [item_data[prop_name]]
                        item_data[prop_name].append(prop_value)
                    else:
                        item_data[prop_name] = prop_value
            
            if item_data:
                structured_data.append(item_data)
        
        return structured_data

    def _extract_canonical_urls(self, soup: BeautifulSoup, base_url: str) -> List[str]:
        """Извлекает canonical URLs со страницы"""
        canonical_urls = []
        
        # Canonical link
        canonical = soup.find('link', rel='canonical')
        if canonical and canonical.get('href'):
            canonical_urls.append(urljoin(base_url, canonical.get('href')))
        
        # Alternate canonical
        alternates = soup.find_all('link', rel='alternate')
        for alt in alternates:
            if alt.get('hreflang') == 'x-default':
                href = alt.get('href')
                if href:
                    canonical_urls.append(urljoin(base_url, href))
        
        return canonical_urls

    def _extract_hreflang_tags(self, soup: BeautifulSoup, base_url: str) -> List[Dict[str, str]]:
        """Извлекает hreflang теги со страницы"""
        hreflang_tags = []
        
        hreflang_links = soup.find_all('link', rel='alternate', hreflang=True)
        for link in hreflang_links:
            hreflang = link.get('hreflang', '')
            href = link.get('href', '')
            if hreflang and href:
                hreflang_tags.append({
                    "hreflang": hreflang,
                    "href": urljoin(base_url, href),
                })
        
        return hreflang_tags

    async def check_robots_txt(self, base_url: str) -> Dict[str, Any]:
        """
        Проверяет robots.txt файл.
        
        Args:
            base_url: Базовый URL сайта (например, https://example.com)
            
        Returns:
            {
                "exists": True/False,
                "content": "...",
                "sitemap_urls": [...],
                "user_agents": [...]
            }
        """
        robots_url = urljoin(base_url, '/robots.txt')
        
        try:
            response = await self.session.get(robots_url)
            response.raise_for_status()
            
            content = response.text
            sitemap_urls = []
            user_agents = []
            
            # Парсинг robots.txt
            lines = content.split('\n')
            current_ua = None
            for line in lines:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                
                if ':' in line:
                    key, value = line.split(':', 1)
                    key = key.strip().lower()
                    value = value.strip()
                    
                    if key == 'user-agent':
                        current_ua = value
                        if current_ua not in user_agents:
                            user_agents.append(current_ua)
                    elif key == 'sitemap':
                        if value not in sitemap_urls:
                            sitemap_urls.append(value)
            
            return {
                "exists": True,
                "content": content[:1000],  # Ограничить длину
                "sitemap_urls": sitemap_urls,
                "user_agents": user_agents,
            }
            
        except httpx.HTTPError:
            return {
                "exists": False,
                "content": None,
                "sitemap_urls": [],
                "user_agents": [],
            }

    async def check_sitemap(self, base_url: str) -> Dict[str, Any]:
        """
        Проверяет sitemap.xml файл.
        
        Args:
            base_url: Базовый URL сайта
            
        Returns:
            {
                "exists": True/False,
                "urls": [...],
                "sitemap_index": True/False,
                "sitemap_urls": [...]
            }
        """
        sitemap_url = urljoin(base_url, '/sitemap.xml')
        
        try:
            response = await self.session.get(sitemap_url)
            response.raise_for_status()
            
            content = response.text
            soup = BeautifulSoup(content, 'xml')
            
            urls = []
            sitemap_urls = []
            
            # Проверить, это sitemap index или обычный sitemap
            sitemapindex = soup.find('sitemapindex')
            if sitemapindex:
                # Это sitemap index
                sitemaps = sitemapindex.find_all('sitemap')
                for sitemap in sitemaps:
                    loc = sitemap.find('loc')
                    if loc:
                        sitemap_urls.append(loc.get_text(strip=True))
                
                return {
                    "exists": True,
                    "urls": [],
                    "sitemap_index": True,
                    "sitemap_urls": sitemap_urls,
                }
            else:
                # Обычный sitemap
                urlset = soup.find('urlset')
                if urlset:
                    url_elements = urlset.find_all('url')
                    for url_elem in url_elements:
                        loc = url_elem.find('loc')
                        if loc:
                            urls.append(loc.get_text(strip=True))
                
                return {
                    "exists": True,
                    "urls": urls[:100],  # Ограничить количество
                    "sitemap_index": False,
                    "sitemap_urls": [],
                }
            
        except httpx.HTTPError:
            return {
                "exists": False,
                "urls": [],
                "sitemap_index": False,
                "sitemap_urls": [],
            }

    def compare_seo_signals(
        self,
        previous: Dict[str, Any],
        current: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Сравнивает SEO сигналы между двумя снимками.
        
        Args:
            previous: Предыдущие SEO сигналы
            current: Текущие SEO сигналы
            
        Returns:
            {
                "has_changes": True/False,
                "meta_tags_changes": {...},
                "structured_data_changes": {...},
                "robots_txt_changes": {...},
                "sitemap_changes": {...}
            }
        """
        if not previous or not current:
            return {"has_changes": False, "error": "Missing signal data"}
        
        changes = {
            "has_changes": False,
            "meta_tags_changes": self._compare_meta_tags(
                previous.get("meta_tags", {}),
                current.get("meta_tags", {})
            ),
            "structured_data_changes": self._compare_structured_data(
                previous.get("structured_data", []),
                current.get("structured_data", [])
            ),
            "robots_txt_changes": self._compare_robots_txt(
                previous.get("robots_txt", {}),
                current.get("robots_txt", {})
            ),
            "sitemap_changes": self._compare_sitemap(
                previous.get("sitemap", {}),
                current.get("sitemap", {})
            ),
        }
        
        # Определить, есть ли изменения
        changes["has_changes"] = (
            changes["meta_tags_changes"]["has_changes"] or
            changes["structured_data_changes"]["has_changes"] or
            changes["robots_txt_changes"]["has_changes"] or
            changes["sitemap_changes"]["has_changes"]
        )
        
        return changes

    def _compare_meta_tags(
        self,
        previous: Dict[str, Any],
        current: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Сравнивает meta теги"""
        changes = {
            "has_changes": False,
            "title_changed": previous.get("title") != current.get("title"),
            "description_changed": previous.get("description") != current.get("description"),
            "keywords_changed": previous.get("keywords") != current.get("keywords"),
            "og_tags_changed": previous.get("og_tags") != current.get("og_tags"),
            "twitter_tags_changed": previous.get("twitter_tags") != current.get("twitter_tags"),
        }
        
        changes["has_changes"] = any([
            changes["title_changed"],
            changes["description_changed"],
            changes["keywords_changed"],
            changes["og_tags_changed"],
            changes["twitter_tags_changed"],
        ])
        
        return changes

    def _compare_structured_data(
        self,
        previous: List[Dict[str, Any]],
        current: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Сравнивает structured data"""
        # Простое сравнение по количеству и типам
        prev_types = {item.get('@type', 'Unknown') for item in previous}
        curr_types = {item.get('@type', 'Unknown') for item in current}
        
        return {
            "has_changes": prev_types != curr_types or len(previous) != len(current),
            "previous_count": len(previous),
            "current_count": len(current),
            "previous_types": sorted(prev_types),
            "current_types": sorted(curr_types),
        }

    def _compare_robots_txt(
        self,
        previous: Dict[str, Any],
        current: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Сравнивает robots.txt"""
        prev_exists = previous.get("exists", False)
        curr_exists = current.get("exists", False)
        
        if prev_exists != curr_exists:
            return {
                "has_changes": True,
                "existence_changed": True,
                "previous_exists": prev_exists,
                "current_exists": curr_exists,
            }
        
        if not prev_exists and not curr_exists:
            return {"has_changes": False}
        
        # Сравнить sitemap URLs
        prev_sitemaps = set(previous.get("sitemap_urls", []))
        curr_sitemaps = set(current.get("sitemap_urls", []))
        
        return {
            "has_changes": prev_sitemaps != curr_sitemaps,
            "sitemap_urls_changed": prev_sitemaps != curr_sitemaps,
            "added_sitemaps": list(curr_sitemaps - prev_sitemaps),
            "removed_sitemaps": list(prev_sitemaps - curr_sitemaps),
        }

    def _compare_sitemap(
        self,
        previous: Dict[str, Any],
        current: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Сравнивает sitemap"""
        prev_exists = previous.get("exists", False)
        curr_exists = current.get("exists", False)
        
        if prev_exists != curr_exists:
            return {
                "has_changes": True,
                "existence_changed": True,
                "previous_exists": prev_exists,
                "current_exists": curr_exists,
            }
        
        if not prev_exists and not curr_exists:
            return {"has_changes": False}
        
        # Сравнить количество URL
        prev_urls = set(previous.get("urls", []))
        curr_urls = set(current.get("urls", []))
        
        return {
            "has_changes": prev_urls != curr_urls or len(prev_urls) != len(curr_urls),
            "urls_count_changed": len(prev_urls) != len(curr_urls),
            "added_urls": list(curr_urls - prev_urls)[:10],  # Ограничить
            "removed_urls": list(prev_urls - curr_urls)[:10],
        }

    def _normalize_url(self, url: str) -> Optional[str]:
        """Нормализует URL"""
        if not url:
            return None
        
        # Добавить схему, если отсутствует
        if not url.startswith(('http://', 'https://')):
            url = f"https://{url}"
        
        try:
            parsed = urlparse(url)
            if not parsed.netloc:
                return None
            return f"{parsed.scheme}://{parsed.netloc}{parsed.path or ''}"
        except Exception:
            return None
