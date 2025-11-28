"""
Press Release Scraper

Специализированный скрапер для поиска и парсинга пресс-релизов компаний.
Ищет страницы пресс-релизов и извлекает новости.
"""

import re
from typing import Dict, List, Optional, Any
from urllib.parse import urljoin, urlparse
from datetime import datetime

import httpx
from bs4 import BeautifulSoup
from loguru import logger

from app.core.config import settings


class PressReleaseScraper:
    """Скрапер для поиска и парсинга пресс-релизов"""

    # Паттерны для поиска страниц пресс-релизов
    PRESS_RELEASE_PATTERNS = [
        '/press',
        '/press-releases',
        '/press-release',
        '/newsroom',
        '/news',
        '/media',
        '/media-center',
        '/press-center',
        '/announcements',
        '/updates',
    ]

    # Селекторы для поиска пресс-релизов на странице
    ARTICLE_SELECTORS = [
        'article',
        '.press-release',
        '.press_release',
        '.news-item',
        '.news-item',
        '.announcement',
        '[class*="press"]',
        '[class*="release"]',
        '[class*="news"]',
    ]

    def __init__(self):
        """Инициализация скрапера"""
        self.session = httpx.AsyncClient(
            headers={"User-Agent": settings.SCRAPER_USER_AGENT},
            timeout=settings.SCRAPER_TIMEOUT,
            follow_redirects=True,
        )

    async def close(self):
        """Закрыть HTTP сессию"""
        await self.session.aclose()

    async def find_press_release_page(self, website_url: str) -> Optional[str]:
        """
        Находит страницу с пресс-релизами на сайте компании.
        
        Args:
            website_url: URL главной страницы сайта
            
        Returns:
            URL страницы с пресс-релизами или None
        """
        if not website_url:
            return None
        
        try:
            normalized_url = self._normalize_url(website_url)
            if not normalized_url:
                return None
            
            logger.info(f"Searching for press release page on {normalized_url}")
            
            # Сначала проверить главную страницу на наличие ссылок
            response = await self.session.get(normalized_url)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'lxml')
            
            # Найти все ссылки
            links = soup.find_all('a', href=True)
            parsed_base = urlparse(normalized_url)
            base_domain = f"{parsed_base.scheme}://{parsed_base.netloc}"
            
            # Поиск по паттернам в URL и тексте ссылок
            for link in links:
                href = link.get('href', '')
                text = link.get_text(strip=True).lower()
                
                if not href:
                    continue
                
                # Нормализовать URL
                full_url = urljoin(normalized_url, href)
                parsed = urlparse(full_url)
                
                # Проверить, что это тот же домен
                if parsed.netloc != parsed_base.netloc:
                    continue
                
                path_lower = parsed.path.lower()
                
                # Проверить паттерны в URL
                for pattern in self.PRESS_RELEASE_PATTERNS:
                    if pattern in path_lower:
                        # Проверить, что страница существует и содержит пресс-релизы
                        if await self._verify_press_release_page(full_url):
                            logger.info(f"Found press release page: {full_url}")
                            return full_url
                
                # Проверить паттерны в тексте ссылки
                press_keywords = ['press', 'release', 'newsroom', 'media', 'announcement']
                if any(keyword in text for keyword in press_keywords):
                    if await self._verify_press_release_page(full_url):
                        logger.info(f"Found press release page: {full_url}")
                        return full_url
            
            # Если не нашли через ссылки, попробовать прямые URL
            for pattern in self.PRESS_RELEASE_PATTERNS:
                test_url = urljoin(normalized_url, pattern)
                if await self._verify_press_release_page(test_url):
                    logger.info(f"Found press release page: {test_url}")
                    return test_url
            
            logger.warning(f"No press release page found for {normalized_url}")
            return None
            
        except httpx.HTTPError as e:
            logger.error(f"HTTP error finding press release page for {website_url}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error finding press release page for {website_url}: {e}")
            return None

    async def _verify_press_release_page(self, url: str) -> bool:
        """
        Проверяет, что страница содержит пресс-релизы.
        
        Args:
            url: URL страницы для проверки
            
        Returns:
            True, если страница содержит пресс-релизы
        """
        try:
            response = await self.session.get(url)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'lxml')
            
            # Проверить наличие статей/пресс-релизов
            for selector in self.ARTICLE_SELECTORS:
                articles = soup.select(selector)
                if len(articles) > 0:
                    return True
            
            # Проверить наличие ключевых слов в тексте
            text = soup.get_text().lower()
            press_keywords = ['press release', 'announcement', 'news', 'media']
            if any(keyword in text for keyword in press_keywords):
                # Проверить наличие ссылок на статьи
                links = soup.find_all('a', href=True)
                if len(links) > 3:  # Если есть несколько ссылок, вероятно это список
                    return True
            
            return False
            
        except Exception:
            return False

    async def scrape_press_releases(
        self,
        press_release_url: str,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Парсит пресс-релизы со страницы.
        
        Args:
            press_release_url: URL страницы с пресс-релизами
            limit: Максимальное количество пресс-релизов для парсинга
            
        Returns:
            Список словарей с данными пресс-релизов:
            [
                {
                    "title": "...",
                    "url": "...",
                    "published_at": "...",
                    "summary": "...",
                    "content": "..."
                },
                ...
            ]
        """
        if not press_release_url:
            return []
        
        try:
            logger.info(f"Scraping press releases from {press_release_url}")
            
            response = await self.session.get(press_release_url)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'lxml')
            
            press_releases = []
            
            # Поиск статей по селекторам
            for selector in self.ARTICLE_SELECTORS:
                articles = soup.select(selector)
                if articles:
                    for article in articles[:limit]:
                        release = self._extract_press_release(article, press_release_url)
                        if release:
                            press_releases.append(release)
                    
                    if press_releases:
                        break
            
            # Если не нашли через селекторы, попробовать найти ссылки на статьи
            if not press_releases:
                press_releases = await self._extract_from_links(soup, press_release_url, limit)
            
            # Удалить дубликаты по URL
            seen_urls = set()
            unique_releases = []
            for release in press_releases:
                if release['url'] not in seen_urls:
                    seen_urls.add(release['url'])
                    unique_releases.append(release)
            
            logger.info(f"Scraped {len(unique_releases)} press releases from {press_release_url}")
            return unique_releases[:limit]
            
        except httpx.HTTPError as e:
            logger.error(f"HTTP error scraping press releases from {press_release_url}: {e}")
            return []
        except Exception as e:
            logger.error(f"Error scraping press releases from {press_release_url}: {e}")
            return []

    def _extract_press_release(self, element: BeautifulSoup, base_url: str) -> Optional[Dict[str, Any]]:
        """
        Извлекает данные пресс-релиза из элемента.
        
        Args:
            element: BeautifulSoup элемент статьи
            base_url: Базовый URL для нормализации ссылок
            
        Returns:
            Словарь с данными пресс-релиза или None
        """
        try:
            # Извлечь заголовок
            title = None
            title_elem = element.find(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
            if title_elem:
                title = title_elem.get_text(strip=True)
            else:
                # Попробовать найти в ссылке
                link = element.find('a', href=True)
                if link:
                    title = link.get_text(strip=True)
            
            if not title:
                return None
            
            # Извлечь URL
            url = None
            link = element.find('a', href=True)
            if link:
                url = urljoin(base_url, link.get('href'))
            else:
                # Если нет ссылки, использовать базовый URL
                url = base_url
            
            # Извлечь дату публикации
            published_at = None
            date_elem = element.find(['time', 'span', 'div'], 
                                    class_=re.compile(r'date|time|published|created', re.I))
            if date_elem:
                date_text = date_elem.get_text(strip=True)
                # Попробовать распарсить дату
                published_at = self._parse_date(date_text)
            
            # Извлечь summary/описание
            summary = None
            summary_elem = element.find(['p', 'div', 'span'], 
                                        class_=re.compile(r'summary|excerpt|description|intro', re.I))
            if summary_elem:
                summary = summary_elem.get_text(strip=True)[:500]  # Ограничить длину
            else:
                # Взять первый параграф
                first_p = element.find('p')
                if first_p:
                    summary = first_p.get_text(strip=True)[:500]
            
            # Извлечь полный контент (если доступен)
            content = None
            content_elem = element.find(['div', 'article'], 
                                       class_=re.compile(r'content|body|text', re.I))
            if content_elem:
                content = content_elem.get_text(strip=True)
            else:
                # Взять весь текст элемента
                content = element.get_text(strip=True)
            
            return {
                "title": title,
                "url": url,
                "published_at": published_at,
                "summary": summary,
                "content": content[:2000] if content else None,  # Ограничить длину
            }
            
        except Exception as e:
            logger.warning(f"Error extracting press release: {e}")
            return None

    async def _extract_from_links(
        self,
        soup: BeautifulSoup,
        base_url: str,
        limit: int
    ) -> List[Dict[str, Any]]:
        """
        Извлекает пресс-релизы из списка ссылок на странице.
        
        Args:
            soup: BeautifulSoup объект страницы
            base_url: Базовый URL
            limit: Максимальное количество
            
        Returns:
            Список пресс-релизов
        """
        press_releases = []
        
        # Найти все ссылки, которые могут быть пресс-релизами
        links = soup.find_all('a', href=True)
        
        for link in links[:limit * 2]:  # Проверить больше ссылок
            href = link.get('href', '')
            text = link.get_text(strip=True)
            
            if not href or not text or len(text) < 10:
                continue
            
            # Пропустить внешние ссылки и якоря
            parsed = urlparse(href)
            if parsed.scheme and parsed.netloc:
                parsed_base = urlparse(base_url)
                if parsed.netloc != parsed_base.netloc:
                    continue
            
            if href.startswith('#'):
                continue
            
            # Нормализовать URL
            full_url = urljoin(base_url, href)
            
            # Попробовать загрузить страницу и извлечь данные
            try:
                response = await self.session.get(full_url)
                response.raise_for_status()
                
                article_soup = BeautifulSoup(response.text, 'lxml')
                
                # Найти основной контент
                article = article_soup.find(['article', 'main', 'div'], 
                                          class_=re.compile(r'article|content|post', re.I))
                if not article:
                    article = article_soup.find('body')
                
                if article:
                    release = self._extract_press_release(article, full_url)
                    if release and release['title']:
                        press_releases.append(release)
                        
                        if len(press_releases) >= limit:
                            break
                            
            except Exception:
                # Если не удалось загрузить, создать базовую запись
                press_releases.append({
                    "title": text,
                    "url": full_url,
                    "published_at": None,
                    "summary": None,
                    "content": None,
                })
        
        return press_releases

    def _parse_date(self, date_text: str) -> Optional[str]:
        """
        Парсит дату из текста.
        
        Args:
            date_text: Текст с датой
            
        Returns:
            ISO формат даты или None
        """
        # Простые паттерны для парсинга дат
        date_patterns = [
            r'(\d{4})-(\d{2})-(\d{2})',  # YYYY-MM-DD
            r'(\d{2})/(\d{2})/(\d{4})',  # MM/DD/YYYY
            r'(\d{2})\.(\d{2})\.(\d{4})',  # DD.MM.YYYY
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, date_text)
            if match:
                try:
                    if len(match.groups()) == 3:
                        # Попробовать создать дату
                        # Упрощенная версия - просто вернуть найденную строку
                        return date_text.strip()
                except Exception:
                    continue
        
        return None

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
