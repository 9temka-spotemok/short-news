"""
Real scrapers for AI news sources
"""

from typing import List, Dict, Any
from datetime import datetime, timedelta
from loguru import logger
import httpx
from bs4 import BeautifulSoup

from app.core.config import settings


class AINewsScraper:
    """Scraper for various AI news sources"""
    
    def __init__(self):
        self.session = httpx.AsyncClient(
            headers={'User-Agent': settings.SCRAPER_USER_AGENT},
            timeout=settings.SCRAPER_TIMEOUT,
            follow_redirects=True
        )
    
    async def scrape_openai_blog(self) -> List[Dict[str, Any]]:
        """Scrape OpenAI blog"""
        logger.info("Scraping OpenAI blog...")
        
        try:
            url = "https://openai.com/blog"
            response = await self.session.get(url)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            news_items = []
            # OpenAI blog structure - find article links
            articles = soup.select('a[href*="/blog/"]')[:10]
            
            for article in articles:
                href = article.get('href', '')
                if href and '/blog/' in href and href != '/blog/' and href != '/blog':
                    title = article.get_text(strip=True)
                    if title and len(title) > 10:
                        full_url = href if href.startswith('http') else f"https://openai.com{href}"
                        
                        news_items.append({
                            'title': title[:500],
                            'content': f"Article from OpenAI blog: {title}",
                            'summary': title[:200],
                            'source_url': full_url,
                            'source_type': 'blog',
                            'company_name': 'OpenAI',
                            'category': 'product_update',
                            'published_at': datetime.now() - timedelta(days=len(news_items)),
                        })
            
            logger.info(f"Scraped {len(news_items)} items from OpenAI blog")
            return news_items[:10]  # Get more news  # Limit to 5 most recent
            
        except Exception as e:
            logger.error(f"Failed to scrape OpenAI blog: {e}")
            return []
    
    async def scrape_anthropic_news(self) -> List[Dict[str, Any]]:
        """Scrape Anthropic news"""
        logger.info("Scraping Anthropic news...")
        
        try:
            url = "https://www.anthropic.com/news"
            response = await self.session.get(url)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            news_items = []
            # Find news articles
            articles = soup.select('a[href*="/news/"]')[:10]
            
            for article in articles:
                href = article.get('href', '')
                if href and '/news/' in href and href != '/news/' and href != '/news':
                    title = article.get_text(strip=True)
                    if title and len(title) > 10:
                        full_url = href if href.startswith('http') else f"https://www.anthropic.com{href}"
                        
                        news_items.append({
                            'title': title[:500],
                            'content': f"News from Anthropic: {title}",
                            'summary': title[:200],
                            'source_url': full_url,
                            'source_type': 'blog',
                            'company_name': 'Anthropic',
                            'category': 'product_update',
                            'published_at': datetime.now() - timedelta(days=len(news_items)),
                        })
            
            logger.info(f"Scraped {len(news_items)} items from Anthropic news")
            return news_items[:10]  # Get more news
            
        except Exception as e:
            logger.error(f"Failed to scrape Anthropic news: {e}")
            return []
    
    async def scrape_google_ai_blog(self) -> List[Dict[str, Any]]:
        """Scrape Google AI blog"""
        logger.info("Scraping Google AI blog...")
        
        try:
            url = "https://blog.google/technology/ai/"
            response = await self.session.get(url)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            news_items = []
            # Find blog posts
            articles = soup.select('article a, h3 a')[:10]
            
            for article in articles:
                href = article.get('href', '')
                title = article.get_text(strip=True)
                
                if href and title and len(title) > 10:
                    full_url = href if href.startswith('http') else f"https://blog.google{href}"
                    
                    news_items.append({
                        'title': title[:500],
                        'content': f"Article from Google AI Blog: {title}",
                        'summary': title[:200],
                        'source_url': full_url,
                        'source_type': 'blog',
                        'company_name': 'Google',
                        'category': 'technical_update',
                        'published_at': datetime.now() - timedelta(days=len(news_items)),
                    })
            
            logger.info(f"Scraped {len(news_items)} items from Google AI blog")
            return news_items[:10]  # Get more news
            
        except Exception as e:
            logger.error(f"Failed to scrape Google AI blog: {e}")
            return []
    
    async def scrape_meta_ai_blog(self) -> List[Dict[str, Any]]:
        """Scrape Meta AI blog"""
        logger.info("Scraping Meta AI blog...")
        
        try:
            url = "https://ai.meta.com/blog/"
            response = await self.session.get(url)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            news_items = []
            # Find blog posts
            articles = soup.select('article a, h2 a, h3 a')[:15]
            
            for article in articles:
                href = article.get('href', '')
                title = article.get_text(strip=True)
                
                if href and title and len(title) > 10 and 'blog' in href:
                    full_url = href if href.startswith('http') else f"https://ai.meta.com{href}"
                    
                    news_items.append({
                        'title': title[:500],
                        'content': f"Article from Meta AI Blog: {title}",
                        'summary': title[:200],
                        'source_url': full_url,
                        'source_type': 'blog',
                        'company_name': 'Meta',
                        'category': 'product_update',
                        'published_at': datetime.now() - timedelta(days=len(news_items)),
                    })
            
            logger.info(f"Scraped {len(news_items)} items from Meta AI blog")
            return news_items[:10]
            
        except Exception as e:
            logger.error(f"Failed to scrape Meta AI blog: {e}")
            return []
    
    async def scrape_huggingface_blog(self) -> List[Dict[str, Any]]:
        """Scrape Hugging Face blog"""
        logger.info("Scraping Hugging Face blog...")
        
        try:
            url = "https://huggingface.co/blog"
            response = await self.session.get(url)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            news_items = []
            # Find blog posts
            articles = soup.select('article a, h2 a')[:15]
            
            for article in articles:
                href = article.get('href', '')
                title = article.get_text(strip=True)
                
                if href and title and len(title) > 10:
                    full_url = href if href.startswith('http') else f"https://huggingface.co{href}"
                    
                    news_items.append({
                        'title': title[:500],
                        'content': f"Article from Hugging Face Blog: {title}",
                        'summary': title[:200],
                        'source_url': full_url,
                        'source_type': 'blog',
                        'company_name': 'Hugging Face',
                        'category': 'technical_update',
                        'published_at': datetime.now() - timedelta(days=len(news_items)),
                    })
            
            logger.info(f"Scraped {len(news_items)} items from Hugging Face blog")
            return news_items[:10]
            
        except Exception as e:
            logger.error(f"Failed to scrape Hugging Face blog: {e}")
            return []
    
    async def scrape_all(self) -> List[Dict[str, Any]]:
        """Scrape all sources"""
        logger.info("Starting scraping all AI news sources...")
        
        all_news = []
        
        # Scrape each source
        openai_news = await self.scrape_openai_blog()
        all_news.extend(openai_news)
        
        anthropic_news = await self.scrape_anthropic_news()
        all_news.extend(anthropic_news)
        
        google_news = await self.scrape_google_ai_blog()
        all_news.extend(google_news)
        
        meta_news = await self.scrape_meta_ai_blog()
        all_news.extend(meta_news)
        
        hf_news = await self.scrape_huggingface_blog()
        all_news.extend(hf_news)
        
        logger.info(f"Total scraped: {len(all_news)} news items")
        return all_news
    
    async def close(self):
        """Close HTTP session"""
        await self.session.aclose()

