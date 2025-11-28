"""
Website Structure Monitor Service

Мониторинг структуры веб-сайтов компаний:
- Извлечение навигационного меню
- Поиск основных страниц (pricing, features, about, blog, news, careers)
- Извлечение метаданных страниц
- Сравнение снимков структуры для обнаружения изменений
"""

import hashlib
import re
from typing import Dict, List, Optional, Any, Set
from urllib.parse import urljoin, urlparse
from datetime import datetime, timezone

import httpx
from bs4 import BeautifulSoup
from loguru import logger

from app.core.config import settings


class WebsiteStructureMonitor:
    """Сервис для мониторинга структуры веб-сайтов компаний"""

    # Ключевые страницы для поиска
    KEY_PAGE_PATTERNS = {
        'pricing': ['/pricing', '/plans', '/price', '/prices', '/cost'],
        'features': ['/features', '/feature', '/solutions', '/capabilities'],
        'about': ['/about', '/about-us', '/company', '/team'],
        'blog': ['/blog', '/blogs', '/news', '/articles', '/posts', '/stories'],
        'news': ['/news', '/newsroom', '/press', '/press-releases', '/media'],
        'careers': ['/careers', '/jobs', '/hiring', '/work-with-us', '/join-us'],
    }

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

    async def capture_website_snapshot(self, website_url: str) -> Dict[str, Any]:
        """
        Захватывает снимок структуры веб-сайта.
        
        Args:
            website_url: URL главной страницы сайта
            
        Returns:
            Словарь с данными снимка:
            {
                "website_url": "...",
                "captured_at": "...",
                "navigation": {...},
                "key_pages": [...],
                "metadata": {...},
                "html_structure": {...}
            }
        """
        if not website_url:
            return {}
        
        try:
            # Нормализовать URL
            normalized_url = self._normalize_url(website_url)
            if not normalized_url:
                logger.warning(f"Invalid website URL: {website_url}")
                return {}
            
            logger.info(f"Capturing website structure snapshot for {normalized_url}")
            
            # Загрузить главную страницу
            response = await self.session.get(normalized_url)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'lxml')
            
            # Извлечь структуру
            snapshot = {
                "website_url": normalized_url,
                "captured_at": datetime.now(timezone.utc).isoformat(),
                "navigation": await self._extract_navigation(soup, normalized_url),
                "key_pages": await self._extract_key_pages(soup, normalized_url),
                "metadata": self._extract_metadata(soup),
                "html_structure": self._extract_html_structure(soup),
            }
            
            logger.info(f"Successfully captured snapshot for {normalized_url}")
            return snapshot
            
        except httpx.HTTPError as e:
            logger.error(f"HTTP error capturing snapshot for {website_url}: {e}")
            return {}
        except Exception as e:
            logger.error(f"Error capturing snapshot for {website_url}: {e}")
            return {}

    async def _extract_navigation(self, soup: BeautifulSoup, base_url: str) -> Dict[str, Any]:
        """
        Извлекает навигационное меню сайта.
        
        Returns:
            {
                "links": [...],
                "structure": {...},
                "hash": "..."  # для быстрого сравнения
            }
        """
        navigation_links = []
        nav_elements = soup.find_all(['nav', 'header', 'menu'], limit=5)
        
        for nav in nav_elements:
            links = nav.find_all('a', href=True)
            for link in links:
                href = link.get('href', '')
                text = link.get_text(strip=True)
                
                if href and text:
                    # Нормализовать URL
                    full_url = urljoin(base_url, href)
                    parsed = urlparse(full_url)
                    
                    # Только внутренние ссылки
                    if parsed.netloc == urlparse(base_url).netloc or not parsed.netloc:
                        navigation_links.append({
                            "url": full_url,
                            "text": text,
                            "href": href,
                        })
        
        # Удалить дубликаты
        seen = set()
        unique_links = []
        for link in navigation_links:
            key = (link['url'], link['text'])
            if key not in seen:
                seen.add(key)
                unique_links.append(link)
        
        # Вычислить hash для быстрого сравнения
        links_str = '|'.join(sorted([f"{l['url']}:{l['text']}" for l in unique_links]))
        links_hash = hashlib.md5(links_str.encode()).hexdigest()
        
        return {
            "links": unique_links,
            "count": len(unique_links),
            "hash": links_hash,
        }

    async def _extract_key_pages(self, soup: BeautifulSoup, base_url: str) -> List[Dict[str, Any]]:
        """
        Извлекает ключевые страницы сайта.
        
        Returns:
            [
                {"type": "pricing", "url": "...", "found": True},
                {"type": "blog", "url": "...", "found": True},
                ...
            ]
        """
        key_pages = []
        parsed_base = urlparse(base_url)
        base_domain = f"{parsed_base.scheme}://{parsed_base.netloc}"
        
        # Найти все ссылки на странице
        all_links = soup.find_all('a', href=True)
        found_urls = {urljoin(base_url, link.get('href', '')) for link in all_links}
        
        # Поиск по паттернам
        for page_type, patterns in self.KEY_PAGE_PATTERNS.items():
            found = False
            found_url = None
            
            for pattern in patterns:
                # Проверить прямые ссылки
                for url in found_urls:
                    parsed = urlparse(url)
                    if pattern in parsed.path.lower():
                        found = True
                        found_url = url
                        break
                
                if found:
                    break
                
                # Проверить текст ссылок
                for link in all_links:
                    href = link.get('href', '')
                    text = link.get_text(strip=True).lower()
                    if pattern.replace('/', '') in text or pattern in href.lower():
                        full_url = urljoin(base_url, href)
                        found = True
                        found_url = full_url
                        break
                
                if found:
                    break
            
            key_pages.append({
                "type": page_type,
                "url": found_url,
                "found": found,
            })
        
        return key_pages

    def _extract_metadata(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """
        Извлекает метаданные страницы.
        
        Returns:
            {
                "title": "...",
                "description": "...",
                "keywords": "...",
                "og_tags": {...},
                "twitter_tags": {...}
            }
        """
        metadata = {
            "title": None,
            "description": None,
            "keywords": None,
            "og_tags": {},
            "twitter_tags": {},
        }
        
        # Title
        title_tag = soup.find('title')
        if title_tag:
            metadata["title"] = title_tag.get_text(strip=True)
        
        # Meta description
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if meta_desc:
            metadata["description"] = meta_desc.get('content', '').strip()
        
        # Meta keywords
        meta_keywords = soup.find('meta', attrs={'name': 'keywords'})
        if meta_keywords:
            metadata["keywords"] = meta_keywords.get('content', '').strip()
        
        # Open Graph теги
        og_tags = soup.find_all('meta', attrs={'property': re.compile(r'^og:')})
        for tag in og_tags:
            prop = tag.get('property', '').replace('og:', '')
            content = tag.get('content', '')
            if prop and content:
                metadata["og_tags"][prop] = content
        
        # Twitter Card теги
        twitter_tags = soup.find_all('meta', attrs={'name': re.compile(r'^twitter:')})
        for tag in twitter_tags:
            name = tag.get('name', '').replace('twitter:', '')
            content = tag.get('content', '')
            if name and content:
                metadata["twitter_tags"][name] = content
        
        return metadata

    def _extract_html_structure(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """
        Извлекает структуру HTML страницы.
        
        Returns:
            {
                "sections": [...],
                "headings": [...],
                "hash": "..."  # для быстрого сравнения
            }
        """
        structure = {
            "sections": [],
            "headings": [],
        }
        
        # Основные секции
        sections = soup.find_all(['header', 'main', 'footer', 'aside', 'section'], limit=10)
        for section in sections:
            structure["sections"].append({
                "tag": section.name,
                "id": section.get('id', ''),
                "class": ' '.join(section.get('class', [])),
            })
        
        # Заголовки
        headings = soup.find_all(['h1', 'h2', 'h3', 'h4'], limit=20)
        for heading in headings:
            structure["headings"].append({
                "level": heading.name,
                "text": heading.get_text(strip=True)[:100],  # Ограничить длину
            })
        
        # Вычислить hash для быстрого сравнения
        structure_str = f"{len(structure['sections'])}:{len(structure['headings'])}"
        structure["hash"] = hashlib.md5(structure_str.encode()).hexdigest()
        
        return structure

    async def detect_structure_changes(
        self,
        previous_snapshot: Dict[str, Any],
        current_snapshot: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Обнаруживает изменения в структуре сайта между двумя снимками.
        
        Args:
            previous_snapshot: Предыдущий снимок структуры
            current_snapshot: Текущий снимок структуры
            
        Returns:
            {
                "has_changes": True/False,
                "navigation_changes": {...},
                "key_pages_changes": {...},
                "metadata_changes": {...},
                "html_structure_changes": {...}
            }
        """
        if not previous_snapshot or not current_snapshot:
            return {"has_changes": False, "error": "Missing snapshot data"}
        
        changes = {
            "has_changes": False,
            "navigation_changes": self._compare_navigation(
                previous_snapshot.get("navigation", {}),
                current_snapshot.get("navigation", {})
            ),
            "key_pages_changes": self._compare_key_pages(
                previous_snapshot.get("key_pages", []),
                current_snapshot.get("key_pages", [])
            ),
            "metadata_changes": self._compare_metadata(
                previous_snapshot.get("metadata", {}),
                current_snapshot.get("metadata", {})
            ),
            "html_structure_changes": self._compare_html_structure(
                previous_snapshot.get("html_structure", {}),
                current_snapshot.get("html_structure", {})
            ),
        }
        
        # Определить, есть ли изменения
        changes["has_changes"] = (
            changes["navigation_changes"]["has_changes"] or
            changes["key_pages_changes"]["has_changes"] or
            changes["metadata_changes"]["has_changes"] or
            changes["html_structure_changes"]["has_changes"]
        )
        
        return changes

    def _compare_navigation(
        self,
        prev_nav: Dict[str, Any],
        curr_nav: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Сравнивает навигацию между снимками"""
        prev_links = {link['url']: link for link in prev_nav.get("links", [])}
        curr_links = {link['url']: link for link in curr_nav.get("links", [])}
        
        prev_urls = set(prev_links.keys())
        curr_urls = set(curr_links.keys())
        
        added = [curr_links[url] for url in curr_urls - prev_urls]
        removed = [prev_links[url] for url in prev_urls - curr_urls]
        changed = []
        
        # Проверить изменения в тексте ссылок
        common = prev_urls & curr_urls
        for url in common:
            if prev_links[url]['text'] != curr_links[url]['text']:
                changed.append({
                    "url": url,
                    "old_text": prev_links[url]['text'],
                    "new_text": curr_links[url]['text'],
                })
        
        return {
            "has_changes": len(added) > 0 or len(removed) > 0 or len(changed) > 0,
            "added": added,
            "removed": removed,
            "changed": changed,
            "prev_hash": prev_nav.get("hash"),
            "curr_hash": curr_nav.get("hash"),
        }

    def _compare_key_pages(
        self,
        prev_pages: List[Dict[str, Any]],
        curr_pages: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Сравнивает ключевые страницы между снимками"""
        prev_dict = {p['type']: p for p in prev_pages}
        curr_dict = {p['type']: p for p in curr_pages}
        
        changes = {
            "has_changes": False,
            "new_pages": [],
            "removed_pages": [],
            "url_changes": [],
        }
        
        all_types = set(prev_dict.keys()) | set(curr_dict.keys())
        
        for page_type in all_types:
            prev_page = prev_dict.get(page_type, {})
            curr_page = curr_dict.get(page_type, {})
            
            prev_found = prev_page.get("found", False)
            curr_found = curr_page.get("found", False)
            prev_url = prev_page.get("url")
            curr_url = curr_page.get("url")
            
            if not prev_found and curr_found:
                changes["new_pages"].append(curr_page)
                changes["has_changes"] = True
            elif prev_found and not curr_found:
                changes["removed_pages"].append(prev_page)
                changes["has_changes"] = True
            elif prev_found and curr_found and prev_url != curr_url:
                changes["url_changes"].append({
                    "type": page_type,
                    "old_url": prev_url,
                    "new_url": curr_url,
                })
                changes["has_changes"] = True
        
        return changes

    def _compare_metadata(
        self,
        prev_meta: Dict[str, Any],
        curr_meta: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Сравнивает метаданные между снимками"""
        changes = {
            "has_changes": False,
            "title_changed": prev_meta.get("title") != curr_meta.get("title"),
            "description_changed": prev_meta.get("description") != curr_meta.get("description"),
            "keywords_changed": prev_meta.get("keywords") != curr_meta.get("keywords"),
            "og_tags_changed": prev_meta.get("og_tags") != curr_meta.get("og_tags"),
            "twitter_tags_changed": prev_meta.get("twitter_tags") != curr_meta.get("twitter_tags"),
        }
        
        changes["has_changes"] = any([
            changes["title_changed"],
            changes["description_changed"],
            changes["keywords_changed"],
            changes["og_tags_changed"],
            changes["twitter_tags_changed"],
        ])
        
        return changes

    def _compare_html_structure(
        self,
        prev_structure: Dict[str, Any],
        curr_structure: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Сравнивает структуру HTML между снимками"""
        prev_hash = prev_structure.get("hash")
        curr_hash = curr_structure.get("hash")
        
        return {
            "has_changes": prev_hash != curr_hash,
            "prev_hash": prev_hash,
            "curr_hash": curr_hash,
            "sections_count_changed": len(prev_structure.get("sections", [])) != len(curr_structure.get("sections", [])),
            "headings_count_changed": len(prev_structure.get("headings", [])) != len(curr_structure.get("headings", [])),
        }

    async def extract_key_pages(self, website_url: str) -> List[str]:
        """
        Извлекает URL ключевых страниц сайта.
        
        Args:
            website_url: URL главной страницы сайта
            
        Returns:
            Список URL найденных ключевых страниц
        """
        snapshot = await self.capture_website_snapshot(website_url)
        if not snapshot:
            return []
        
        key_pages = snapshot.get("key_pages", [])
        return [page["url"] for page in key_pages if page.get("found") and page.get("url")]

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
