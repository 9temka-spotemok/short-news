"""
Scraper abstractions for the news domain.
"""

from .interfaces import CompanyContext, ScrapedNewsItem, ScraperProvider
from .registry import NewsScraperRegistry

__all__ = [
    "CompanyContext",
    "ScrapedNewsItem",
    "ScraperProvider",
    "NewsScraperRegistry",
]




