"""
Base scraper class
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from datetime import datetime
import httpx
from bs4 import BeautifulSoup
from loguru import logger

from app.core.config import settings


class BaseScraper(ABC):
    """Base class for all scrapers"""
    
    def __init__(self, source_id: str, base_url: str):
        self.source_id = source_id
        self.base_url = base_url
        self.session = httpx.AsyncClient(
            headers={
                'User-Agent': settings.SCRAPER_USER_AGENT,
            },
            timeout=settings.SCRAPER_TIMEOUT,
            follow_redirects=True
        )
    
    @abstractmethod
    async def scrape(self) -> List[Dict[str, Any]]:
        """
        Main scraping method to be implemented by subclasses
        Returns list of scraped items
        """
        pass
    
    async def fetch_page(self, url: str) -> Optional[BeautifulSoup]:
        """
        Fetch and parse a web page
        """
        try:
            logger.info(f"Fetching page: {url}")
            response = await self.session.get(url)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            return soup
            
        except Exception as e:
            logger.error(f"Failed to fetch page {url}: {e}")
            return None
    
    async def extract_text(self, soup: BeautifulSoup, selector: str) -> Optional[str]:
        """
        Extract text from soup using CSS selector
        """
        try:
            element = soup.select_one(selector)
            return element.get_text(strip=True) if element else None
        except Exception as e:
            logger.error(f"Failed to extract text with selector {selector}: {e}")
            return None
    
    async def extract_links(self, soup: BeautifulSoup, selector: str) -> List[str]:
        """
        Extract links from soup using CSS selector
        """
        try:
            elements = soup.select(selector)
            links = []
            for element in elements:
                href = element.get('href')
                if href:
                    # Convert relative URLs to absolute
                    if href.startswith('/'):
                        href = self.base_url + href
                    elif not href.startswith('http'):
                        href = self.base_url + '/' + href
                    links.append(href)
            return links
        except Exception as e:
            logger.error(f"Failed to extract links with selector {selector}: {e}")
            return []
    
    def normalize_text(self, text: str) -> str:
        """
        Normalize text content
        """
        if not text:
            return ""
        
        # Remove extra whitespace
        text = ' '.join(text.split())
        
        # Remove common unwanted characters
        text = text.replace('\u00a0', ' ')  # Non-breaking space
        text = text.replace('\u2013', '-')  # En dash
        text = text.replace('\u2014', '--')  # Em dash
        
        return text.strip()
    
    def summarize_text(self, content: str, max_length: int = 200) -> str:
        """
        Extract summary from content
        """
        if not content:
            return ""
        
        # Simple summary extraction - take first sentences
        sentences = content.split('. ')
        summary = ""
        
        for sentence in sentences:
            if len(summary + sentence) < max_length:
                summary += sentence + '. '
            else:
                break
        
        return summary.strip()
    
    async def close(self):
        """
        Close the HTTP session
        """
        await self.session.aclose()
    
    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(source_id={self.source_id})>"
