"""
Marketing Change Detector Service

Детекция маркетинговых изменений на сайтах компаний:
- Изменения в ценах (pricing pages)
- Изменения баннеров (hash изображений)
- Изменения лендингов (сравнение структуры)
- Новые продукты (парсинг списка продуктов)
- Вакансии (парсинг careers страницы)
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
from app.services.website_structure_monitor import WebsiteStructureMonitor


class MarketingChangeDetector:
    """Сервис для детекции маркетинговых изменений на сайтах компаний"""

    # Селекторы для поиска цен
    PRICING_SELECTORS = [
        '.price', '.pricing', '.cost', '.amount',
        '[class*="price"]', '[class*="pricing"]',
        '[data-price]', '[data-amount]',
    ]

    # Селекторы для поиска продуктов
    PRODUCT_SELECTORS = [
        '.product', '.feature', '.solution', '.service',
        '[class*="product"]', '[class*="feature"]',
        '[data-product]', '[data-feature]',
    ]

    # Селекторы для поиска вакансий
    JOB_SELECTORS = [
        '.job', '.position', '.career', '.vacancy',
        '[class*="job"]', '[class*="position"]',
        '[class*="career"]', '[data-job]',
    ]

    def __init__(self):
        """Инициализация сервиса"""
        self.session = httpx.AsyncClient(
            headers={"User-Agent": settings.SCRAPER_USER_AGENT},
            timeout=settings.SCRAPER_TIMEOUT,
            follow_redirects=True,
        )
        self.structure_monitor = WebsiteStructureMonitor()

    async def close(self):
        """Закрыть HTTP сессии"""
        await self.session.aclose()
        await self.structure_monitor.close()

    async def detect_pricing_changes(
        self,
        pricing_url: str,
        previous_pricing: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Обнаруживает изменения в ценах на странице pricing.
        
        Args:
            pricing_url: URL страницы с ценами
            previous_pricing: Предыдущие данные о ценах (опционально)
            
        Returns:
            {
                "has_changes": True/False,
                "current_pricing": {...},
                "changes": {...}
            }
        """
        if not pricing_url:
            return {"has_changes": False, "error": "No pricing URL"}
        
        try:
            logger.info(f"Detecting pricing changes for {pricing_url}")
            
            response = await self.session.get(pricing_url)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'lxml')
            
            # Извлечь цены
            current_pricing = self._extract_pricing(soup, pricing_url)
            
            if not previous_pricing:
                return {
                    "has_changes": False,
                    "current_pricing": current_pricing,
                    "message": "No previous pricing to compare",
                }
            
            # Сравнить с предыдущими ценами
            changes = self._compare_pricing(previous_pricing, current_pricing)
            
            return {
                "has_changes": changes.get("has_changes", False),
                "current_pricing": current_pricing,
                "changes": changes,
            }
            
        except httpx.HTTPError as e:
            logger.error(f"HTTP error detecting pricing changes for {pricing_url}: {e}")
            return {"has_changes": False, "error": str(e)}
        except Exception as e:
            logger.error(f"Error detecting pricing changes for {pricing_url}: {e}")
            return {"has_changes": False, "error": str(e)}

    def _extract_pricing(self, soup: BeautifulSoup, base_url: str) -> Dict[str, Any]:
        """
        Извлекает информацию о ценах со страницы.
        
        Returns:
            {
                "plans": [...],
                "hash": "...",
                "extracted_at": "..."
            }
        """
        plans = []
        
        # Поиск по селекторам
        for selector in self.PRICING_SELECTORS:
            elements = soup.select(selector)
            for elem in elements:
                text = elem.get_text(strip=True)
                # Попытка найти цену в тексте
                price_match = re.search(r'[\$€£¥]?\s*(\d+[.,]?\d*)\s*[/\s]*(?:month|year|mo|yr|per|monthly|yearly)?', text, re.IGNORECASE)
                if price_match:
                    price = price_match.group(1).replace(',', '.')
                    plan_name = self._extract_plan_name(elem)
                    plans.append({
                        "name": plan_name,
                        "price": price,
                        "text": text[:200],  # Ограничить длину
                    })
        
        # Удалить дубликаты
        seen = set()
        unique_plans = []
        for plan in plans:
            key = (plan['name'], plan['price'])
            if key not in seen:
                seen.add(key)
                unique_plans.append(plan)
        
        # Вычислить hash
        plans_str = '|'.join(sorted([f"{p['name']}:{p['price']}" for p in unique_plans]))
        plans_hash = hashlib.md5(plans_str.encode()).hexdigest()
        
        return {
            "plans": unique_plans,
            "count": len(unique_plans),
            "hash": plans_hash,
            "extracted_at": datetime.now(timezone.utc).isoformat(),
        }

    def _extract_plan_name(self, element) -> str:
        """Извлекает название плана из элемента"""
        # Попробовать найти заголовок рядом
        parent = element.parent
        if parent:
            heading = parent.find(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
            if heading:
                return heading.get_text(strip=True)
        
        # Попробовать найти в data-атрибутах
        for attr in ['data-plan', 'data-name', 'data-tier']:
            if element.get(attr):
                return element.get(attr)
        
        return "Unknown Plan"

    def _compare_pricing(
        self,
        previous: Dict[str, Any],
        current: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Сравнивает цены между двумя снимками"""
        prev_hash = previous.get("hash")
        curr_hash = current.get("hash")
        
        if prev_hash == curr_hash:
            return {"has_changes": False}
        
        prev_plans = {p['name']: p for p in previous.get("plans", [])}
        curr_plans = {p['name']: p for p in current.get("plans", [])}
        
        changes = {
            "has_changes": True,
            "added_plans": [],
            "removed_plans": [],
            "price_changes": [],
        }
        
        # Новые планы
        for name, plan in curr_plans.items():
            if name not in prev_plans:
                changes["added_plans"].append(plan)
        
        # Удаленные планы
        for name, plan in prev_plans.items():
            if name not in curr_plans:
                changes["removed_plans"].append(plan)
        
        # Изменения цен
        common_names = set(prev_plans.keys()) & set(curr_plans.keys())
        for name in common_names:
            prev_price = prev_plans[name].get("price")
            curr_price = curr_plans[name].get("price")
            if prev_price != curr_price:
                changes["price_changes"].append({
                    "name": name,
                    "old_price": prev_price,
                    "new_price": curr_price,
                })
        
        return changes

    async def detect_banner_changes(
        self,
        website_url: str,
        previous_banners: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Обнаруживает изменения в баннерах на главной странице.
        
        Args:
            website_url: URL главной страницы
            previous_banners: Предыдущие данные о баннерах (опционально)
            
        Returns:
            {
                "has_changes": True/False,
                "current_banners": {...},
                "changes": {...}
            }
        """
        if not website_url:
            return {"has_changes": False, "error": "No website URL"}
        
        try:
            logger.info(f"Detecting banner changes for {website_url}")
            
            response = await self.session.get(website_url)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'lxml')
            
            # Извлечь баннеры
            current_banners = self._extract_banners(soup, website_url)
            
            if not previous_banners:
                return {
                    "has_changes": False,
                    "current_banners": current_banners,
                    "message": "No previous banners to compare",
                }
            
            # Сравнить с предыдущими баннерами
            changes = self._compare_banners(previous_banners, current_banners)
            
            return {
                "has_changes": changes.get("has_changes", False),
                "current_banners": current_banners,
                "changes": changes,
            }
            
        except httpx.HTTPError as e:
            logger.error(f"HTTP error detecting banner changes for {website_url}: {e}")
            return {"has_changes": False, "error": str(e)}
        except Exception as e:
            logger.error(f"Error detecting banner changes for {website_url}: {e}")
            return {"has_changes": False, "error": str(e)}

    def _extract_banners(self, soup: BeautifulSoup, base_url: str) -> Dict[str, Any]:
        """
        Извлекает баннеры (изображения) со страницы.
        
        Returns:
            {
                "banners": [...],
                "hash": "...",
                "extracted_at": "..."
            }
        """
        banners = []
        
        # Найти все изображения в hero/header секциях
        hero_sections = soup.find_all(['header', 'section', 'div'], 
                                      class_=re.compile(r'hero|banner|header|slider', re.I),
                                      limit=5)
        
        for section in hero_sections:
            images = section.find_all('img', src=True)
            for img in images:
                src = img.get('src', '')
                if src:
                    # Нормализовать URL
                    full_url = urljoin(base_url, src)
                    
                    # Получить hash изображения (по URL, так как загрузка может быть дорогой)
                    img_hash = hashlib.md5(full_url.encode()).hexdigest()
                    
                    banners.append({
                        "url": full_url,
                        "alt": img.get('alt', ''),
                        "hash": img_hash,
                    })
        
        # Удалить дубликаты
        seen = set()
        unique_banners = []
        for banner in banners:
            if banner['hash'] not in seen:
                seen.add(banner['hash'])
                unique_banners.append(banner)
        
        # Вычислить общий hash
        banners_str = '|'.join(sorted([b['hash'] for b in unique_banners]))
        banners_hash = hashlib.md5(banners_str.encode()).hexdigest()
        
        return {
            "banners": unique_banners,
            "count": len(unique_banners),
            "hash": banners_hash,
            "extracted_at": datetime.now(timezone.utc).isoformat(),
        }

    def _compare_banners(
        self,
        previous: Dict[str, Any],
        current: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Сравнивает баннеры между двумя снимками"""
        prev_hash = previous.get("hash")
        curr_hash = current.get("hash")
        
        if prev_hash == curr_hash:
            return {"has_changes": False}
        
        prev_hashes = {b['hash'] for b in previous.get("banners", [])}
        curr_hashes = {b['hash'] for b in current.get("banners", [])}
        
        return {
            "has_changes": True,
            "added_banners": [b for b in current.get("banners", []) if b['hash'] not in prev_hashes],
            "removed_banners": [b for b in previous.get("banners", []) if b['hash'] not in curr_hashes],
        }

    async def detect_landing_page_changes(
        self,
        landing_url: str,
        previous_snapshot: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Обнаруживает изменения на лендинг-странице (сравнение структуры).
        
        Args:
            landing_url: URL лендинг-страницы
            previous_snapshot: Предыдущий снимок структуры (опционально)
            
        Returns:
            {
                "has_changes": True/False,
                "current_snapshot": {...},
                "changes": {...}
            }
        """
        if not landing_url:
            return {"has_changes": False, "error": "No landing URL"}
        
        try:
            # Использовать WebsiteStructureMonitor для захвата снимка
            current_snapshot = await self.structure_monitor.capture_website_snapshot(landing_url)
            
            if not current_snapshot:
                return {"has_changes": False, "error": "Failed to capture snapshot"}
            
            if not previous_snapshot:
                return {
                    "has_changes": False,
                    "current_snapshot": current_snapshot,
                    "message": "No previous snapshot to compare",
                }
            
            # Сравнить снимки
            changes = await self.structure_monitor.detect_structure_changes(
                previous_snapshot,
                current_snapshot
            )
            
            return {
                "has_changes": changes.get("has_changes", False),
                "current_snapshot": current_snapshot,
                "changes": changes,
            }
            
        except Exception as e:
            logger.error(f"Error detecting landing page changes for {landing_url}: {e}")
            return {"has_changes": False, "error": str(e)}

    async def detect_new_products(
        self,
        products_url: str,
        previous_products: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Обнаруживает новые продукты на странице продуктов.
        
        Args:
            products_url: URL страницы с продуктами
            previous_products: Предыдущие данные о продуктах (опционально)
            
        Returns:
            {
                "has_changes": True/False,
                "current_products": {...},
                "new_products": [...]
            }
        """
        if not products_url:
            return {"has_changes": False, "error": "No products URL"}
        
        try:
            logger.info(f"Detecting new products for {products_url}")
            
            response = await self.session.get(products_url)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'lxml')
            
            # Извлечь продукты
            current_products = self._extract_products(soup, products_url)
            
            if not previous_products:
                return {
                    "has_changes": False,
                    "current_products": current_products,
                    "message": "No previous products to compare",
                }
            
            # Сравнить с предыдущими продуктами
            changes = self._compare_products(previous_products, current_products)
            
            return {
                "has_changes": changes.get("has_changes", False),
                "current_products": current_products,
                "new_products": changes.get("new_products", []),
            }
            
        except httpx.HTTPError as e:
            logger.error(f"HTTP error detecting new products for {products_url}: {e}")
            return {"has_changes": False, "error": str(e)}
        except Exception as e:
            logger.error(f"Error detecting new products for {products_url}: {e}")
            return {"has_changes": False, "error": str(e)}

    def _extract_products(self, soup: BeautifulSoup, base_url: str) -> Dict[str, Any]:
        """
        Извлекает список продуктов со страницы.
        
        Returns:
            {
                "products": [...],
                "hash": "...",
                "extracted_at": "..."
            }
        """
        products = []
        
        # Поиск по селекторам
        for selector in self.PRODUCT_SELECTORS:
            elements = soup.select(selector)
            for elem in elements:
                # Извлечь название продукта
                name = self._extract_product_name(elem)
                if name and name != "Unknown Product":
                    # Извлечь описание
                    desc_elem = elem.find(['p', 'div', 'span'], class_=re.compile(r'desc|text|summary', re.I))
                    description = desc_elem.get_text(strip=True)[:200] if desc_elem else ""
                    
                    # Извлечь URL продукта
                    link = elem.find('a', href=True)
                    product_url = urljoin(base_url, link['href']) if link else None
                    
                    products.append({
                        "name": name,
                        "description": description,
                        "url": product_url,
                    })
        
        # Удалить дубликаты
        seen = set()
        unique_products = []
        for product in products:
            key = product['name'].lower()
            if key not in seen:
                seen.add(key)
                unique_products.append(product)
        
        # Вычислить hash
        products_str = '|'.join(sorted([p['name'] for p in unique_products]))
        products_hash = hashlib.md5(products_str.encode()).hexdigest()
        
        return {
            "products": unique_products,
            "count": len(unique_products),
            "hash": products_hash,
            "extracted_at": datetime.now(timezone.utc).isoformat(),
        }

    def _extract_product_name(self, element) -> str:
        """Извлекает название продукта из элемента"""
        # Попробовать найти заголовок
        heading = element.find(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
        if heading:
            return heading.get_text(strip=True)
        
        # Попробовать найти в data-атрибутах
        for attr in ['data-product', 'data-name', 'data-title']:
            if element.get(attr):
                return element.get(attr)
        
        # Попробовать найти в тексте ссылки
        link = element.find('a')
        if link:
            text = link.get_text(strip=True)
            if text:
                return text
        
        return "Unknown Product"

    def _compare_products(
        self,
        previous: Dict[str, Any],
        current: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Сравнивает продукты между двумя снимками"""
        prev_hash = previous.get("hash")
        curr_hash = current.get("hash")
        
        if prev_hash == curr_hash:
            return {"has_changes": False, "new_products": []}
        
        prev_names = {p['name'].lower() for p in previous.get("products", [])}
        curr_products = current.get("products", [])
        
        new_products = [p for p in curr_products if p['name'].lower() not in prev_names]
        
        return {
            "has_changes": len(new_products) > 0,
            "new_products": new_products,
        }

    async def detect_job_postings(
        self,
        careers_url: str,
        previous_jobs: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Обнаруживает новые вакансии на странице careers.
        
        Args:
            careers_url: URL страницы с вакансиями
            previous_jobs: Предыдущие данные о вакансиях (опционально)
            
        Returns:
            {
                "has_changes": True/False,
                "current_jobs": {...},
                "new_jobs": [...]
            }
        """
        if not careers_url:
            return {"has_changes": False, "error": "No careers URL"}
        
        try:
            logger.info(f"Detecting job postings for {careers_url}")
            
            response = await self.session.get(careers_url)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'lxml')
            
            # Извлечь вакансии
            current_jobs = self._extract_jobs(soup, careers_url)
            
            if not previous_jobs:
                return {
                    "has_changes": False,
                    "current_jobs": current_jobs,
                    "message": "No previous jobs to compare",
                }
            
            # Сравнить с предыдущими вакансиями
            changes = self._compare_jobs(previous_jobs, current_jobs)
            
            return {
                "has_changes": changes.get("has_changes", False),
                "current_jobs": current_jobs,
                "new_jobs": changes.get("new_jobs", []),
            }
            
        except httpx.HTTPError as e:
            logger.error(f"HTTP error detecting job postings for {careers_url}: {e}")
            return {"has_changes": False, "error": str(e)}
        except Exception as e:
            logger.error(f"Error detecting job postings for {careers_url}: {e}")
            return {"has_changes": False, "error": str(e)}

    def _extract_jobs(self, soup: BeautifulSoup, base_url: str) -> Dict[str, Any]:
        """
        Извлекает список вакансий со страницы.
        
        Returns:
            {
                "jobs": [...],
                "hash": "...",
                "extracted_at": "..."
            }
        """
        jobs = []
        
        # Поиск по селекторам
        for selector in self.JOB_SELECTORS:
            elements = soup.select(selector)
            for elem in elements:
                # Извлечь название вакансии
                name = self._extract_job_name(elem)
                if name and name != "Unknown Job":
                    # Извлечь описание
                    desc_elem = elem.find(['p', 'div', 'span'], class_=re.compile(r'desc|text|summary', re.I))
                    description = desc_elem.get_text(strip=True)[:200] if desc_elem else ""
                    
                    # Извлечь URL вакансии
                    link = elem.find('a', href=True)
                    job_url = urljoin(base_url, link['href']) if link else None
                    
                    # Извлечь локацию
                    location_elem = elem.find(['span', 'div'], class_=re.compile(r'location|city|place', re.I))
                    location = location_elem.get_text(strip=True) if location_elem else ""
                    
                    jobs.append({
                        "name": name,
                        "description": description,
                        "location": location,
                        "url": job_url,
                    })
        
        # Удалить дубликаты
        seen = set()
        unique_jobs = []
        for job in jobs:
            key = (job['name'].lower(), job.get('location', '').lower())
            if key not in seen:
                seen.add(key)
                unique_jobs.append(job)
        
        # Вычислить hash
        jobs_str = '|'.join(sorted([f"{j['name']}:{j.get('location', '')}" for j in unique_jobs]))
        jobs_hash = hashlib.md5(jobs_str.encode()).hexdigest()
        
        return {
            "jobs": unique_jobs,
            "count": len(unique_jobs),
            "hash": jobs_hash,
            "extracted_at": datetime.now(timezone.utc).isoformat(),
        }

    def _extract_job_name(self, element) -> str:
        """Извлекает название вакансии из элемента"""
        # Попробовать найти заголовок
        heading = element.find(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
        if heading:
            return heading.get_text(strip=True)
        
        # Попробовать найти в data-атрибутах
        for attr in ['data-job', 'data-position', 'data-title']:
            if element.get(attr):
                return element.get(attr)
        
        # Попробовать найти в тексте ссылки
        link = element.find('a')
        if link:
            text = link.get_text(strip=True)
            if text:
                return text
        
        return "Unknown Job"

    def _compare_jobs(
        self,
        previous: Dict[str, Any],
        current: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Сравнивает вакансии между двумя снимками"""
        prev_hash = previous.get("hash")
        curr_hash = current.get("hash")
        
        if prev_hash == curr_hash:
            return {"has_changes": False, "new_jobs": []}
        
        prev_keys = {(j['name'].lower(), j.get('location', '').lower()) 
                     for j in previous.get("jobs", [])}
        curr_jobs = current.get("jobs", [])
        
        new_jobs = [j for j in curr_jobs 
                    if (j['name'].lower(), j.get('location', '').lower()) not in prev_keys]
        
        return {
            "has_changes": len(new_jobs) > 0,
            "new_jobs": new_jobs,
        }
