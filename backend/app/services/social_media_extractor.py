"""
Social Media Extractor Service

Извлекает ссылки на социальные сети из веб-сайтов компаний.
Ищет в meta tags, footer, страницах About/Contact, JSON-LD structured data.
"""

import re
from typing import Dict, List, Optional, Set
from urllib.parse import urljoin, urlparse
import httpx
from bs4 import BeautifulSoup
from loguru import logger

from app.core.config import settings


class SocialMediaExtractor:
    """Сервис для извлечения ссылок на социальные сети из веб-сайтов"""

    # Паттерны для распознавания URL соцсетей
    SOCIAL_PATTERNS = {
        'facebook': [
            r'facebook\.com/([^/?\s]+)',
            r'fb\.com/([^/?\s]+)',
            r'fb\.me/([^/?\s]+)',
        ],
        'instagram': [
            r'instagram\.com/([^/?\s]+)',
            r'instagr\.am/([^/?\s]+)',
        ],
        'twitter': [
            r'twitter\.com/([^/?\s]+)',
            r'x\.com/([^/?\s]+)',
        ],
        'linkedin': [
            r'linkedin\.com/company/([^/?\s]+)',
            r'linkedin\.com/in/([^/?\s]+)',
            r'linkedin\.com/([^/?\s]+)',
        ],
        'youtube': [
            r'youtube\.com/@([^/?\s]+)',
            r'youtube\.com/c/([^/?\s]+)',
            r'youtube\.com/channel/([^/?\s]+)',
            r'youtube\.com/user/([^/?\s]+)',
            r'youtu\.be/([^/?\s]+)',
        ],
        'tiktok': [
            r'tiktok\.com/@([^/?\s]+)',
        ],
    }

    # Meta property names для соцсетей
    META_PROPERTIES = {
        'facebook': ['og:url', 'article:author', 'fb:app_id'],
        'instagram': ['og:url'],
        'twitter': ['twitter:site', 'twitter:creator'],
        'linkedin': ['og:url'],
        'youtube': ['og:url'],
        'tiktok': ['og:url'],
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

    async def extract_social_media_from_website(self, website_url: str) -> Dict[str, Optional[str]]:
        """
        Извлекает ссылки на социальные сети с веб-сайта компании.
        
        Args:
            website_url: URL главной страницы сайта
            
        Returns:
            Словарь с найденными URL соцсетей:
            {
                'facebook': 'https://facebook.com/company',
                'instagram': 'https://instagram.com/company',
                ...
            }
        """
        if not website_url:
            return {}
        
        # Нормализовать URL
        normalized_url = self._normalize_url(website_url)
        if not normalized_url:
            return {}
        
        found_urls: Dict[str, Optional[str]] = {
            'facebook': None,
            'instagram': None,
            'twitter': None,
            'linkedin': None,
            'youtube': None,
            'tiktok': None,
        }
        
        try:
            # 1. Парсинг главной страницы
            main_page_urls = await self._extract_from_page(normalized_url)
            self._merge_urls(found_urls, main_page_urls)
            
            # 2. Парсинг страницы About
            about_urls = await self._extract_from_about_page(normalized_url)
            self._merge_urls(found_urls, about_urls)
            
            # 3. Парсинг страницы Contact
            contact_urls = await self._extract_from_contact_page(normalized_url)
            self._merge_urls(found_urls, contact_urls)
            
            # 4. Нормализация найденных URL
            for platform in found_urls:
                if found_urls[platform]:
                    found_urls[platform] = self.normalize_social_url(
                        found_urls[platform], platform
                    )
            
            logger.info(f"Found social media URLs for {normalized_url}: {sum(1 for v in found_urls.values() if v)}")
            
        except Exception as e:
            logger.error(f"Error extracting social media from {normalized_url}: {e}")
        
        return found_urls

    async def _extract_from_page(self, url: str) -> Dict[str, Optional[str]]:
        """Извлекает соцсети с одной страницы"""
        found_urls: Dict[str, Optional[str]] = {}
        
        try:
            response = await self.session.get(url)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 1. Извлечение из meta tags
            meta_urls = self.extract_from_meta_tags(soup, url)
            self._merge_urls(found_urls, meta_urls)
            
            # 2. Извлечение из footer
            footer_urls = self.extract_from_footer(soup, url)
            self._merge_urls(found_urls, footer_urls)
            
            # 3. Извлечение из JSON-LD structured data
            jsonld_urls = self._extract_from_jsonld(soup, url)
            self._merge_urls(found_urls, jsonld_urls)
            
            # 4. Поиск по всему HTML
            html_urls = self._extract_from_html(soup, url)
            self._merge_urls(found_urls, html_urls)
            
        except httpx.HTTPError as e:
            logger.warning(f"Failed to fetch {url}: {e}")
        except Exception as e:
            logger.error(f"Error parsing {url}: {e}")
        
        return found_urls

    def extract_from_meta_tags(self, soup: BeautifulSoup, base_url: str) -> Dict[str, Optional[str]]:
        """
        Извлекает ссылки на соцсети из meta tags.
        
        Args:
            soup: BeautifulSoup объект страницы
            base_url: Базовый URL для разрешения относительных ссылок
            
        Returns:
            Словарь с найденными URL
        """
        found_urls: Dict[str, Optional[str]] = {}
        
        # Проверка meta property
        for meta in soup.find_all('meta', property=True):
            prop = meta.get('property', '').lower()
            content = meta.get('content', '')
            
            if not content:
                continue
            
            # Проверка на Facebook
            if 'facebook' in prop or 'fb' in prop:
                if self._is_social_url(content, 'facebook'):
                    found_urls['facebook'] = content
            
            # Проверка на Twitter/X
            if 'twitter' in prop:
                if self._is_social_url(content, 'twitter'):
                    found_urls['twitter'] = content
        
        # Проверка meta name
        for meta in soup.find_all('meta', attrs={'name': re.compile(r'social|facebook|twitter|instagram|linkedin|youtube|tiktok', re.I)}):
            name = meta.get('name', '').lower()
            content = meta.get('content', '')
            
            if not content:
                continue
            
            # Определение платформы по имени
            if 'facebook' in name or 'fb' in name:
                if self._is_social_url(content, 'facebook'):
                    found_urls['facebook'] = content
            elif 'twitter' in name or 'x.com' in name:
                if self._is_social_url(content, 'twitter'):
                    found_urls['twitter'] = content
            elif 'instagram' in name:
                if self._is_social_url(content, 'instagram'):
                    found_urls['instagram'] = content
            elif 'linkedin' in name:
                if self._is_social_url(content, 'linkedin'):
                    found_urls['linkedin'] = content
            elif 'youtube' in name:
                if self._is_social_url(content, 'youtube'):
                    found_urls['youtube'] = content
            elif 'tiktok' in name:
                if self._is_social_url(content, 'tiktok'):
                    found_urls['tiktok'] = content
        
        return found_urls

    def extract_from_footer(self, soup: BeautifulSoup, base_url: str) -> Dict[str, Optional[str]]:
        """
        Извлекает ссылки на соцсети из footer страницы.
        
        Args:
            soup: BeautifulSoup объект страницы
            base_url: Базовый URL для разрешения относительных ссылок
            
        Returns:
            Словарь с найденными URL
        """
        found_urls: Dict[str, Optional[str]] = {}
        
        # Поиск footer
        footer = soup.find('footer') or soup.find('div', class_=re.compile(r'footer', re.I))
        
        if not footer:
            return found_urls
        
        # Поиск всех ссылок в footer
        for link in footer.find_all('a', href=True):
            href = link.get('href', '')
            if not href:
                continue
            
            # Разрешение относительных URL
            full_url = urljoin(base_url, href)
            
            # Проверка на соцсети
            for platform, patterns in self.SOCIAL_PATTERNS.items():
                for pattern in patterns:
                    if re.search(pattern, full_url, re.I):
                        if not found_urls.get(platform):
                            found_urls[platform] = full_url
                        break
        
        return found_urls

    async def extract_from_contact_page(self, base_url: str) -> Dict[str, Optional[str]]:
        """
        Извлекает ссылки на соцсети со страницы Contact.
        
        Args:
            base_url: Базовый URL сайта
            
        Returns:
            Словарь с найденными URL
        """
        contact_paths = ['/contact', '/contact-us', '/contacts', '/get-in-touch']
        
        for path in contact_paths:
            try:
                contact_url = urljoin(base_url, path)
                urls = await self._extract_from_page(contact_url)
                if any(urls.values()):
                    return urls
            except Exception as e:
                logger.debug(f"Failed to extract from {contact_url}: {e}")
                continue
        
        return {}

    async def _extract_from_about_page(self, base_url: str) -> Dict[str, Optional[str]]:
        """
        Извлекает ссылки на соцсети со страницы About.
        
        Args:
            base_url: Базовый URL сайта
            
        Returns:
            Словарь с найденными URL
        """
        about_paths = ['/about', '/about-us', '/company', '/team']
        
        for path in about_paths:
            try:
                about_url = urljoin(base_url, path)
                urls = await self._extract_from_page(about_url)
                if any(urls.values()):
                    return urls
            except Exception as e:
                logger.debug(f"Failed to extract from {about_url}: {e}")
                continue
        
        return {}

    def _extract_from_jsonld(self, soup: BeautifulSoup, base_url: str) -> Dict[str, Optional[str]]:
        """Извлекает ссылки из JSON-LD structured data"""
        found_urls: Dict[str, Optional[str]] = {}
        
        for script in soup.find_all('script', type='application/ld+json'):
            try:
                import json
                data = json.loads(script.string)
                
                # Рекурсивный поиск URL в JSON
                urls = self._find_urls_in_json(data)
                
                for url in urls:
                    for platform, patterns in self.SOCIAL_PATTERNS.items():
                        for pattern in patterns:
                            if re.search(pattern, url, re.I):
                                if not found_urls.get(platform):
                                    found_urls[platform] = url
                                break
            except (json.JSONDecodeError, AttributeError):
                continue
        
        return found_urls

    def _extract_from_html(self, soup: BeautifulSoup, base_url: str) -> Dict[str, Optional[str]]:
        """Извлекает ссылки из всего HTML документа"""
        found_urls: Dict[str, Optional[str]] = {}
        
        # Поиск всех ссылок
        for link in soup.find_all('a', href=True):
            href = link.get('href', '')
            if not href:
                continue
            
            full_url = urljoin(base_url, href)
            
            # Проверка на соцсети
            for platform, patterns in self.SOCIAL_PATTERNS.items():
                for pattern in patterns:
                    if re.search(pattern, full_url, re.I):
                        if not found_urls.get(platform):
                            found_urls[platform] = full_url
                        break
        
        return found_urls

    def _find_urls_in_json(self, obj: any) -> List[str]:
        """Рекурсивно находит все URL в JSON объекте"""
        urls = []
        
        if isinstance(obj, dict):
            for value in obj.values():
                urls.extend(self._find_urls_in_json(value))
        elif isinstance(obj, list):
            for item in obj:
                urls.extend(self._find_urls_in_json(item))
        elif isinstance(obj, str) and (obj.startswith('http://') or obj.startswith('https://')):
            urls.append(obj)
        
        return urls

    def normalize_social_url(self, url: str, platform: str) -> str:
        """
        Нормализует URL социальной сети.
        
        Args:
            url: URL для нормализации
            platform: Платформа (facebook, instagram, etc.)
            
        Returns:
            Нормализованный URL
        """
        if not url:
            return url
        
        # Убедиться, что URL начинается с https://
        if not url.startswith('http://') and not url.startswith('https://'):
            url = f'https://{url}'
        
        # Нормализация для разных платформ
        if platform == 'facebook':
            # Убрать параметры и нормализовать
            url = re.sub(r'[?&].*$', '', url)
            if not url.endswith('/'):
                url = url.rstrip('/')
        elif platform == 'instagram':
            url = re.sub(r'[?&].*$', '', url)
        elif platform == 'twitter':
            # Нормализовать x.com -> twitter.com (или наоборот, в зависимости от предпочтений)
            url = re.sub(r'x\.com', 'twitter.com', url)
            url = re.sub(r'[?&].*$', '', url)
        elif platform == 'linkedin':
            url = re.sub(r'[?&].*$', '', url)
        elif platform == 'youtube':
            url = re.sub(r'[?&].*$', '', url)
        elif platform == 'tiktok':
            url = re.sub(r'[?&].*$', '', url)
        
        return url

    def _is_social_url(self, url: str, platform: str) -> bool:
        """Проверяет, является ли URL ссылкой на указанную соцсеть"""
        if not url:
            return False
        
        patterns = self.SOCIAL_PATTERNS.get(platform, [])
        for pattern in patterns:
            if re.search(pattern, url, re.I):
                return True
        
        return False

    def _normalize_url(self, url: str) -> Optional[str]:
        """Нормализует базовый URL"""
        if not url:
            return None
        
        # Добавить протокол, если отсутствует
        if not url.startswith('http://') and not url.startswith('https://'):
            url = f'https://{url}'
        
        # Убрать www для нормализации
        url = re.sub(r'^https?://www\.', 'https://', url)
        
        return url.rstrip('/')

    def _merge_urls(self, target: Dict[str, Optional[str]], source: Dict[str, Optional[str]]):
        """Объединяет найденные URL, приоритет у уже существующих"""
        for platform, url in source.items():
            if url and not target.get(platform):
                target[platform] = url

    async def validate_social_url(self, url: str, platform: str) -> bool:
        """
        Валидирует URL социальной сети (проверка формата и доступности).
        
        Args:
            url: URL для валидации
            platform: Платформа (facebook, instagram, etc.)
            
        Returns:
            True если URL валиден и доступен
        """
        if not url:
            return False
        
        # Проверка формата
        if not self._is_social_url(url, platform):
            return False
        
        # Проверка доступности (опционально, можно отключить для ускорения)
        try:
            response = await self.session.head(url, timeout=5)
            # Принимаем любые коды ответа, кроме явных ошибок
            return response.status_code < 500
        except Exception:
            # Если проверка доступности не удалась, считаем URL валидным по формату
            return True

